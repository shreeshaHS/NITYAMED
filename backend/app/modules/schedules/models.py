"""SQLAlchemy models for immutable schedule versions and dose events."""

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.modules.auth.models import utcnow

FREQUENCY_TYPES_SQL = (
    "('once_daily', 'multiple_daily', 'alternate_day', "
    "'weekly', 'selected_weekdays', 'varying_dose', 'fixed_course', 'as_needed')"
)
DOSE_STATUS_SQL = (
    "('pending', 'snoozed', 'taken_on_time', 'taken_late', "
    "'explicitly_skipped', 'partially_taken', 'expired_unconfirmed')"
)


class ScheduleVersion(Base):
    """Immutable schedule specification version preserving historical regimen rules."""

    __tablename__ = "schedule_versions"
    __table_args__ = (
        CheckConstraint(f"frequency_type IN {FREQUENCY_TYPES_SQL}", name="ck_schedule_freq"),
        CheckConstraint("version_number >= 1", name="ck_schedule_version_pos"),
        CheckConstraint("end_date IS NULL OR end_date >= start_date", name="ck_schedule_dates"),
        UniqueConstraint("personal_med_id", "version_number", name="uq_schedule_med_version"),
        Index("idx_schedule_med_effective", "personal_med_id", "effective_to"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    personal_med_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("personal_medicines.id", ondelete="CASCADE"), nullable=False
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    frequency_type: Mapped[str] = mapped_column(String(30), nullable=False)
    schedule_rules: Mapped[dict] = mapped_column(JSON, nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_prn: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    dose_events: Mapped[list["DoseEvent"]] = relationship(back_populates="schedule_version")


class DoseEvent(Base):
    """Individual scheduled medication administration event with strict adherence states."""

    __tablename__ = "dose_events"
    __table_args__ = (
        CheckConstraint("expected_qty > 0", name="ck_dose_expected_pos"),
        CheckConstraint("confirmed_qty >= 0", name="ck_dose_confirmed_nonneg"),
        CheckConstraint(f"status IN {DOSE_STATUS_SQL}", name="ck_dose_status"),
        UniqueConstraint("schedule_version_id", "scheduled_at", name="uq_dose_sched_time"),
        Index("idx_dose_events_user_date", "user_id", "scheduled_at"),
        Index("idx_dose_events_med_status", "personal_med_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    personal_med_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("personal_medicines.id", ondelete="CASCADE"), nullable=False
    )
    schedule_version_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("schedule_versions.id", ondelete="RESTRICT"), nullable=False
    )
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expected_qty: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    confirmed_qty: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, default=Decimal("0.00")
    )
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending")
    snoozed_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    actioned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    client_event_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, unique=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )

    schedule_version: Mapped["ScheduleVersion"] = relationship(back_populates="dose_events")
