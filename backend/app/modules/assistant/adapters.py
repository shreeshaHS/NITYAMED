"""Swappable external STT, TTS, and bounded LLM adapter interfaces (with Hugging Face support)."""

from dataclasses import dataclass
import json
import logging

import httpx

from app.core.config import get_settings
from app.core.exceptions import AppError

logger = logging.getLogger("nityamed.assistant")

ALLOWED_ASSISTANT_INTENTS: tuple[str, ...] = (
    "check_stock",
    "today_schedule",
    "next_dose",
    "medicine_info",
    "adherence_status",
    "refill_check",
    "confirm_dose",
    "skip_dose",
    "snooze_dose",
    "update_stock_purchase",
    "company_lookup",
    "greeting_help",
    "out_of_scope",
)


@dataclass(slots=True)
class STTResult:
    """Result from speech-to-text transcription."""

    transcript: str
    detected_language: str | None = None


def _parse_bounded_intent_json(raw_text: str) -> tuple[str, float] | None:
    """Extract a validated (intent, confidence) tuple from bounded JSON text."""
    cleaned = raw_text.strip().strip("`")
    if cleaned.lower().startswith("json"):
        cleaned = cleaned[4:].strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end > start:
        cleaned = cleaned[start : end + 1]
    parsed = json.loads(cleaned)
    intent = str(parsed.get("intent") or "").strip()
    conf = float(parsed.get("confidence") or 0.75)
    if intent in ALLOWED_ASSISTANT_INTENTS:
        return intent, max(0.0, min(1.0, conf))
    return None


class STTAdapter:
    """Speech-to-text adapter supporting custom Whisper URL and Hugging Face Whisper API."""

    def transcribe(
        self, audio_bytes: bytes, filename: str, language_hint: str | None = None
    ) -> STTResult:
        """Transcribe audio bytes via custom STT_API_URL or Hugging Face Router Whisper."""
        settings = get_settings()

        if settings.stt_api_url:
            headers: dict[str, str] = {}
            if settings.stt_api_key:
                headers["Authorization"] = f"Bearer {settings.stt_api_key}"
            data: dict[str, str] = {"model": "whisper-1"}
            if language_hint in {"en", "kn", "hi"}:
                data["language"] = language_hint
            try:
                resp = httpx.post(
                    settings.stt_api_url,
                    headers=headers,
                    data=data,
                    files={"file": (filename or "voice.wav", audio_bytes, "audio/wav")},
                    timeout=15.0,
                )
                resp.raise_for_status()
                transcript = str(resp.json().get("text") or "").strip()
                if not transcript:
                    raise AppError(422, "EMPTY_TRANSCRIPT", "Could not detect speech in audio.")
                return STTResult(transcript=transcript, detected_language=language_hint)
            except AppError:
                raise
            except Exception as exc:
                logger.warning("Custom STT provider failed: %s", exc)
                raise AppError(502, "STT_PROVIDER_ERROR", "Speech transcription failed; please try again.") from exc

        if settings.hf_token:
            hf_url = f"https://router.huggingface.co/hf-inference/models/{settings.hf_stt_model}"
            content_type = "audio/wav" if (filename or "").lower().endswith(".wav") else "audio/mpeg"
            try:
                resp = httpx.post(
                    hf_url,
                    headers={
                        "Authorization": f"Bearer {settings.hf_token}",
                        "Content-Type": content_type,
                    },
                    content=audio_bytes,
                    timeout=20.0,
                )
                resp.raise_for_status()
                transcript = str(resp.json().get("text") or "").strip()
                if not transcript:
                    raise AppError(422, "EMPTY_TRANSCRIPT", "Could not detect speech in audio.")
                return STTResult(transcript=transcript, detected_language=language_hint)
            except AppError:
                raise
            except Exception as exc:
                logger.warning("Hugging Face Whisper STT failed: %s", exc)
                raise AppError(
                    502,
                    "STT_PROVIDER_ERROR",
                    "Hugging Face speech transcription is temporarily unavailable.",
                ) from exc

        raise AppError(
            503,
            "STT_PROVIDER_NOT_CONFIGURED",
            "Server STT provider is not configured; use the app microphone button or configure HF_TOKEN / STT_API_URL.",
        )


class TTSAdapter:
    """Text-to-speech adapter interface (client uses native expo-speech by default)."""

    def synthesize_base64(self, text: str, language: str) -> str | None:
        """Synthesize reply text into base64 audio, or return None if client TTS handles playback."""
        return None


class BoundedLLMAdapter:
    """Bounded dialect fallback strictly restricted to classifying into ALLOWED_ASSISTANT_INTENTS."""

    def classify_dialect_intent(self, text: str) -> tuple[str, float] | None:
        """Disambiguate low-confidence queries via MuRIL HF Space, HF Router LLM, or Gemini.

        Never generates clinical advice; only returns a validated intent from ALLOWED_ASSISTANT_INTENTS.
        """
        settings = get_settings()

        # 1. Optional self-hosted fine-tuned MuRIL Hugging Face Space
        if settings.hf_space_url:
            space_endpoint = settings.hf_space_url.rstrip("/")
            if not space_endpoint.endswith("/classify"):
                space_endpoint = f"{space_endpoint}/classify"
            headers = {"Authorization": f"Bearer {settings.hf_token}"} if settings.hf_token else {}
            try:
                resp = httpx.post(space_endpoint, headers=headers, json={"text": text}, timeout=6.0)
                resp.raise_for_status()
                data = resp.json()
                intent = str(data.get("intent") or "").strip()
                conf = float(data.get("confidence") or 0.0)
                if intent in ALLOWED_ASSISTANT_INTENTS:
                    return intent, max(0.0, min(1.0, conf))
            except Exception as exc:
                logger.warning("HF Space classifier fallback skipped: %s", exc)

        classification_prompt = (
            "Classify this patient medication continuity query (English, Kannada, Hindi, or Romanized/mixed) "
            "into ONLY ONE of these exact intents:\n"
            f"{', '.join(ALLOWED_ASSISTANT_INTENTS)}\n"
            "If the user asks for diagnosis, prescribing, stopping/changing dosage, or off-topic chat, return out_of_scope.\n"
            'Respond ONLY with JSON: {"intent": "<intent>", "confidence": 0.85}\n'
            f"Query: {text}"
        )

        # 2. Optional Hugging Face Inference Router chat completions
        if settings.hf_token:
            try:
                resp = httpx.post(
                    "https://router.huggingface.co/v1/chat/completions",
                    headers={"Authorization": f"Bearer {settings.hf_token}"},
                    json={
                        "model": settings.hf_llm_model,
                        "temperature": 0.0,
                        "max_tokens": 60,
                        "messages": [{"role": "user", "content": classification_prompt}],
                    },
                    timeout=8.0,
                )
                resp.raise_for_status()
                choices = resp.json().get("choices") or []
                raw_text = choices[0].get("message", {}).get("content", "") if choices else ""
                parsed = _parse_bounded_intent_json(str(raw_text))
                if parsed is not None:
                    return parsed
            except Exception as exc:
                logger.warning("Hugging Face dialect fallback skipped: %s", exc)

        # 3. Optional Google Gemini fallback
        if settings.gemini_api_key:
            url = (
                f"https://generativelanguage.googleapis.com/v1beta/models/"
                f"{settings.gemini_model}:generateContent?key={settings.gemini_api_key}"
            )
            try:
                resp = httpx.post(
                    url,
                    json={"contents": [{"parts": [{"text": classification_prompt}]}]},
                    timeout=6.0,
                )
                resp.raise_for_status()
                candidates = resp.json().get("candidates") or []
                raw_text = (
                    candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                    if candidates
                    else ""
                )
                parsed = _parse_bounded_intent_json(str(raw_text))
                if parsed is not None:
                    return parsed
            except Exception as exc:
                logger.warning("Gemini dialect fallback skipped: %s", exc)

        return None

    def simplify_or_translate(self, verified_text: str, target_language: str) -> str:
        """Return verified_text unchanged to guarantee deterministic clinical & data fidelity."""
        return verified_text

    def generate_conversational_reply(
        self,
        *,
        user_text: str,
        target_language: str,
        grounded_facts: str,
        history: list[dict[str, str]] | None = None,
    ) -> str | None:
        """Generate a warm, Gemini/Google-Assistant-style reply strictly grounded in verified DB facts."""
        settings = get_settings()
        if not settings.gemini_api_key and not settings.hf_token:
            return None

        lang_label = {"kn": "Kannada (ಕನ್ನಡ)", "hi": "Hindi (हिन्दी)"}.get(target_language, "English")
        recent_turns = "\n".join(
            f"User: {h.get('user', '')}\nAssistant: {h.get('assistant', '')}"
            for h in (history or [])[-4:]
        )
        system_prompt = (
            f"You are NityaMed Voice Companion — warm, friendly, conversational like Google Assistant or Gemini, "
            f"speaking in {lang_label}.\n"
            "STRICT RULES:\n"
            "1. Use ONLY the Verified Facts below (exact medicine names, numbers, dates, and stock counts).\n"
            "2. NEVER diagnose, prescribe, suggest starting/stopping/changing dosages, or mention unverified facts.\n"
            "3. Reply naturally and empathetically in 1 to 3 concise sentences suitable for spoken voice.\n"
            "4. Keep all numeric stock counts, dates, times, and source citations exact when present in Verified Facts."
        )
        user_prompt = (
            f"Recent Conversation:\n{recent_turns or 'None'}\n\n"
            f"Verified Facts From NityaMed Database:\n{grounded_facts}\n\n"
            f"User Query: {user_text}"
        )

        if settings.gemini_api_key:
            url = (
                f"https://generativelanguage.googleapis.com/v1beta/models/"
                f"{settings.gemini_model}:generateContent?key={settings.gemini_api_key}"
            )
            try:
                resp = httpx.post(
                    url,
                    json={
                        "system_instruction": {"parts": [{"text": system_prompt}]},
                        "contents": [{"parts": [{"text": user_prompt}]}],
                        "generationConfig": {"temperature": 0.35, "maxOutputTokens": 220},
                    },
                    timeout=8.0,
                )
                resp.raise_for_status()
                candidates = resp.json().get("candidates") or []
                reply = (
                    candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                    if candidates
                    else ""
                ).strip()
                if reply:
                    return reply
            except Exception as exc:
                logger.warning("Gemini conversational reply skipped: %s", exc)

        if settings.hf_token:
            try:
                resp = httpx.post(
                    "https://router.huggingface.co/v1/chat/completions",
                    headers={"Authorization": f"Bearer {settings.hf_token}"},
                    json={
                        "model": settings.hf_llm_model,
                        "temperature": 0.35,
                        "max_tokens": 220,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                    },
                    timeout=10.0,
                )
                resp.raise_for_status()
                choices = resp.json().get("choices") or []
                reply = (choices[0].get("message", {}).get("content", "") if choices else "").strip()
                if reply:
                    return reply
            except Exception as exc:
                logger.warning("HF Router conversational reply skipped: %s", exc)

        return None
