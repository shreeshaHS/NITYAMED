"""Pydantic schemas for deterministic refill predictions and alerts."""

from datetime import date
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class RefillPredictionItem(BaseModel):
    """Deterministic refill calculation for a personal medicine."""

    personal_med_id: UUID
    display_name: str
    confirmed_stock: Decimal
    stock_unit: str
    prediction_mode: Literal[
        "scheduled_deterministic", "as_needed_threshold_only", "no_active_schedule", "not_applicable"
    ]
    estimated_remaining_days: int | None
    projected_depletion_date: date | None
    suggested_refill_alert_date: date | None
    should_alert_now: bool
    reason: str
