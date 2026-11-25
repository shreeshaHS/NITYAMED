"""Pydantic schemas for medication schedules and adherence dose events."""

from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

FrequencyType = Literal[
    "once_daily",
    "multiple_daily",
    "alternate_day",
    "weekly",
    "selected_weekdays",
    "varying_dose",
    "fixed_course",
    "as_needed",
]

DoseStatus = Literal[
    "pending",
    "snoozed",
    "taken_on_time",
    "taken_late",
    "explicitly_skipped",
    "partially_taken",
    "expired_unconfirmed",
]


class ScheduleSlotInput(BaseModel):
    """Single scheduled time-of-day and expected dose quantity."""

    time: str = Field(pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    dose: Decimal = Field(gt=0, max_digits=10, decimal_places=2)


class ScheduleCreateRequest(BaseModel):
    """Payload to create a new immutable schedule version for a personal medicine."""

    frequency_type: FrequencyType
    times: list[ScheduleSlotInput] = Field(default_factory=list)
    weekdays: list[int] = Field(default_factory=list)
    interval_days: int = Field(default=2, ge=1, le=30)
    start_date: date
    end_date: date | None = None
    horizon_days: int = Field(default=14, ge=1, le=60)

    @field_validator("weekdays")
    @classmethod
    def validate_weekdays(cls, values: list[int]) -> list[int]:
        """Ensure weekday integers follow Python Monday=0..Sunday=6 convention."""
        for day in values:
            if day < 0 or day > 6:
                raise ValueError("Weekdays must be integers from 0 (Monday) to 6 (Sunday)")
        return sorted(set(values))

    @model_validator(mode="after")
    def validate_schedule_rules(self) -> "ScheduleCreateRequest":
        """Validate frequency-specific required fields and date ordering."""
        if self.end_date is not None and self.end_date < self.start_date:
            raise ValueError("end_date cannot precede start_date")
        if self.frequency_type == "fixed_course" and self.end_date is None:
            raise ValueError("fixed_course schedules require an end_date")
        if self.frequency_type != "as_needed" and not self.times:
            raise ValueError("Non-PRN schedules require at least one time slot")
        if self.frequency_type == "selected_weekdays" and not self.weekdays:
            raise ValueError("selected_weekdays requires at least one weekday (0-6)")
        return self


class ScheduleVersionResponse(BaseModel):
    """Serialized immutable schedule version."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    personal_med_id: UUID
    version_number: int
    frequency_type: FrequencyType
    schedule_rules: dict
    start_date: date
    end_date: date | None
    is_prn: bool
    effective_from: datetime
    effective_to: datetime | None


class DoseConfirmRequest(BaseModel):
    """Payload to confirm a dose as taken (full or partial)."""

    actual_qty: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    actioned_at: datetime | None = None
    client_event_id: UUID | None = None


class DoseSkipRequest(BaseModel):
    """Payload to explicitly skip a scheduled dose."""

    client_event_id: UUID | None = None


class DoseSnoozeRequest(BaseModel):
    """Payload to snooze a pending or snoozed dose."""

    minutes: int = Field(default=15, ge=5, le=120)


class DoseCorrectRequest(BaseModel):
    """Audited correction payload for accidental dose confirmation or skip."""

    new_status: Literal["taken_on_time", "taken_late", "partially_taken", "explicitly_skipped"]
    new_qty: Decimal = Field(default=Decimal("0"), ge=0, max_digits=10, decimal_places=2)
    reason: str = Field(min_length=3, max_length=300)

    @model_validator(mode="after")
    def validate_qty_for_status(self) -> "DoseCorrectRequest":
        """Ensure skipped corrections have 0 qty and taken corrections have > 0 qty."""
        if self.new_status == "explicitly_skipped" and self.new_qty != 0:
            raise ValueError("explicitly_skipped correction must have new_qty = 0")
        if self.new_status != "explicitly_skipped" and self.new_qty <= 0:
            raise ValueError("Taken/partial correction requires new_qty > 0")
        return self


class DailyDoseItemResponse(BaseModel):
    """Dose event enriched with medicine details for the Daily Schedule view."""

    id: UUID
    personal_med_id: UUID
    schedule_version_id: UUID
    display_name: str
    strength: str
    dosage_form: str
    dose_unit: str
    instructions: str | None
    confirmed_stock: Decimal
    scheduled_at: datetime
    expected_qty: Decimal
    confirmed_qty: Decimal
    status: DoseStatus
    snoozed_until: datetime | None
    actioned_at: datetime | None


class DoseActionResponse(BaseModel):
    """Response returned after confirming, skipping, snoozing, or correcting a dose."""

    dose: DailyDoseItemResponse
    updated_confirmed_stock: Decimal
    idempotent_replay: bool = False
    stock_reconciliation_recommended: bool = False
