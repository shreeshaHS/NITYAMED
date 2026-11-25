"""Pydantic schemas for notification history and delivery status updates."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

NotifType = Literal["dose_reminder", "low_stock", "refill_alert", "system"]
DeliveryStatus = Literal["scheduled", "delivered", "dismissed", "failed"]


class NotificationResponse(BaseModel):
    """Serialized notification record."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    personal_med_id: UUID | None
    notif_type: NotifType
    dedup_key: str
    scheduled_for: datetime
    sent_at: datetime | None
    delivery_status: DeliveryStatus
    payload_preview: str
    created_at: datetime


class NotificationStatusUpdateRequest(BaseModel):
    """Update notification delivery/dismissal status."""

    delivery_status: Literal["delivered", "dismissed", "failed"]


class SweepSummaryResponse(BaseModel):
    """Summary returned by the protected maintenance sweep endpoint."""

    expired_doses_marked: int
    refill_alerts_created: int
