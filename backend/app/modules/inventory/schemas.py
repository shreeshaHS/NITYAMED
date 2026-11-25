"""Pydantic schemas for inventory management, stock ledger, and projections."""

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PurchaseRequest(BaseModel):
    """Payload to record purchased stock in packs/strips and/or loose units."""

    packs: int = Field(default=0, ge=0)
    loose_units: Decimal = Field(default=Decimal("0"), ge=0, max_digits=12, decimal_places=2)
    notes: str | None = Field(default=None, max_length=500)
    client_event_id: UUID | None = None

    @model_validator(mode="after")
    def validate_positive_addition(self) -> "PurchaseRequest":
        """Require a non-zero purchase quantity."""
        if self.packs == 0 and self.loose_units <= 0:
            raise ValueError("Purchase requires packs > 0 or loose_units > 0")
        return self


class StockAdjustmentRequest(BaseModel):
    """Payload for manual adjustments or expired/damaged/lost deductions."""

    tx_type: Literal["MANUAL_ADJUSTMENT", "EXPIRED_DAMAGED_LOST"]
    qty_delta: Decimal = Field(max_digits=12, decimal_places=2)
    notes: str = Field(min_length=2, max_length=500)
    client_event_id: UUID | None = None

    @model_validator(mode="after")
    def validate_delta(self) -> "StockAdjustmentRequest":
        """Ensure loss entries are negative and non-zero."""
        if self.qty_delta == 0:
            raise ValueError("qty_delta cannot be zero")
        if self.tx_type == "EXPIRED_DAMAGED_LOST" and self.qty_delta > 0:
            raise ValueError("EXPIRED_DAMAGED_LOST requires a negative qty_delta")
        return self


class PhysicalReconcileRequest(BaseModel):
    """Payload to reconcile recorded balance with physically counted stock."""

    actual_counted_stock: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    notes: str | None = Field(default=None, max_length=500)
    client_event_id: UUID | None = None


class StockTransactionResponse(BaseModel):
    """Serialized immutable stock ledger entry."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    personal_med_id: UUID
    dose_event_id: UUID | None
    tx_type: str
    qty_delta: Decimal
    balance_after: Decimal
    notes: str | None
    client_event_id: UUID | None
    created_at: datetime


class InventorySummaryItem(BaseModel):
    """Confirmed vs. projected stock balance for a personal medicine."""

    personal_med_id: UUID
    display_name: str
    stock_unit: str
    confirmed_stock: Decimal
    projected_upcoming_consumption: Decimal
    projected_stock_balance: Decimal
    projection_horizon_days: int
    is_estimate: bool = True
