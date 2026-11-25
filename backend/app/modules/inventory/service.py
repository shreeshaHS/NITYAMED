"""Transactional, append-only inventory ledger and stock projection services."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.modules.auth.models import User
from app.modules.inventory.models import StockTransaction
from app.modules.inventory.schemas import (
    InventorySummaryItem,
    PhysicalReconcileRequest,
    PurchaseRequest,
    StockAdjustmentRequest,
    StockTransactionResponse,
)
from app.modules.medicines.models import PersonalMedicine
from app.modules.medicines.service import get_owned_medicine
from app.modules.schedules.models import DoseEvent


def apply_stock_transaction(
    db: Session,
    med: PersonalMedicine,
    tx_type: str,
    qty_delta: Decimal,
    notes: str | None = None,
    dose_event_id: UUID | None = None,
    client_event_id: UUID | None = None,
    clamp_floor_zero: bool = False,
) -> tuple[StockTransaction, bool]:
    """Append a stock ledger entry idempotently and update confirmed_stock.

    Returns (transaction_record, is_idempotent_replay).
    """
    if client_event_id is not None:
        existing = db.scalar(
            select(StockTransaction).where(
                StockTransaction.client_event_id == client_event_id,
                StockTransaction.user_id == med.user_id,
            )
        )
        if existing is not None:
            return existing, True

    new_balance = (med.confirmed_stock + qty_delta).quantize(Decimal("0.01"))
    applied_delta = qty_delta.quantize(Decimal("0.01"))
    resolved_notes = notes

    if new_balance < Decimal("0.00"):
        if not clamp_floor_zero:
            raise AppError(
                422,
                "NEGATIVE_STOCK_NOT_ALLOWED",
                f"Operation would reduce stock below zero (current: {med.confirmed_stock})",
            )
        applied_delta = -med.confirmed_stock
        new_balance = Decimal("0.00")
        suffix = "Confirmed at zero/insufficient recorded stock; reconciliation prompted"
        resolved_notes = f"{notes} ({suffix})" if notes else suffix

    med.confirmed_stock = new_balance
    tx = StockTransaction(
        user_id=med.user_id,
        personal_med_id=med.id,
        dose_event_id=dose_event_id,
        tx_type=tx_type,
        qty_delta=applied_delta,
        balance_after=new_balance,
        notes=resolved_notes,
        client_event_id=client_event_id,
    )
    db.add(tx)
    db.flush()
    return tx, False


def record_purchase(
    db: Session, user: User, med_id: UUID, payload: PurchaseRequest
) -> StockTransactionResponse:
    """Add purchased stock (packs/strips + loose units) to confirmed stock."""
    med = get_owned_medicine(db, user, med_id)
    if payload.packs > 0 and med.units_per_pack is None:
        raise AppError(
            422,
            "PACK_SIZE_REQUIRED",
            "units_per_pack must be configured on this medicine to add packs/strips",
        )

    pack_qty = (
        Decimal(payload.packs) * med.units_per_pack
        if payload.packs > 0 and med.units_per_pack is not None
        else Decimal("0.00")
    )
    total_added = (pack_qty + payload.loose_units).quantize(Decimal("0.01"))

    tx, is_replay = apply_stock_transaction(
        db,
        med,
        tx_type="PURCHASE",
        qty_delta=total_added,
        notes=payload.notes or f"Purchased {payload.packs} packs + {payload.loose_units} loose",
        client_event_id=payload.client_event_id,
    )
    if not is_replay:
        db.commit()
        db.refresh(tx)
    return StockTransactionResponse.model_validate(tx)


def record_adjustment(
    db: Session, user: User, med_id: UUID, payload: StockAdjustmentRequest
) -> StockTransactionResponse:
    """Record manual stock adjustment or expired/damaged/lost units."""
    med = get_owned_medicine(db, user, med_id)
    tx, is_replay = apply_stock_transaction(
        db,
        med,
        tx_type=payload.tx_type,
        qty_delta=payload.qty_delta,
        notes=payload.notes,
        client_event_id=payload.client_event_id,
    )
    if not is_replay:
        db.commit()
        db.refresh(tx)
    return StockTransactionResponse.model_validate(tx)


def reconcile_physical_stock(
    db: Session, user: User, med_id: UUID, payload: PhysicalReconcileRequest
) -> StockTransactionResponse:
    """Log physical count reconciliation delta without erasing ledger history."""
    med = get_owned_medicine(db, user, med_id)
    delta = (payload.actual_counted_stock - med.confirmed_stock).quantize(Decimal("0.01"))
    note = payload.notes or (
        f"Physical reconciliation: recorded {med.confirmed_stock} -> counted {payload.actual_counted_stock}"
    )

    tx, is_replay = apply_stock_transaction(
        db,
        med,
        tx_type="RECONCILIATION",
        qty_delta=delta,
        notes=note,
        client_event_id=payload.client_event_id,
    )
    if not is_replay:
        db.commit()
        db.refresh(tx)
    return StockTransactionResponse.model_validate(tx)


def list_transactions(
    db: Session, user: User, med_id: UUID, limit: int = 50
) -> list[StockTransactionResponse]:
    """Return chronological stock ledger history for an owned medicine."""
    get_owned_medicine(db, user, med_id)
    rows = db.scalars(
        select(StockTransaction)
        .where(
            StockTransaction.personal_med_id == med_id,
            StockTransaction.user_id == user.id,
        )
        .order_by(StockTransaction.created_at.desc())
        .limit(limit)
    ).all()
    return [StockTransactionResponse.model_validate(row) for row in rows]


def get_inventory_summary(
    db: Session, user: User, horizon_days: int = 14
) -> list[InventorySummaryItem]:
    """Return Confirmed Stock Balance alongside Projected Stock Balance (Estimate)."""
    now = datetime.now(UTC)
    horizon_end = now + timedelta(days=horizon_days)

    meds = db.scalars(
        select(PersonalMedicine)
        .where(PersonalMedicine.user_id == user.id, PersonalMedicine.status == "active")
        .order_by(PersonalMedicine.display_name.asc())
    ).all()

    summary: list[InventorySummaryItem] = []
    for med in meds:
        upcoming = db.scalar(
            select(func.coalesce(func.sum(DoseEvent.expected_qty), 0)).where(
                DoseEvent.personal_med_id == med.id,
                DoseEvent.status.in_(("pending", "snoozed")),
                DoseEvent.scheduled_at >= now,
                DoseEvent.scheduled_at <= horizon_end,
            )
        )
        upcoming_dec = Decimal(str(upcoming or 0)).quantize(Decimal("0.01"))
        projected = max(Decimal("0.00"), (med.confirmed_stock - upcoming_dec).quantize(Decimal("0.01")))
        summary.append(
            InventorySummaryItem(
                personal_med_id=med.id,
                display_name=med.display_name,
                stock_unit=med.stock_unit,
                confirmed_stock=med.confirmed_stock,
                projected_upcoming_consumption=upcoming_dec,
                projected_stock_balance=projected,
                projection_horizon_days=horizon_days,
                is_estimate=True,
            )
        )
    return summary
