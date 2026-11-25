"""REST API routes for NityaMed's hybrid voice and text assistant."""

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.assistant import service
from app.modules.assistant.adapters import BoundedLLMAdapter, STTAdapter
from app.modules.assistant.schemas import (
    AssistantConfirmRequest,
    AssistantResponse,
    AssistantTextRequest,
    SupportedLang,
)
from app.modules.auth.dependencies import require_role
from app.modules.auth.models import User

assistant_router = APIRouter(prefix="/assistant", tags=["Hybrid Voice Assistant"])


def get_stt_adapter() -> STTAdapter:
    """Dependency provider for STTAdapter (overrideable for cloud STT or tests)."""
    return STTAdapter()


def get_llm_adapter() -> BoundedLLMAdapter:
    """Dependency provider for BoundedLLMAdapter (overrideable for dialect LLM fallback)."""
    return BoundedLLMAdapter()


@assistant_router.post("/text", response_model=AssistantResponse)
def assistant_text_query(
    payload: AssistantTextRequest,
    current_user: User = Depends(require_role("patient")),
    llm_adapter: BoundedLLMAdapter = Depends(get_llm_adapter),
    db: Session = Depends(get_db),
) -> AssistantResponse:
    """Process a patient text query through rules, custom ML intent model, and safety gates."""
    return service.handle_text_query(
        db,
        current_user,
        raw_text=payload.text,
        language_hint=payload.language_hint,
        llm_adapter=llm_adapter,
    )


@assistant_router.post("/voice", response_model=AssistantResponse)
async def assistant_voice_query(
    audio: UploadFile = File(...),
    language_hint: SupportedLang | None = Form(default=None),
    current_user: User = Depends(require_role("patient")),
    stt_adapter: STTAdapter = Depends(get_stt_adapter),
    llm_adapter: BoundedLLMAdapter = Depends(get_llm_adapter),
    db: Session = Depends(get_db),
) -> AssistantResponse:
    """Transcribe voice audio via STT adapter and process through the hybrid assistant pipeline."""
    audio_bytes = await audio.read()
    stt_result = stt_adapter.transcribe(
        audio_bytes,
        filename=audio.filename or "voice.wav",
        language_hint=language_hint,
    )
    return service.handle_text_query(
        db,
        current_user,
        raw_text=stt_result.transcript,
        language_hint=language_hint or stt_result.detected_language,
        llm_adapter=llm_adapter,
        transcript=stt_result.transcript,
    )


@assistant_router.post("/confirm", response_model=AssistantResponse)
def confirm_assistant_action(
    payload: AssistantConfirmRequest,
    current_user: User = Depends(require_role("patient")),
    db: Session = Depends(get_db),
) -> AssistantResponse:
    """Execute or cancel a staged assistant mutation after explicit user confirmation."""
    return service.execute_confirmed_action(db, current_user, payload)
