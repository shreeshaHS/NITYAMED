"""Hybrid voice and text assistant orchestrator with dialogue state and confirmation gates."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
import uuid
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.modules.assistant.adapters import (
    ALLOWED_ASSISTANT_INTENTS,
    BoundedLLMAdapter,
    STTAdapter,
    TTSAdapter,
)
from app.modules.assistant.models import ConversationState
from app.modules.assistant.nlp import (
    classify_intent,
    detect_language,
    extract_quantity_and_unit,
    extract_time_window,
    match_user_medicines,
    normalize_text,
    parse_voice_confirmation_reply,
)
from app.modules.assistant.schemas import AssistantConfirmRequest, AssistantResponse
from app.modules.auth.models import PatientProfile, User
from app.modules.inventory import service as inventory_service
from app.modules.inventory.schemas import PurchaseRequest
from app.modules.medicines.models import MedicineCatalogue, PersonalMedicine
from app.modules.medicines.service import _ensure_catalogue_education
from app.modules.refill.service import get_refill_predictions
from app.modules.schedules import service as schedules_service
from app.modules.schedules.models import DoseEvent
from app.modules.schedules.schemas import DoseConfirmRequest

_CLINICAL_REFUSAL = {
    "en": (
        "I cannot give medical advice, diagnose conditions, or recommend changing or stopping prescribed medicines. "
        "Please consult your doctor or pharmacist."
    ),
    "kn": (
        "ನಾನು ವೈದ್ಯಕೀಯ ಸಲಹೆ ನೀಡಲು ಅಥವಾ ಔಷಧಿ ಬದಲಾಯಿಸಲು ಶಿಫಾರಸು ಮಾಡಲು ಸಾಧ್ಯವಿಲ್ಲ. "
        "ದಯವಿಟ್ಟು ನಿಮ್ಮ ವೈದ್ಯರು ಅಥವಾ ಫಾರ್ಮಸಿಸ್ಟ್ ಅವರನ್ನು ಸಂಪರ್ಕಿಸಿ."
    ),
    "hi": (
        "मैं चिकित्सीय सलाह नहीं दे सकता और न ही दवा बदलने या बंद करने की सिफारिश कर सकता हूँ। "
        "कृपया अपने डॉक्टर या फार्मासिस्ट से सलाह लें।"
    ),
}

_OOS_REPLY = {
    "en": (
        "I did not understand that as a medication continuity request. You can ask about today's schedule, "
        "remaining stock, next dose, refill date, medicine uses, or confirm a dose."
    ),
    "kn": (
        "ಇದು ಔಷಧಿ ನಿರ್ವಹಣೆಗೆ ಸಂಬಂಧಿಸಿದ ಪ್ರಶ್ನೆಯಂತೆ ಕಾಣುತ್ತಿಲ್ಲ. ಇಂದಿನ ಶೆಡ್ಯೂಲ್, ಸ್ಟಾಕ್, ಮುಂದಿನ ಡೋಸ್, "
        "ರಿಫಿಲ್ ಅಥವಾ ಮಾತ್ರೆಯ ಮಾಹಿತಿ ಬಗ್ಗೆ ಕೇಳಬಹುದು."
    ),
    "hi": (
        "मैं इसे दवाई प्रबंधन से जुड़ा अनुरोध नहीं समझ पाया। आप आज के शेड्यूल, बचे हुए स्टॉक, अगली डोज़, "
        "रीफिल या दवा की जानकारी के बारे में पूछ सकते हैं।"
    ),
}


_LOCALIZED_PREFIXES: dict[str, dict[str, str]] = {
    "stock_empty": {
        "en": "You currently have no active medicines in your inventory.",
        "kn": "ನಿಮ್ಮ ಸ್ಟಾಕ್‌ನಲ್ಲಿ ಸದ್ಯಕ್ಕೆ ಯಾವುದೇ ಸಕ್ರಿಯ ಔಷಧಿಗಳಿಲ್ಲ.",
        "hi": "आपके स्टॉक में अभी कोई सक्रिय दवाई दर्ज नहीं है।",
    },
    "stock_header": {
        "en": "Remaining confirmed stock — ",
        "kn": "ಬಾಕಿ ಇರುವ ದೃಢೀಕೃತ ಸ್ಟಾಕ್ — ",
        "hi": "बचा हुआ कन्फर्म स्टॉक — ",
    },
    "schedule_empty": {
        "en": "You have no scheduled doses remaining for that period today.",
        "kn": "ಇಂದು ಆ ಸಮಯಕ್ಕೆ ಯಾವುದೇ ಬಾಕಿ ಡೋಸ್ ನಿಗದಿಯಾಗಿಲ್ಲ.",
        "hi": "आज उस समय के लिए कोई निर्धारित डोज़ शेष नहीं है।",
    },
    "schedule_header": {
        "en": "Today's schedule: ",
        "kn": "ಇಂದಿನ ಔಷಧಿ ಶೆಡ್ಯೂಲ್: ",
        "hi": "आज का दवाई शेड्यूल: ",
    },
    "next_empty": {
        "en": "You have no upcoming scheduled doses right now.",
        "kn": "ಸದ್ಯಕ್ಕೆ ಮುಂದಿನ ಯಾವುದೇ ನಿಗದಿತ ಡೋಸ್ ಇಲ್ಲ.",
        "hi": "अभी आगे कोई निर्धारित डोज़ नहीं है।",
    },
    "confirm_dose_prompt": {
        "en": "Please confirm: mark {name} ({qty} {unit}) as taken?",
        "kn": "ದಯವಿಟ್ಟು ದೃಢೀಕರಿಸಿ: {name} ({qty} {unit}) ತೆಗೆದುಕೊಂಡಿದ್ದೀರಿ ಎಂದು ಗುರುತಿಸಲೇ?",
        "hi": "कृपया कन्फर्म करें: क्या {name} ({qty} {unit}) को लिया गया मार्क करें?",
    },
    "confirm_stock_prompt": {
        "en": "Do you want to add {qty} {unit}(s) to {name}?",
        "kn": "{name} ಸ್ಟಾಕ್‌ಗೆ {qty} {unit} ಸೇರಿಸಲೇ?",
        "hi": "क्या {name} के स्टॉक में {qty} {unit} जोड़ दें?",
    },
    "cancelled": {
        "en": "Action cancelled. No changes were made.",
        "kn": "ಕ್ರಿಯೆಯನ್ನು ರದ್ದುಗೊಳಿಸಲಾಗಿದೆ. ಯಾವುದೇ ಬದಲಾವಣೆ ಮಾಡಲಾಗಿಲ್ಲ.",
        "hi": "कार्रवाई रद्द कर दी गई। कोई बदलाव नहीं किया गया।",
    },
}

_DIALECT_LLM_FALLBACK_THRESHOLD = 0.45


def _as_utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


def _get_or_create_dialogue_state(db: Session, user_id: uuid.UUID) -> ConversationState:
    now = datetime.now(UTC)
    state = db.scalar(
        select(ConversationState)
        .where(ConversationState.user_id == user_id)
        .order_by(ConversationState.updated_at.desc())
    )
    if state is None or _as_utc(state.expires_at) <= now:
        state = ConversationState(
            user_id=user_id,
            context_json={},
            expires_at=now + timedelta(minutes=15),
        )
        db.add(state)
        db.flush()
    return state


def _time_bucket(hour: int) -> str:
    if 5 <= hour < 12:
        return "morning"
    if 12 <= hour < 17:
        return "afternoon"
    if 17 <= hour < 22:
        return "evening"
    return "night"


def _resolve_target_medicine(
    norm_text: str,
    user_meds: list[PersonalMedicine],
    state: ConversationState,
) -> tuple[PersonalMedicine | None, str | None]:
    """Resolve a single medicine from utterance or recent dialogue context."""
    matched = match_user_medicines(norm_text, user_meds)
    if len(matched) == 1:
        return matched[0], None
    if len(matched) > 1:
        names = ", ".join(m.display_name for m in matched[:4])
        return None, f"I found multiple matching medicines ({names}). Which one do you mean?"

    last_id = (state.context_json or {}).get("last_medicine_id")
    if last_id:
        for m in user_meds:
            if str(m.id) == last_id:
                return m, None

    if len(user_meds) == 1:
        return user_meds[0], None
    if not user_meds:
        return None, "You do not have any active medicines added yet."
    return None, "Which medicine are you referring to? Please include its name."


def handle_text_query(
    db: Session,
    user: User,
    raw_text: str,
    language_hint: str | None = None,
    llm_adapter: BoundedLLMAdapter | None = None,
    tts_adapter: TTSAdapter | None = None,
    transcript: str | None = None,
) -> AssistantResponse:
    """Run the complete safety-guarded hybrid NLU pipeline for a text or transcribed query."""
    profile = db.get(PatientProfile, user.id)
    pref_lang = language_hint or (profile.preferred_lang if profile else "en")
    tz = ZoneInfo(profile.timezone if profile else "Asia/Kolkata")
    detected_lang = detect_language(raw_text, fallback=pref_lang)
    norm_text = normalize_text(raw_text)

    state = _get_or_create_dialogue_state(db, user.id)
    now_utc = datetime.now(UTC)
    if (
        state.pending_action is not None
        and state.confirmation_token is not None
        and _as_utc(state.expires_at) > now_utc
    ):
        voice_decision = parse_voice_confirmation_reply(norm_text)
        if voice_decision is not None:
            ctx = dict(state.context_json or {})
            ctx["last_language"] = detected_lang
            state.context_json = ctx
            resp = execute_confirmed_action(
                db,
                user,
                AssistantConfirmRequest(
                    confirmation_token=state.confirmation_token,
                    approved=voice_decision,
                ),
            )
            resp.transcript = transcript
            return resp

    intent, confidence, source = classify_intent(norm_text)
    llm = llm_adapter or BoundedLLMAdapter()
    tts = tts_adapter or TTSAdapter()

    # Hybrid fallback: if local ML has low confidence (e.g., unseen regional dialect),
    # let the Bounded LLM map ONLY to an allowed intent while keeping safety gates intact.
    if source == "ml_model" and confidence < _DIALECT_LLM_FALLBACK_THRESHOLD:
        fallback = llm.classify_dialect_intent(raw_text)
        if fallback is not None and fallback[0] in ALLOWED_ASSISTANT_INTENTS:
            intent, confidence = fallback[0], round(float(fallback[1]), 4)
            source = "llm_fallback"

    def _finalize(
        reply: str,
        *,
        final_intent: str = intent,
        final_source: str = source,
        requires_confirmation: bool = False,
        token: uuid.UUID | None = None,
        proposed_action: dict | None = None,
        med_id_context: uuid.UUID | None = None,
    ) -> AssistantResponse:
        ctx = dict(state.context_json or {})
        if med_id_context is not None:
            ctx["last_medicine_id"] = str(med_id_context)
        ctx["last_language"] = detected_lang
        state.active_intent = final_intent
        state.context_json = ctx
        state.expires_at = datetime.now(UTC) + timedelta(minutes=15)
        db.commit()

        localized_reply = llm.simplify_or_translate(reply, detected_lang)
        audio_b64 = tts.synthesize_base64(localized_reply, detected_lang)
        return AssistantResponse(
            reply_text=localized_reply,
            transcript=transcript,
            language=detected_lang,  # type: ignore[arg-type]
            intent=final_intent,
            confidence=confidence,
            classification_source=final_source,  # type: ignore[arg-type]
            requires_confirmation=requires_confirmation,
            confirmation_token=token,
            proposed_action=proposed_action,
            tts_audio_base64=audio_b64,
        )

    if intent == "out_of_scope_clinical":
        return _finalize(_CLINICAL_REFUSAL[detected_lang], final_source="safety_guard")

    if intent == "out_of_scope":
        return _finalize(_OOS_REPLY[detected_lang])

    active_meds = list(
        db.scalars(
            select(PersonalMedicine)
            .where(PersonalMedicine.user_id == user.id, PersonalMedicine.status == "active")
            .order_by(PersonalMedicine.display_name.asc())
        ).all()
    )

    # --- READ-ONLY INTENTS ---
    if intent == "check_stock":
        matched = match_user_medicines(norm_text, active_meds)
        targets = matched or active_meds
        if not targets:
            return _finalize(_LOCALIZED_PREFIXES["stock_empty"][detected_lang])
        lines = [f"{m.display_name}: {m.confirmed_stock} {m.stock_unit}" for m in targets]
        ctx_med = targets[0].id if len(targets) == 1 else None
        return _finalize(
            _LOCALIZED_PREFIXES["stock_header"][detected_lang] + "; ".join(lines) + ".",
            med_id_context=ctx_med,
        )

    if intent == "today_schedule":
        today_local = datetime.now(UTC).astimezone(tz).date()
        daily = schedules_service.get_daily_schedule(db, user, target_date=today_local)
        window = extract_time_window(norm_text)
        if window:
            daily = [d for d in daily if _time_bucket(d.scheduled_at.astimezone(tz).hour) == window]
        if not daily:
            return _finalize(_LOCALIZED_PREFIXES["schedule_empty"][detected_lang])
        parts = [
            f"{d.display_name} ({d.expected_qty} {d.dose_unit} at {d.scheduled_at.astimezone(tz).strftime('%H:%M')}, {d.status})"
            for d in daily
        ]
        return _finalize(
            _LOCALIZED_PREFIXES["schedule_header"][detected_lang] + "; ".join(parts) + ".",
            med_id_context=daily[0].personal_med_id,
        )

    if intent == "next_dose":
        now = datetime.now(UTC)
        schedules_service.expire_overdue_doses(db, user_id=user.id, now=now)
        next_row = db.execute(
            select(DoseEvent, PersonalMedicine)
            .join(PersonalMedicine, DoseEvent.personal_med_id == PersonalMedicine.id)
            .where(
                DoseEvent.user_id == user.id,
                DoseEvent.status.in_(("pending", "snoozed")),
                DoseEvent.scheduled_at >= now - timedelta(hours=1),
            )
            .order_by(DoseEvent.scheduled_at.asc())
        ).first()
        if next_row is None:
            return _finalize(_LOCALIZED_PREFIXES["next_empty"][detected_lang])
        dose, med = next_row
        local_dt = _as_utc(dose.scheduled_at).astimezone(tz)
        if detected_lang == "kn":
            msg = f"ನಿಮ್ಮ ಮುಂದಿನ ಡೋಸ್ {med.display_name} ({dose.expected_qty} {med.dose_unit}) — {local_dt.strftime('%Y-%m-%d %H:%M')}."
        elif detected_lang == "hi":
            msg = f"आपकी अगली डोज़ {med.display_name} ({dose.expected_qty} {med.dose_unit}) {local_dt.strftime('%Y-%m-%d %H:%M')} बजे है।"
        else:
            msg = f"Your next dose is {med.display_name} ({dose.expected_qty} {med.dose_unit}) at {local_dt.strftime('%Y-%m-%d %H:%M')}."
        return _finalize(msg, med_id_context=med.id)

    if intent == "adherence_status":
        today_local = datetime.now(UTC).astimezone(tz).date()
        daily = schedules_service.get_daily_schedule(db, user, target_date=today_local)
        window = extract_time_window(norm_text)
        if window:
            daily = [d for d in daily if _time_bucket(d.scheduled_at.astimezone(tz).hour) == window]
        if not daily:
            empty_msg = {
                "kn": "ಇಂದು ಆ ಸಮಯಕ್ಕೆ ಯಾವುದೇ ಡೋಸ್ ನಿಗದಿಯಾಗಿರಲಿಲ್ಲ.",
                "hi": "आज उस समय के लिए कोई डोज़ निर्धारित नहीं थी।",
            }.get(detected_lang, "No doses were scheduled for that time window today.")
            return _finalize(empty_msg)
        summary = "; ".join(
            f"{d.display_name} ({d.scheduled_at.astimezone(tz).strftime('%H:%M')}): {d.status}"
            for d in daily
        )
        prefix = {
            "kn": "ಇಂದಿನ ಡೋಸ್ ಸ್ಥಿತಿ: ",
            "hi": "आज की डोज़ स्थिति: ",
        }.get(detected_lang, "Today's dose status: ")
        return _finalize(prefix + summary + ".", med_id_context=daily[0].personal_med_id)

    if intent == "refill_check":
        preds = get_refill_predictions(db, user)
        med, err = _resolve_target_medicine(norm_text, active_meds, state)
        if med is not None:
            preds = [p for p in preds if p.personal_med_id == med.id]
        if not preds:
            no_refill_msg = err or {
                "kn": "ರಿಫಿಲ್ ಅಂದಾಜು ಮಾಹಿತಿ ಸದ್ಯಕ್ಕೆ ಲಭ್ಯವಿಲ್ಲ.",
                "hi": "रीफिल अनुमान की जानकारी अभी उपलब्ध नहीं है।",
            }.get(detected_lang, "No refill prediction data available.")
            return _finalize(no_refill_msg)
        lines = []
        for p in preds:
            if p.projected_depletion_date:
                dep_date = p.projected_depletion_date.isoformat()
                if detected_lang == "kn":
                    lines.append(
                        f"{p.display_name}: ಇನ್ನೂ ~{p.estimated_remaining_days} ದಿನ ಉಳಿದಿದೆ ({dep_date} ರ ಸುಮಾರಿಗೆ ಖಾಲಿಯಾಗುತ್ತದೆ)"
                    )
                elif detected_lang == "hi":
                    lines.append(
                        f"{p.display_name}: लगभग ~{p.estimated_remaining_days} दिन बचे हैं ({dep_date} के आसपास खत्म होगी)"
                    )
                else:
                    lines.append(
                        f"{p.display_name}: ~{p.estimated_remaining_days} days left (runs out around {dep_date})"
                    )
            else:
                lines.append(f"{p.display_name}: {p.reason}")
        refill_prefix = {
            "kn": "ರಿಫಿಲ್ ಸಾರಾಂಶ — ",
            "hi": "रीफिल सारांश — ",
        }.get(detected_lang, "Refill summary — ")
        return _finalize(refill_prefix + "; ".join(lines), med_id_context=med.id if med else None)

    if intent == "medicine_info":
        med, err = _resolve_target_medicine(norm_text, active_meds, state)
        if med is None:
            clarify_med = err or {
                "kn": "ದಯವಿಟ್ಟು ಯಾವ ಔಷಧಿಯ ಬಗ್ಗೆ ಮಾಹಿತಿ ಬೇಕು ಎಂಬುದನ್ನು ತಿಳಿಸಿ.",
                "hi": "कृपया बताएं कि आपको किस दवाई की जानकारी चाहिए।",
            }.get(detected_lang, "Please specify which medicine you want information about.")
            return _finalize(clarify_med, final_source="clarification")
        if med.is_custom or med.catalogue_id is None:
            custom_msg = {
                "kn": f"{med.display_name} ಕಸ್ಟಮ್ ಎಂಟ್ರಿಯಾಗಿರುವುದರಿಂದ ಪರಿಶೀಲಿತ ಶೈಕ್ಷಣಿಕ ಮಾಹಿತಿ ಲಭ್ಯವಿಲ್ಲ.",
                "hi": f"{med.display_name} एक कस्टम दवाई एंट्री है, इसलिए सत्यापित शैक्षिक जानकारी उपलब्ध नहीं है।",
            }.get(
                detected_lang,
                f"{med.display_name} is a custom medicine entry, so verified educational reference details are unavailable.",
            )
            return _finalize(custom_msg, med_id_context=med.id)
        cat = db.get(MedicineCatalogue, med.catalogue_id)
        edu = _ensure_catalogue_education(db, cat) if cat else None
        if edu is None:
            unavail_msg = {
                "kn": f"{med.display_name} ಗಾಗಿ ಪರಿಶೀಲಿತ ಮಾಹಿತಿ ಸದ್ಯಕ್ಕೆ ಲಭ್ಯವಿಲ್ಲ.",
                "hi": f"{med.display_name} के लिए सत्यापित जानकारी अभी उपलब्ध नहीं है।",
            }.get(
                detected_lang,
                f"Verified educational details for {med.display_name} are currently unavailable.",
            )
            return _finalize(unavail_msg, med_id_context=med.id)
        if detected_lang == "kn":
            info_msg = (
                f"{med.display_name} ({edu.category}) — ಉಪಯೋಗ: {edu.common_uses} "
                f"ಅಡ್ಡಪರಿಣಾಮಗಳು: {edu.side_effects} ಮುನ್ನೆಚ್ಚರಿಕೆ: {edu.precautions} "
                f"(ಮೂಲ: {edu.source_name}, {edu.verified_at.isoformat()})."
            )
        elif detected_lang == "hi":
            info_msg = (
                f"{med.display_name} ({edu.category}) — उपयोग: {edu.common_uses} "
                f"साइड इफेक्ट: {edu.side_effects} सावधानियां: {edu.precautions} "
                f"(स्रोत: {edu.source_name}, {edu.verified_at.isoformat()})."
            )
        else:
            info_msg = (
                f"{med.display_name} ({edu.category}): {edu.common_uses} Common side effects: {edu.side_effects} "
                f"Precautions: {edu.precautions} (Source: {edu.source_name}, verified {edu.verified_at.isoformat()})."
            )
        return _finalize(info_msg, med_id_context=med.id)

    # --- STATE-CHANGING INTENTS (STRICT CONFIRMATION GATE) ---
    if intent == "confirm_dose":
        today_local = datetime.now(UTC).astimezone(tz).date()
        daily = schedules_service.get_daily_schedule(db, user, target_date=today_local)
        pending = [d for d in daily if d.status in {"pending", "snoozed"}]

        med, _ = _resolve_target_medicine(norm_text, active_meds, state)
        if med is not None:
            pending = [d for d in pending if d.personal_med_id == med.id]

        window = extract_time_window(norm_text)
        if window and len(pending) > 1:
            windowed = [d for d in pending if _time_bucket(d.scheduled_at.astimezone(tz).hour) == window]
            if windowed:
                pending = windowed

        if not pending:
            no_pending_msg = {
                "kn": "ಇಂದು ದೃಢೀಕರಿಸಲು ಯಾವುದೇ ಬಾಕಿ ಡೋಸ್ ಕಂಡುಬಂದಿಲ್ಲ.",
                "hi": "आज कन्फर्म करने के लिए कोई लंबित डोज़ नहीं मिली।",
            }.get(detected_lang, "No pending scheduled dose matched your request today.")
            return _finalize(no_pending_msg, final_source="clarification")
        if len(pending) > 1:
            options = ", ".join(
                f"{d.display_name} ({d.scheduled_at.astimezone(tz).strftime('%H:%M')})" for d in pending[:4]
            )
            multi_msg = {
                "kn": f"ಒಂದಕ್ಕಿಂತ ಹೆಚ್ಚು ಬಾಕಿ ಡೋಸ್‌ಗಳಿವೆ ({options}). ದಯವಿಟ್ಟು ಔಷಧಿಯ ಹೆಸರು ಅಥವಾ ಸಮಯ ತಿಳಿಸಿ.",
                "hi": f"कई लंबित डोज़ मिली हैं ({options})। कृपया दवाई का नाम या समय बताएं।",
            }.get(
                detected_lang,
                f"Multiple pending doses found ({options}). Please mention which medicine or time you took.",
            )
            return _finalize(multi_msg, final_source="clarification")

        target_dose = pending[0]
        spoken_qty, is_pack = extract_quantity_and_unit(norm_text)
        actual_qty = (
            spoken_qty.quantize(Decimal("0.01"))
            if spoken_qty is not None
            and not is_pack
            and Decimal("0") < spoken_qty <= target_dose.expected_qty * Decimal("4")
            else target_dose.expected_qty
        )
        token = uuid.uuid4()
        proposed = {
            "action_type": "confirm_dose",
            "dose_event_id": str(target_dose.id),
            "personal_med_id": str(target_dose.personal_med_id),
            "medicine_name": target_dose.display_name,
            "actual_qty": str(actual_qty),
            "unit": target_dose.dose_unit,
        }
        state.pending_action = proposed
        state.confirmation_token = token
        return _finalize(
            _LOCALIZED_PREFIXES["confirm_dose_prompt"][detected_lang].format(
                name=target_dose.display_name,
                qty=actual_qty,
                unit=target_dose.dose_unit,
            ),
            requires_confirmation=True,
            token=token,
            proposed_action=proposed,
            med_id_context=target_dose.personal_med_id,
        )

    if intent == "update_stock_purchase":
        med, err = _resolve_target_medicine(norm_text, active_meds, state)
        if med is None:
            return _finalize(err or "Which medicine did you purchase?", final_source="clarification")

        qty, is_pack = extract_quantity_and_unit(norm_text)
        if qty is None or qty <= 0:
            return _finalize(
                f"How many strips or {med.stock_unit}s of {med.display_name} did you purchase?",
                final_source="clarification",
                med_id_context=med.id,
            )

        if is_pack:
            if med.units_per_pack is None:
                return _finalize(
                    f"Pack size is not set for {med.display_name}. Please tell me the exact number of {med.stock_unit}s.",
                    final_source="clarification",
                    med_id_context=med.id,
                )
            packs = int(qty)
            loose = Decimal("0")
            total_units = (Decimal(packs) * med.units_per_pack).quantize(Decimal("0.01"))
        else:
            packs = 0
            loose = qty.quantize(Decimal("0.01"))
            total_units = loose

        token = uuid.uuid4()
        proposed = {
            "action_type": "update_stock_purchase",
            "personal_med_id": str(med.id),
            "medicine_name": med.display_name,
            "packs": packs,
            "loose_units": str(loose),
            "total_units_to_add": str(total_units),
            "unit": med.stock_unit,
        }
        state.pending_action = proposed
        state.confirmation_token = token
        return _finalize(
            _LOCALIZED_PREFIXES["confirm_stock_prompt"][detected_lang].format(
                name=med.display_name,
                qty=total_units,
                unit=med.stock_unit,
            ),
            requires_confirmation=True,
            token=token,
            proposed_action=proposed,
            med_id_context=med.id,
        )

    return _finalize(_OOS_REPLY[detected_lang])


def execute_confirmed_action(
    db: Session,
    user: User,
    payload: AssistantConfirmRequest,
) -> AssistantResponse:
    """Execute or cancel a staged assistant mutation after explicit user confirmation."""
    now = datetime.now(UTC)
    state = db.scalar(
        select(ConversationState).where(
            ConversationState.confirmation_token == payload.confirmation_token,
            ConversationState.user_id == user.id,
        )
    )
    if state is None or state.pending_action is None or _as_utc(state.expires_at) <= now:
        raise AppError(
            404,
            "CONFIRMATION_TOKEN_INVALID",
            "Confirmation prompt has expired or does not exist",
        )

    pending = dict(state.pending_action)
    lang = (state.context_json or {}).get("last_language", "en")
    state.pending_action = None
    state.confirmation_token = None

    if not payload.approved:
        db.commit()
        return AssistantResponse(
            reply_text=_LOCALIZED_PREFIXES["cancelled"].get(lang, _LOCALIZED_PREFIXES["cancelled"]["en"]),
            language=lang,  # type: ignore[arg-type]
            intent=pending.get("action_type", "cancelled"),
            confidence=1.0,
            classification_source="rule",
            requires_confirmation=False,
        )

    action_type = pending.get("action_type")
    if action_type == "confirm_dose":
        res = schedules_service.confirm_dose(
            db,
            user,
            uuid.UUID(pending["dose_event_id"]),
            DoseConfirmRequest(
                actual_qty=Decimal(pending["actual_qty"]),
                client_event_id=uuid.uuid4(),
            ),
        )
        if lang == "kn":
            confirm_reply = (
                f"{pending['medicine_name']} ತೆಗೆದುಕೊಂಡಿದ್ದೀರಿ ಎಂದು ದಾಖಲಿಸಲಾಗಿದೆ ({res.dose.status}). "
                f"ಬಾಕಿ ಸ್ಟಾಕ್: {res.updated_confirmed_stock} {pending['unit']}."
            )
        elif lang == "hi":
            confirm_reply = (
                f"{pending['medicine_name']} को लिया गया मार्क कर दिया गया है ({res.dose.status})। "
                f"बचा स्टॉक: {res.updated_confirmed_stock} {pending['unit']}।"
            )
        else:
            confirm_reply = (
                f"Confirmed {pending['medicine_name']} as {res.dose.status}. "
                f"Remaining stock: {res.updated_confirmed_stock} {pending['unit']}(s)."
            )
        return AssistantResponse(
            reply_text=confirm_reply,
            language=lang,  # type: ignore[arg-type]
            intent="confirm_dose",
            confidence=1.0,
            classification_source="rule",
            requires_confirmation=False,
        )

    if action_type == "update_stock_purchase":
        tx = inventory_service.record_purchase(
            db,
            user,
            uuid.UUID(pending["personal_med_id"]),
            PurchaseRequest(
                packs=int(pending["packs"]),
                loose_units=Decimal(pending["loose_units"]),
                notes="Added via NityaMed assistant after confirmation",
                client_event_id=uuid.uuid4(),
            ),
        )
        if lang == "kn":
            stock_reply = (
                f"{pending['medicine_name']} ಸ್ಟಾಕ್‌ಗೆ +{pending['total_units_to_add']} {pending['unit']} ಸೇರಿಸಲಾಗಿದೆ. "
                f"ಹೊಸ ದೃಢೀಕೃತ ಸ್ಟಾಕ್: {tx.balance_after}."
            )
        elif lang == "hi":
            stock_reply = (
                f"{pending['medicine_name']} के स्टॉक में +{pending['total_units_to_add']} {pending['unit']} जोड़ दिए गए हैं। "
                f"नया कन्फर्म स्टॉक: {tx.balance_after}।"
            )
        else:
            stock_reply = (
                f"Updated {pending['medicine_name']} stock by +{pending['total_units_to_add']} {pending['unit']}(s). "
                f"New confirmed balance: {tx.balance_after}."
            )
        return AssistantResponse(
            reply_text=stock_reply,
            language=lang,  # type: ignore[arg-type]
            intent="update_stock_purchase",
            confidence=1.0,
            classification_source="rule",
            requires_confirmation=False,
        )

    raise AppError(400, "UNSUPPORTED_PENDING_ACTION", "Unsupported assistant action")
