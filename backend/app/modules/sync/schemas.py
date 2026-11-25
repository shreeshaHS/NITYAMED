"""Pydantic schemas for offline mobile bootstrap and batch event synchronization."""

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.medicines.schemas import PersonalMedicineResponse
from app.modules.schedules.schemas import DailyDoseItemResponse, ScheduleVersionResponse

SyncEventType = Literal[
    "DOSE_CONFIRM",
    "DOSE_SKIP",
    "DOSE_CORRECTION",
    "STOCK_PURCHASE",
    "STOCK_ADJUST",
    "STOCK_RECONCILE",
]


class SyncEventItem(BaseModel):
    """Single queued offline operation sent from mobile SQLite outbox."""

    client_event_id: UUID
    event_type: SyncEventType
    dose_event_id: UUID | None = None
    personal_med_id: UUID | None = None
    payload: dict = Field(default_factory=dict)


class SyncBatchRequest(BaseModel):
    """Ordered batch of offline events to replay idempotently."""

    events: list[SyncEventItem] = Field(min_length=1, max_length=100)


class SyncEventResult(BaseModel):
    """Per-event synchronization outcome."""

    client_event_id: UUID
    status: Literal["applied", "duplicate_ignored", "rejected"]
    message: str
    updated_confirmed_stock: Decimal | None = None


class SyncBatchResponse(BaseModel):
    """Summary of batch offline synchronization."""

    results: list[SyncEventResult]
    applied_count: int
    duplicate_count: int
    rejected_count: int


class SyncBootstrapResponse(BaseModel):
    """Hydration snapshot for mobile SQLite (past 30 days + upcoming 14 days)."""

    synced_at: datetime
    medicines: list[PersonalMedicineResponse]
    active_schedules: list[ScheduleVersionResponse]
    dose_events: list[DailyDoseItemResponse]
