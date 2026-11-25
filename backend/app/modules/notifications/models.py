"""SQLAlchemy model for deduplicated reminder and refill notification records."""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.modules.auth.models import utcnow

NOTIF_TYPES_SQL = "('dose_reminder', 'low_stock', 'refill_alert', 'system')"
DELIVERY_STATUS_SQL = "('scheduled', 'delivered', 'dismissed', 'failed')"


class Notification(Base):
    """Deduplicated notification record for reminders, refill alerts, and history."""

    __tablename__ = "notifications"
    __table_args__ = (
        CheckConstraint(f"notif_type IN {NOTIF_TYPES_SQL}", name="ck_notif_type"),
        CheckConstraint(f"delivery_status IN {DELIVERY_STATUS_SQL}", name="ck_notif_status"),
        Index("idx_notifications_user_sched", "user_id", "scheduled_for"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    personal_med_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("personal_medicines.id", ondelete="CASCADE"), nullable=True
    )
    notif_type: Mapped[str] = mapped_column(String(30), nullable=False)
    dedup_key: Mapped[str] = mapped_column(String(160), unique=True, nullable=False)
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivery_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="scheduled"
    )
    payload_preview: Mapped[str] = mapped_column(String(160), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
