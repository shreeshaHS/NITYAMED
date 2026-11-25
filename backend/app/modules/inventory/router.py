"""REST API routes for inventory ledger, purchases, adjustments, and reconciliation."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.auth.dependencies import require_role
from app.modules.auth.models import User
from app.modules.inventory import service
from app.modules.inventory.schemas import (
    InventorySummaryItem,
    PhysicalReconcileRequest,
    PurchaseRequest,
    StockAdjustmentRequest,
    StockTransactionResponse,
)

inventory_router = APIRouter(prefix="/inventory", tags=["Medicine Inventory"])


@inventory_router.get("/summary", response_model=list[InventorySummaryItem])
def inventory_summary(
    horizon_days: int = Query(default=14, ge=1, le=90),
    current_user: User = Depends(require_role("patient")),
    db: Session = Depends(get_db),
) -> list[InventorySummaryItem]:
    """Return confirmed vs. projected stock balances for active medicines."""
    return service.get_inventory_summary(db, current_user, horizon_days=horizon_days)


@inventory_router.get("/{med_id}/transactions", response_model=list[StockTransactionResponse])
def list_stock_transactions(
    med_id: UUID,
    limit: int = Query(default=50, ge=1, le=200),
    current_user: User = Depends(require_role("patient")),
    db: Session = Depends(get_db),
) -> list[StockTransactionResponse]:
    """Return immutable stock transaction history for a medicine."""
    return service.list_transactions(db, current_user, med_id, limit=limit)


@inventory_router.post("/{med_id}/purchase", response_model=StockTransactionResponse)
def purchase_stock(
    med_id: UUID,
    payload: PurchaseRequest,
    current_user: User = Depends(require_role("patient")),
    db: Session = Depends(get_db),
) -> StockTransactionResponse:
    """Record newly purchased strips/packs or loose units."""
    return service.record_purchase(db, current_user, med_id, payload)


@inventory_router.post("/{med_id}/adjust", response_model=StockTransactionResponse)
def adjust_stock(
    med_id: UUID,
    payload: StockAdjustmentRequest,
    current_user: User = Depends(require_role("patient")),
    db: Session = Depends(get_db),
) -> StockTransactionResponse:
    """Record manual adjustment or expired/damaged/lost deduction."""
    return service.record_adjustment(db, current_user, med_id, payload)


@inventory_router.post("/{med_id}/reconcile", response_model=StockTransactionResponse)
def reconcile_stock(
    med_id: UUID,
    payload: PhysicalReconcileRequest,
    current_user: User = Depends(require_role("patient")),
    db: Session = Depends(get_db),
) -> StockTransactionResponse:
    """Reconcile recorded balance against physically counted stock."""
    return service.reconcile_physical_stock(db, current_user, med_id, payload)
