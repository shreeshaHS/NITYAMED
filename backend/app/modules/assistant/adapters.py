"""Swappable external STT, TTS, and bounded LLM adapter interfaces."""

from dataclasses import dataclass

from app.core.exceptions import AppError

ALLOWED_ASSISTANT_INTENTS: tuple[str, ...] = (
    "check_stock",
    "today_schedule",
    "next_dose",
    "medicine_info",
    "adherence_status",
    "refill_check",
    "confirm_dose",
    "update_stock_purchase",
    "out_of_scope",
)


@dataclass(slots=True)
class STTResult:
    """Result from speech-to-text transcription."""

    transcript: str
    detected_language: str | None = None


class STTAdapter:
    """Speech-to-text adapter interface (swappable with Whisper/Google/Bhashini/Sarvam)."""

    def transcribe(
        self, audio_bytes: bytes, filename: str, language_hint: str | None = None
    ) -> STTResult:
        """Transcribe audio bytes into text; raises clear 503 if no provider is configured."""
        raise AppError(
            503,
            "STT_PROVIDER_NOT_CONFIGURED",
            "Speech-to-text provider is not configured on this server; please use text mode or configure an STT adapter.",
        )


class TTSAdapter:
    """Text-to-speech adapter interface (returns base64 audio when configured)."""

    def synthesize_base64(self, text: str, language: str) -> str | None:
        """Synthesize reply text into base64 audio, or return None if unavailable."""
        return None


class BoundedLLMAdapter:
    """Bounded LLM adapter strictly limited to dialect disambiguation and verified-text simplification."""

    def classify_dialect_intent(self, text: str) -> tuple[str, float] | None:
        """Optionally disambiguate a low-confidence regional dialect utterance into an allowed intent.

        Returns (intent_name, confidence) or None if no external LLM provider is configured.
        """
        return None

    def simplify_or_translate(self, verified_text: str, target_language: str) -> str:
        """Return verified_text unchanged unless an external bounded LLM provider is enabled."""
        return verified_text
