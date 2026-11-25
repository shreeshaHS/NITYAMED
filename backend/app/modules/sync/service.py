"""Service layer for offline mobile SQLite bootstrap and idempotent batch sync."""

from datetime import UTC, datetime, timedelta

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.modules.auth.models import User
from app.modules.inventory import service as inventory_service
from app.modules.inventory.models import StockTransaction
from app.modules.inventory.schemas import (
    PhysicalReconcileRequest,
    PurchaseRequest,
    StockAdjustmentRequest,
)
from app.modules.medicines.models import PersonalMedicine
from app.modules.medicines.schemas import PersonalMedicineResponse
from app.modules.schedules import service as schedules_service
from app.modules.schedules.models import DoseEvent, ScheduleVersion
from app.modules.schedules.schemas import (
    DoseConfirmRequest,
    DoseCorrectRequest,
    DoseSkipRequest,
    ScheduleVersionResponse,
)
from app.modules.sync.schemas import (
    SyncBatchRequest,
    SyncBatchResponse,
    SyncBootstrapResponse,
    SyncEventItem,
    SyncEventResult,
)


def _process_single_event(db: Session, user: User, item: SyncEventItem) -> SyncEventResult:
    """Route a single offline sync event to its domain service with idempotency."""
    try:
        if item.event_type == "DOSE_CONFIRM":
            if item.dose_event_id is None:
                raise AppError(422, "MISSING_DOSE_ID", "dose_event_id is required for DOSE_CONFIRM")
            req = DoseConfirmRequest(**{**item.payload, "client_event_id": item.client_event_id})
            res = schedules_service.confirm_dose(db, user, item.dose_event_id, req)
            return SyncEventResult(
                client_event_id=item.client_event_id,
                status="duplicate_ignored" if res.idempotent_replay else "applied",
                message="Dose confirmation synced",
                updated_confirmed_stock=res.updated_confirmed_stock,
            )

        if item.event_type == "DOSE_SKIP":
            if item.dose_event_id is None:
                raise AppError(422, "MISSING_DOSE_ID", "dose_event_id is required for DOSE_SKIP")
            req = DoseSkipRequest(client_event_id=item.client_event_id)
            res = schedules_service.skip_dose(db, user, item.dose_event_id, req)
            return SyncEventResult(
                client_event_id=item.client_event_id,
                status="duplicate_ignored" if res.idempotent_replay else "applied",
                message="Dose skip synced",
                updated_confirmed_stock=res.updated_confirmed_stock,
            )

        if item.event_type == "DOSE_CORRECTION":
            if item.dose_event_id is None:
                raise AppError(422, "MISSING_DOSE_ID", "dose_event_id is required for DOSE_CORRECTION")
            req = DoseCorrectRequest(**item.payload)
            res = schedules_service.correct_dose(db, user, item.dose_event_id, req)
            return SyncEventResult(
                client_event_id=item.client_event_id,
                status="applied",
                message="Dose correction synced",
                updated_confirmed_stock=res.updated_confirmed_stock,
            )

        if item.personal_med_id is None:
            raise AppError(422, "MISSING_MED_ID", f"personal_med_id is required for {item.event_type}")

        already_seen = db.scalar(
            select(StockTransaction).where(
                StockTransaction.client_event_id == item.client_event_id,
                StockTransaction.user_id == user.id,
            )
        )
        if already_seen is not None:
            return SyncEventResult(
                client_event_id=item.client_event_id,
                status="duplicate_ignored",
                message="Duplicate stock event already recorded",
                updated_confirmed_stock=already_seen.balance_after,
            )

        if item.event_type == "STOCK_PURCHASE":
            req = PurchaseRequest(**{**item.payload, "client_event_id": item.client_event_id})
            tx = inventory_service.record_purchase(db, user, item.personal_med_id, req)
        elif item.event_type == "STOCK_ADJUST":
            req = StockAdjustmentRequest(**{**item.payload, "client_event_id": item.client_event_id})
            tx = inventory_service.record_adjustment(db, user, item.personal_med_id, req)
        else:
            req = PhysicalReconcileRequest(**{**item.payload, "client_event_id": item.client_event_id})
            tx = inventory_service.reconcile_physical_stock(db, user, item.personal_med_id, req)

        return SyncEventResult(
            client_event_id=item.client_event_id,
            status="applied",
            message=f"{item.event_type} synced",
            updated_confirmed_stock=tx.balance_after,
        )
    except (AppError, ValidationError, ValueError) as exc:
        db.rollback()
        msg = exc.message if isinstance(exc, AppError) else str(exc)
        return SyncEventResult(
            client_event_id=item.client_event_id,
            status="rejected",
            message=msg,
        )


def process_sync_batch(
    db: Session, user: User, payload: SyncBatchRequest
) -> SyncBatchResponse:
    """Process an ordered batch of offline client events idempotently."""
    results = [_process_single_event(db, user, item) for item in payload.events]
    return SyncBatchResponse(
        results=results,
        applied_count=sum(1 for r in results if r.status == "applied"),
        duplicate_count=sum(1 for r in results if r.status == "duplicate_ignored"),
        rejected_count=sum(1 for r in results if r.status == "rejected"),
    )


def get_bootstrap_snapshot(db: Session, user: User) -> SyncBootstrapResponse:
    """Return active medicines, active schedule versions, and 44-day dose window for SQLite."""
    now = datetime.now(UTC)
    schedules_service.expire_overdue_doses(db, user_id=user.id, now=now)

    meds = db.scalars(
        select(PersonalMedicine)
        .where(PersonalMedicine.user_id == user.id, PersonalMedicine.status != "archived")
        .order_by(PersonalMedicine.display_name.asc())
    ).all()
    med_map = {m.id: m for m in meds}

    active_schedules = db.scalars(
        select(ScheduleVersion)
        .join(PersonalMedicine, ScheduleVersion.personal_med_id == PersonalMedicine.id)
        .where(
            PersonalMedicine.user_id == user.id,
            ScheduleVersion.effective_to.is_(None),
        )
    ).all()

    window_start = now - timedelta(days=30)
    window_end = now + timedelta(days=14)
    doses = db.scalars(
        select(DoseEvent)
        .where(
            DoseEvent.user_id == user.id,
            DoseEvent.scheduled_at >= window_start,
            DoseEvent.scheduled_at <= window_end,
        )
        .order_by(DoseEvent.scheduled_at.asc())
    ).all()

    dose_items = [
        schedules_service._build_daily_item(d, med_map[d.personal_med_id])
        for d in doses
        if d.personal_med_id in med_map
    ]

    return SyncBootstrapResponse(
        synced_at=now,
        medicines=[PersonalMedicineResponse.model_validate(m) for m in meds],
        active_schedules=[ScheduleVersionResponse.model_validate(s) for s in active_schedules],
        dose_events=dose_items,
    )
