"""Pydantic schemas for hybrid text and voice assistant endpoints."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

SupportedLang = Literal["en", "kn", "hi"]


class AssistantTextRequest(BaseModel):
    """Text query submitted to the NityaMed hybrid assistant."""

    text: str = Field(min_length=1, max_length=600)
    language_hint: SupportedLang | None = None


class AssistantConfirmRequest(BaseModel):
    """Explicit confirmation payload before executing a state-changing assistant action."""

    confirmation_token: UUID
    approved: bool


class AssistantResponse(BaseModel):
    """Structured response returned by the hybrid assistant."""

    reply_text: str
    transcript: str | None = None
    language: SupportedLang
    intent: str
    confidence: float
    classification_source: Literal["safety_guard", "rule", "ml_model", "llm_fallback", "clarification"]
    requires_confirmation: bool = False
    confirmation_token: UUID | None = None
    proposed_action: dict | None = None
    tts_audio_base64: str | None = None
    suggested_replies: list[str] = Field(default_factory=list)
