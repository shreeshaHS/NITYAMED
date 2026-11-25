"""Pydantic schemas for medicine catalogue, education, and personal medicines."""

from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

DosageForm = Literal["tablet", "capsule", "syrup", "injection", "inhaler", "drops", "other"]
MedicineStatus = Literal["active", "paused", "completed", "archived"]

EDUCATION_DISCLAIMER = (
    "Informational reference only. NityaMed does not diagnose conditions or advise "
    "starting, stopping, or changing prescribed medicines. Consult a qualified doctor or pharmacist."
)
CUSTOM_EDUCATION_NOTICE = "Unverified custom entry — educational details unavailable."


class CatalogueItemResponse(BaseModel):
    """Search result item from the verified medicine catalogue."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    brand_name: str
    generic_name: str
    active_ingredients: str | None
    strength: str
    dosage_form: DosageForm
    standard_pack_size: Decimal | None
    pack_unit: str | None
    manufacturer: str | None
    is_verified: bool


class MedicineEducationResponse(BaseModel):
    """Verified, source-attributed patient education entry."""

    model_config = ConfigDict(from_attributes=True)

    catalogue_id: UUID
    category: str
    common_uses: str
    mechanism: str
    side_effects: str
    precautions: str
    additional_notes: str | None
    source_name: str
    source_url: str | None
    verified_at: date
    disclaimer: str = EDUCATION_DISCLAIMER


class PersonalMedicineCreateRequest(BaseModel):
    """Payload to add a catalogue-linked or custom personal medicine."""

    catalogue_id: UUID | None = None
    is_custom: bool = False
    display_name: str | None = Field(default=None, min_length=1, max_length=200)
    generic_name: str | None = Field(default=None, max_length=200)
    strength: str | None = Field(default=None, min_length=1, max_length=100)
    dosage_form: DosageForm | None = None

    dose_per_intake: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    dose_unit: str = Field(min_length=1, max_length=30)
    stock_unit: str = Field(min_length=1, max_length=30)
    units_per_pack: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=2)

    initial_packs: int = Field(default=0, ge=0)
    initial_loose_units: Decimal = Field(default=Decimal("0"), ge=0, max_digits=12, decimal_places=2)
    low_stock_threshold: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    instructions: str | None = Field(default=None, max_length=1000)
    client_event_id: UUID | None = None

    @model_validator(mode="after")
    def validate_source_and_stock(self) -> "PersonalMedicineCreateRequest":
        """Ensure either catalogue_id or custom fields are present, and packs have pack size."""
        if not self.is_custom and self.catalogue_id is None:
            raise ValueError("Provide either catalogue_id or set is_custom=true")
        if self.is_custom:
            if not self.display_name or not self.strength or not self.dosage_form:
                raise ValueError("Custom medicines require display_name, strength, and dosage_form")
        return self


class PersonalMedicineUpdateRequest(BaseModel):
    """Partial update for personal medicine settings or lifecycle status."""

    display_name: str | None = Field(default=None, min_length=1, max_length=200)
    dose_per_intake: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=2)
    dose_unit: str | None = Field(default=None, min_length=1, max_length=30)
    units_per_pack: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=2)
    low_stock_threshold: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    instructions: str | None = Field(default=None, max_length=1000)
    status: MedicineStatus | None = None


class PersonalMedicineResponse(BaseModel):
    """Patient personal medicine keeping prescribed dose separate from stock balance."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    catalogue_id: UUID | None
    is_custom: bool
    display_name: str
    generic_name: str | None
    strength: str
    dosage_form: DosageForm
    dose_per_intake: Decimal
    dose_unit: str
    stock_unit: str
    units_per_pack: Decimal | None
    confirmed_stock: Decimal
    low_stock_threshold: Decimal | None
    instructions: str | None
    status: MedicineStatus
    created_at: datetime
    updated_at: datetime


class PersonalMedicineDetailResponse(BaseModel):
    """Detailed personal medicine view including verified education or custom fallback notice."""

    medicine: PersonalMedicineResponse
    education: MedicineEducationResponse | None
    education_notice: str | None = None
