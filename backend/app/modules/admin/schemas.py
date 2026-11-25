"""Pydantic schemas for system administrator catalogue and health endpoints."""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, EmailStr, Field

from app.modules.medicines.schemas import DosageForm


class AdminEducationPayload(BaseModel):
    """Required provenance-backed education payload for admin catalogue items."""

    category: str = Field(min_length=2, max_length=150)
    common_uses: str = Field(min_length=5)
    mechanism: str = Field(min_length=5)
    side_effects: str = Field(min_length=5)
    precautions: str = Field(min_length=5)
    additional_notes: str | None = None
    source_name: str = Field(min_length=2, max_length=200)
    source_url: str | None = None
    verified_at: date


class AdminCatalogueCreateRequest(BaseModel):
    """Payload to create a verified catalogue item with education metadata."""

    brand_name: str = Field(min_length=1, max_length=200)
    generic_name: str = Field(min_length=1, max_length=200)
    active_ingredients: str | None = None
    strength: str = Field(min_length=1, max_length=100)
    dosage_form: DosageForm
    standard_pack_size: Decimal | None = Field(default=None, gt=0)
    pack_unit: str | None = Field(default=None, max_length=30)
    manufacturer: str | None = Field(default=None, max_length=200)
    education: AdminEducationPayload


class AdminCatalogueUpdateRequest(BaseModel):
    """Partial update or deprecation for an existing catalogue entry."""

    brand_name: str | None = Field(default=None, min_length=1, max_length=200)
    generic_name: str | None = Field(default=None, min_length=1, max_length=200)
    standard_pack_size: Decimal | None = Field(default=None, gt=0)
    manufacturer: str | None = None
    is_verified: bool | None = None
    is_deprecated: bool | None = None


class AdminCatalogueListItem(BaseModel):
    """Catalogue row visible in the Admin management console (including deprecated status)."""

    id: str
    brand_name: str
    generic_name: str
    strength: str
    dosage_form: DosageForm
    standard_pack_size: Decimal | None
    manufacturer: str | None
    is_verified: bool
    is_deprecated: bool


class AdminHealthMetricsResponse(BaseModel):
    """Anonymized platform summary metrics (strictly zero patient PII)."""

    total_users: int
    verified_users: int
    email_backup_opt_in_users: int
    active_personal_medicines: int
    total_dose_events: int
    confirmed_dose_events: int
    expired_unconfirmed_events: int
    total_catalogue_items: int
    verified_catalogue_items: int
    deprecated_catalogue_items: int
    total_notifications: int
    smtp_configured: bool
    require_email_verification: bool
    ml_model_ready: bool
    ml_model_name: str | None


class AdminTestEmailRequest(BaseModel):
    """Payload to verify live SMTP mail delivery from Admin Console."""

    recipient_email: EmailStr


class AdminTestEmailResponse(BaseModel):
    """Result of SMTP test delivery."""

    sent: bool
    detail: str
