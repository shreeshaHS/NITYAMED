"""SQLAlchemy model for multi-turn assistant dialogue and confirmation tokens."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, JSON, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.modules.auth.models import utcnow


class ConversationState(Base):
    """Short-lived assistant dialogue context and staged confirmation payload."""

    __tablename__ = "conversation_states"
    __table_args__ = (Index("idx_conv_user_exp", "user_id", "expires_at"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    active_intent: Mapped[str | None] = mapped_column(String(80), nullable=True)
    context_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    pending_action: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    confirmation_token: Mapped[uuid.UUID | None] = mapped_column(Uuid, unique=True, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )
