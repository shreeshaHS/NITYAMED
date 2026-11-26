"""Hybrid generative tool-calling LLM agent with strict safety rails and graceful fallback."""

from dataclasses import dataclass
import json
import logging

import httpx

from app.core.config import get_settings
from app.modules.assistant.tools import (
    ASSISTANT_TOOLS,
    ToolExecutionContext,
    execute_assistant_tool,
    to_gemini_function_declarations,
)

logger = logging.getLogger("nityamed.assistant.agent")

SAFETY_SYSTEM_PROMPT = """
ABSOLUTE CLINICAL & REGULATORY PROHIBITIONS:
1. NO diagnosis ("Do I have diabetes?" -> Refuse safely and refer to a doctor).
2. NO prescribing ("What antibiotic/tablet should I take for pain?" -> Refuse safely).
3. NO dose changes ("Can I double my dose?" -> Refuse safely).
4. NO stopping prescribed medications ("Should I stop my BP tablet?" -> Refuse safely).
5. NO drug-interaction advice ("Can I take X with Y?" -> Refuse safely).
6. NO emergency medical triage ("Chest pain / trouble breathing" -> Urge immediate emergency medical services).
7. Verified-catalogue-only policy: never recommend custom/unverified/banned drugs.

TOOL & GROUNDING RULES:
- Use ONLY verified facts returned by your tool calls (exact medicine names, stock numbers, dates, times).
- For state-changing actions (`stage_confirm_dose`, `stage_skip_dose`, `stage_stock_purchase`), ALWAYS call the `stage_*` tool so the user gets an explicit confirmation prompt before database mutation. NEVER pretend a staged action is already saved.
- Keep final spoken replies warm, helpful, accurate, and concise (1 to 3 short sentences) in the requested language (English, Kannada in Kannada script, or Hindi in Devanagari).
""".strip()


@dataclass
class AgentTurnResult:
    """Grounded result returned by HybridToolAgent when an LLM provider handles the turn."""

    reply_text: str
    primary_intent: str
    provider: str


def _infer_primary_intent(called_tools: list[str], staged_actions: list[dict]) -> str:
    if staged_actions:
        if len(staged_actions) > 1:
            return "compound_action"
        return str(staged_actions[0].get("action_type") or "confirm_dose")
    mapping = {
        "get_today_schedule": "today_schedule",
        "get_user_medicines": "check_stock",
        "get_refill_predictions": "refill_check",
        "get_next_dose": "next_dose",
        "get_adherence_status": "adherence_status",
        "search_medicine_catalogue": "company_lookup",
        "get_medicine_education": "medicine_info",
        "snooze_dose_reminder": "snooze_dose",
        "stage_confirm_dose": "confirm_dose",
        "stage_stock_purchase": "update_stock_purchase",
        "stage_skip_dose": "skip_dose",
    }
    for name in called_tools:
        if name in mapping:
            return mapping[name]
    return "assistant_agent"


class HybridToolAgent:
    """Executes bounded Gemini / Hugging Face tool-calling turns over HTTPS (`httpx`)."""

    max_tool_rounds = 3

    def build_system_prompt(self, ctx: ToolExecutionContext, target_language: str) -> str:
        """Assemble grounded user snapshot + safety guardrails for the LLM."""
        lang_label = {"kn": "Kannada (ಕನ್ನಡ)", "hi": "Hindi (हिन्दी)"}.get(target_language, "English")
        display_name = ctx.profile.display_name if ctx.profile else "Patient"
        med_summary = ", ".join(
            f"{m.display_name} ({m.strength}, stock={m.confirmed_stock} {m.stock_unit})"
            for m in ctx.active_meds[:12]
        ) or "None added yet"
        return (
            f"{SAFETY_SYSTEM_PROMPT}\n\n"
            f"USER CONTEXT:\n"
            f"- Patient Name: {display_name}\n"
            f"- Response Language: {lang_label}\n"
            f"- Timezone: {ctx.tz.key}\n"
            f"- Active Medicines Snapshot: {med_summary}"
        )

    def run(
        self,
        *,
        user_text: str,
        target_language: str,
        history: list[dict[str, str]],
        ctx: ToolExecutionContext,
    ) -> AgentTurnResult | None:
        """Run tool-calling loop via Gemini (priority 1) or HF Router (priority 2)."""
        settings = get_settings()
        system_prompt = self.build_system_prompt(ctx, target_language)

        if settings.gemini_api_key:
            res = self._run_gemini_loop(
                api_key=settings.gemini_api_key,
                model=settings.gemini_model,
                system_prompt=system_prompt,
                user_text=user_text,
                history=history,
                ctx=ctx,
            )
            if res is not None:
                return res

        if settings.hf_token:
            res = self._run_hf_loop(
                hf_token=settings.hf_token,
                model=settings.hf_llm_model,
                system_prompt=system_prompt,
                user_text=user_text,
                history=history,
                ctx=ctx,
            )
            if res is not None:
                return res

        return None

    def _run_gemini_loop(
        self,
        *,
        api_key: str,
        model: str,
        system_prompt: str,
        user_text: str,
        history: list[dict[str, str]],
        ctx: ToolExecutionContext,
    ) -> AgentTurnResult | None:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:generateContent?key={api_key}"
        )
        contents: list[dict] = []
        for turn in (history or [])[-4:]:
            if turn.get("user"):
                contents.append({"role": "user", "parts": [{"text": turn["user"]}]})
            if turn.get("assistant"):
                contents.append({"role": "model", "parts": [{"text": turn["assistant"]}]})
        contents.append({"role": "user", "parts": [{"text": user_text}]})

        tools_payload = [{"functionDeclarations": to_gemini_function_declarations()}]

        try:
            for _ in range(self.max_tool_rounds):
                resp = httpx.post(
                    url,
                    json={
                        "system_instruction": {"parts": [{"text": system_prompt}]},
                        "contents": contents,
                        "tools": tools_payload,
                        "generationConfig": {"temperature": 0.25, "maxOutputTokens": 320},
                    },
                    timeout=10.0,
                )
                resp.raise_for_status()
                candidates = resp.json().get("candidates") or []
                if not candidates:
                    return None
                model_content = candidates[0].get("content") or {}
                parts = model_content.get("parts") or []
                fn_calls = [p["functionCall"] for p in parts if "functionCall" in p]
                if not fn_calls:
                    reply = " ".join(str(p.get("text") or "").strip() for p in parts if p.get("text")).strip()
                    if reply and ctx.called_tools:
                        return AgentTurnResult(
                            reply_text=reply,
                            primary_intent=_infer_primary_intent(ctx.called_tools, ctx.staged_actions),
                            provider="gemini",
                        )
                    return None

                contents.append({"role": "model", "parts": parts})
                fn_responses = []
                for call in fn_calls:
                    fn_name = str(call.get("name") or "")
                    fn_args = call.get("args") if isinstance(call.get("args"), dict) else {}
                    tool_out = execute_assistant_tool(fn_name, fn_args, ctx)
                    fn_responses.append(
                        {
                            "functionResponse": {
                                "name": fn_name,
                                "response": tool_out,
                            }
                        }
                    )
                contents.append({"role": "user", "parts": fn_responses})
        except Exception as exc:
            logger.warning("Gemini tool-calling loop fell back: %s", exc)
        return None

    def _run_hf_loop(
        self,
        *,
        hf_token: str,
        model: str,
        system_prompt: str,
        user_text: str,
        history: list[dict[str, str]],
        ctx: ToolExecutionContext,
    ) -> AgentTurnResult | None:
        messages: list[dict] = [{"role": "system", "content": system_prompt}]
        for turn in (history or [])[-4:]:
            if turn.get("user"):
                messages.append({"role": "user", "content": turn["user"]})
            if turn.get("assistant"):
                messages.append({"role": "assistant", "content": turn["assistant"]})
        messages.append({"role": "user", "content": user_text})

        try:
            for _ in range(self.max_tool_rounds):
                resp = httpx.post(
                    "https://router.huggingface.co/v1/chat/completions",
                    headers={"Authorization": f"Bearer {hf_token}"},
                    json={
                        "model": model,
                        "temperature": 0.25,
                        "max_tokens": 320,
                        "messages": messages,
                        "tools": ASSISTANT_TOOLS,
                        "tool_choice": "auto",
                    },
                    timeout=12.0,
                )
                resp.raise_for_status()
                choices = resp.json().get("choices") or []
                if not choices:
                    return None
                msg = choices[0].get("message") or {}
                tool_calls = msg.get("tool_calls") or []
                if not tool_calls:
                    reply = str(msg.get("content") or "").strip()
                    if reply and ctx.called_tools:
                        return AgentTurnResult(
                            reply_text=reply,
                            primary_intent=_infer_primary_intent(ctx.called_tools, ctx.staged_actions),
                            provider="hf_router",
                        )
                    return None

                messages.append(msg)
                for call in tool_calls:
                    fn = call.get("function") or {}
                    fn_name = str(fn.get("name") or "")
                    raw_args = fn.get("arguments")
                    if isinstance(raw_args, str):
                        try:
                            fn_args = json.loads(raw_args) if raw_args.strip() else {}
                        except ValueError:
                            fn_args = {}
                    elif isinstance(raw_args, dict):
                        fn_args = raw_args
                    else:
                        fn_args = {}
                    tool_out = execute_assistant_tool(fn_name, fn_args, ctx)
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": call.get("id") or fn_name,
                            "content": json.dumps(tool_out),
                        }
                    )
        except Exception as exc:
            logger.warning("HF Router tool-calling loop fell back: %s", exc)
        return None
