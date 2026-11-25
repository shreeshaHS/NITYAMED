"""SQLAlchemy models for medicine catalogue, verified education, and personal medicines."""

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
    Numeric,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.modules.auth.models import utcnow

DOSAGE_FORMS_SQL = "('tablet', 'capsule', 'syrup', 'injection', 'inhaler', 'drops', 'other')"
MED_STATUS_SQL = "('active', 'paused', 'completed', 'archived')"


class MedicineCatalogue(Base):
    """Curated shared medicine reference catalogue."""

    __tablename__ = "medicine_catalogue"
    __table_args__ = (
        CheckConstraint(f"dosage_form IN {DOSAGE_FORMS_SQL}", name="ck_catalogue_form"),
        CheckConstraint(
            "standard_pack_size IS NULL OR standard_pack_size > 0",
            name="ck_catalogue_pack_size",
        ),
        Index("idx_catalogue_brand_lower", func.lower("brand_name")),
        Index("idx_catalogue_generic_lower", func.lower("generic_name")),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    brand_name: Mapped[str] = mapped_column(String(200), nullable=False)
    generic_name: Mapped[str] = mapped_column(String(200), nullable=False)
    active_ingredients: Mapped[str | None] = mapped_column(Text, nullable=True)
    strength: Mapped[str] = mapped_column(String(100), nullable=False)
    dosage_form: Mapped[str] = mapped_column(String(30), nullable=False)
    standard_pack_size: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    pack_unit: Mapped[str | None] = mapped_column(String(30), nullable=True)
    manufacturer: Mapped[str | None] = mapped_column(String(200), nullable=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_deprecated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )

    education: Mapped["MedicineEducation | None"] = relationship(
        back_populates="catalogue_item", uselist=False, cascade="all, delete-orphan"
    )


class MedicineEducation(Base):
    """Source-attributed, non-diagnostic patient education linked to a catalogue item."""

    __tablename__ = "medicine_education"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    catalogue_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("medicine_catalogue.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    category: Mapped[str] = mapped_column(String(150), nullable=False)
    common_uses: Mapped[str] = mapped_column(Text, nullable=False)
    mechanism: Mapped[str] = mapped_column(Text, nullable=False)
    side_effects: Mapped[str] = mapped_column(Text, nullable=False)
    precautions: Mapped[str] = mapped_column(Text, nullable=False)
    additional_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_name: Mapped[str] = mapped_column(String(200), nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    verified_at: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )

    catalogue_item: Mapped["MedicineCatalogue"] = relationship(back_populates="education")


class PersonalMedicine(Base):
    """User-owned medicine entry separating prescribed dose from stock balance."""

    __tablename__ = "personal_medicines"
    __table_args__ = (
        CheckConstraint(f"dosage_form IN {DOSAGE_FORMS_SQL}", name="ck_personal_med_form"),
        CheckConstraint("dose_per_intake > 0", name="ck_personal_med_dose_pos"),
        CheckConstraint("confirmed_stock >= 0", name="ck_personal_med_stock_nonneg"),
        CheckConstraint(
            "units_per_pack IS NULL OR units_per_pack > 0",
            name="ck_personal_med_pack_pos",
        ),
        CheckConstraint(
            "low_stock_threshold IS NULL OR low_stock_threshold >= 0",
            name="ck_personal_med_threshold_nonneg",
        ),
        CheckConstraint(f"status IN {MED_STATUS_SQL}", name="ck_personal_med_status"),
        CheckConstraint(
            "is_custom OR (catalogue_id IS NOT NULL)",
            name="ck_personal_med_custom_or_catalogue",
        ),
        Index("idx_personal_meds_user_status", "user_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    catalogue_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("medicine_catalogue.id", ondelete="SET NULL"), nullable=True
    )
    is_custom: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    generic_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    strength: Mapped[str] = mapped_column(String(100), nullable=False)
    dosage_form: Mapped[str] = mapped_column(String(30), nullable=False)
    dose_per_intake: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    dose_unit: Mapped[str] = mapped_column(String(30), nullable=False)
    stock_unit: Mapped[str] = mapped_column(String(30), nullable=False)
    units_per_pack: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    confirmed_stock: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )
    low_stock_threshold: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )

    catalogue_item: Mapped["MedicineCatalogue | None"] = relationship()
