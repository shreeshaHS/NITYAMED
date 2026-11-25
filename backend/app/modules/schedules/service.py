"""Service layer for schedule versioning, dose event materialization, and adherence state machine."""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.modules.audit.models import AuditLog
from app.modules.auth.models import PatientProfile, User
from app.modules.inventory.models import StockTransaction
from app.modules.inventory.service import apply_stock_transaction
from app.modules.medicines.models import PersonalMedicine
from app.modules.medicines.service import get_owned_medicine
from app.modules.schedules.models import DoseEvent, ScheduleVersion
from app.modules.schedules.rules import daily_slots_for_date
from app.modules.schedules.schemas import (
    DailyDoseItemResponse,
    DoseActionResponse,
    DoseConfirmRequest,
    DoseCorrectRequest,
    DoseSkipRequest,
    DoseSnoozeRequest,
    ScheduleCreateRequest,
    ScheduleVersionResponse,
)

CONFIRMED_DOSE_STATUSES = {"taken_on_time", "taken_late", "partially_taken"}


def _as_utc(dt: datetime) -> datetime:
    """Normalize naive datetimes (e.g. SQLite) to UTC-aware datetimes."""
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


def _get_user_profile_settings(db: Session, user_id: UUID) -> tuple[str, int, int]:
    """Return (timezone, ontime_window_min, expiry_cutoff_hours) for a patient."""
    profile = db.get(PatientProfile, user_id)
    if profile is None:
        return "Asia/Kolkata", 30, 4
    return profile.timezone, profile.ontime_window_min, profile.expiry_cutoff_hours


def _materialize_window(
    db: Session,
    med: PersonalMedicine,
    schedule: ScheduleVersion,
    tz_name: str,
    from_date: date,
    to_date: date,
) -> None:
    """Generate pending dose_events for schedule between local dates inclusive."""
    if schedule.is_prn:
        return

    tz = ZoneInfo(tz_name)
    start = max(from_date, schedule.start_date)
    end = min(to_date, schedule.end_date) if schedule.end_date else to_date
    cursor = start
    while cursor <= end:
        slots = daily_slots_for_date(
            frequency_type=schedule.frequency_type,
            schedule_rules=schedule.schedule_rules,
            start_date=schedule.start_date,
            end_date=schedule.end_date,
            is_prn=schedule.is_prn,
            target_date=cursor,
        )
        for slot_time, dose_qty in slots:
            scheduled_utc = datetime.combine(cursor, slot_time, tzinfo=tz).astimezone(UTC)
            db.add(
                DoseEvent(
                    user_id=med.user_id,
                    personal_med_id=med.id,
                    schedule_version_id=schedule.id,
                    scheduled_at=scheduled_utc,
                    expected_qty=dose_qty,
                    status="pending",
                )
            )
        cursor += timedelta(days=1)


def create_schedule_version(
    db: Session, user: User, med_id: UUID, payload: ScheduleCreateRequest
) -> ScheduleVersionResponse:
    """Create a new immutable schedule version and materialize upcoming dose events."""
    med = get_owned_medicine(db, user, med_id)
    tz_name, _, _ = _get_user_profile_settings(db, user.id)
    now = datetime.now(UTC)
    today_local = now.astimezone(ZoneInfo(tz_name)).date()

    current_active = db.scalar(
        select(ScheduleVersion).where(
            ScheduleVersion.personal_med_id == med.id,
            ScheduleVersion.effective_to.is_(None),
        )
    )
    next_version = 1
    if current_active is not None:
        current_active.effective_to = now
        next_version = current_active.version_number + 1
        # Remove only un-actioned future pending doses from superseded schedule; preserve history.
        db.execute(
            delete(DoseEvent).where(
                DoseEvent.schedule_version_id == current_active.id,
                DoseEvent.status == "pending",
                DoseEvent.scheduled_at > now,
            )
        )

    is_prn = payload.frequency_type == "as_needed"
    rules_dict = {
        "times": [{"time": s.time, "dose": str(s.dose)} for s in payload.times],
        "weekdays": payload.weekdays,
        "interval_days": payload.interval_days,
    }

    schedule = ScheduleVersion(
        personal_med_id=med.id,
        version_number=next_version,
        frequency_type=payload.frequency_type,
        schedule_rules=rules_dict,
        start_date=payload.start_date,
        end_date=payload.end_date,
        is_prn=is_prn,
        effective_from=now,
    )
    db.add(schedule)
    db.flush()

    from_date = max(today_local, payload.start_date)
    to_date = from_date + timedelta(days=payload.horizon_days - 1)
    _materialize_window(db, med, schedule, tz_name, from_date, to_date)

    db.commit()
    db.refresh(schedule)
    return ScheduleVersionResponse.model_validate(schedule)


def list_schedule_versions(
    db: Session, user: User, med_id: UUID
) -> list[ScheduleVersionResponse]:
    """Return all historical and active schedule versions for an owned medicine."""
    get_owned_medicine(db, user, med_id)
    rows = db.scalars(
        select(ScheduleVersion)
        .where(ScheduleVersion.personal_med_id == med_id)
        .order_by(ScheduleVersion.version_number.desc())
    ).all()
    return [ScheduleVersionResponse.model_validate(row) for row in rows]


def expire_overdue_doses(
    db: Session, user_id: UUID | None = None, now: datetime | None = None
) -> int:
    """Transition past-cutoff unanswered doses to 'expired_unconfirmed' (never taken/missed)."""
    current = now or datetime.now(UTC)
    stmt = select(DoseEvent).where(DoseEvent.status.in_(("pending", "snoozed")))
    if user_id is not None:
        stmt = stmt.where(DoseEvent.user_id == user_id)

    candidates = db.scalars(stmt).all()
    cutoff_cache: dict[UUID, int] = {}
    expired_count = 0

    for dose in candidates:
        if dose.user_id not in cutoff_cache:
            _, _, cutoff_hours = _get_user_profile_settings(db, dose.user_id)
            cutoff_cache[dose.user_id] = cutoff_hours
        cutoff = timedelta(hours=cutoff_cache[dose.user_id])
        if _as_utc(dose.scheduled_at) + cutoff <= current:
            dose.status = "expired_unconfirmed"
            expired_count += 1

    if expired_count > 0:
        db.commit()
    return expired_count


def _build_daily_item(dose: DoseEvent, med: PersonalMedicine) -> DailyDoseItemResponse:
    """Assemble DailyDoseItemResponse for a dose event and its parent medicine."""
    return DailyDoseItemResponse(
        id=dose.id,
        personal_med_id=dose.personal_med_id,
        schedule_version_id=dose.schedule_version_id,
        display_name=med.display_name,
        strength=med.strength,
        dosage_form=med.dosage_form,
        dose_unit=med.dose_unit,
        instructions=med.instructions,
        confirmed_stock=med.confirmed_stock,
        scheduled_at=_as_utc(dose.scheduled_at),
        expected_qty=dose.expected_qty,
        confirmed_qty=dose.confirmed_qty,
        status=dose.status,  # type: ignore[arg-type]
        snoozed_until=_as_utc(dose.snoozed_until) if dose.snoozed_until else None,
        actioned_at=_as_utc(dose.actioned_at) if dose.actioned_at else None,
    )


def get_daily_schedule(
    db: Session, user: User, target_date: date | None = None
) -> list[DailyDoseItemResponse]:
    """Return chronological dose events for target_date in the patient's timezone."""
    tz_name, _, _ = _get_user_profile_settings(db, user.id)
    tz = ZoneInfo(tz_name)
    now = datetime.now(UTC)
    expire_overdue_doses(db, user_id=user.id, now=now)

    local_day = target_date or now.astimezone(tz).date()
    day_start_utc = datetime.combine(local_day, datetime.min.time(), tzinfo=tz).astimezone(UTC)
    day_end_utc = day_start_utc + timedelta(days=1)

    rows = db.execute(
        select(DoseEvent, PersonalMedicine)
        .join(PersonalMedicine, DoseEvent.personal_med_id == PersonalMedicine.id)
        .where(
            DoseEvent.user_id == user.id,
            DoseEvent.scheduled_at >= day_start_utc,
            DoseEvent.scheduled_at < day_end_utc,
        )
        .order_by(DoseEvent.scheduled_at.asc())
    ).all()

    return [_build_daily_item(dose, med) for dose, med in rows]


def _get_owned_dose(db: Session, user: User, dose_id: UUID) -> tuple[DoseEvent, PersonalMedicine]:
    """Fetch dose event and its parent personal medicine after ownership verification."""
    dose = db.get(DoseEvent, dose_id)
    if dose is None or dose.user_id != user.id:
        raise AppError(404, "DOSE_EVENT_NOT_FOUND", "Dose event was not found")
    med = db.get(PersonalMedicine, dose.personal_med_id)
    if med is None:
        raise AppError(404, "MEDICINE_NOT_FOUND", "Parent medicine was not found")
    return dose, med


def confirm_dose(
    db: Session, user: User, dose_id: UUID, payload: DoseConfirmRequest
) -> DoseActionResponse:
    """Confirm a dose as taken on time, taken late, or partially taken, deducting stock."""
    if payload.client_event_id is not None:
        existing_dose = db.scalar(
            select(DoseEvent).where(
                DoseEvent.client_event_id == payload.client_event_id,
                DoseEvent.user_id == user.id,
            )
        )
        if existing_dose is not None:
            med = get_owned_medicine(db, user, existing_dose.personal_med_id)
            return DoseActionResponse(
                dose=_build_daily_item(existing_dose, med),
                updated_confirmed_stock=med.confirmed_stock,
                idempotent_replay=True,
                stock_reconciliation_recommended=False,
            )

    dose, med = _get_owned_dose(db, user, dose_id)
    if dose.status in CONFIRMED_DOSE_STATUSES:
        raise AppError(
            409,
            "DOSE_ALREADY_CONFIRMED",
            "Dose is already confirmed; use the correction endpoint to modify it",
        )

    _, ontime_min, _ = _get_user_profile_settings(db, user.id)
    actioned_at = _as_utc(payload.actioned_at) if payload.actioned_at else datetime.now(UTC)
    delta_sec = abs((actioned_at - _as_utc(dose.scheduled_at)).total_seconds())

    if payload.actual_qty < dose.expected_qty:
        new_status = "partially_taken"
    elif delta_sec <= ontime_min * 60:
        new_status = "taken_on_time"
    else:
        new_status = "taken_late"

    reconciliation_needed = med.confirmed_stock < payload.actual_qty
    dose.status = new_status
    dose.confirmed_qty = payload.actual_qty
    dose.actioned_at = actioned_at
    dose.snoozed_until = None
    dose.client_event_id = payload.client_event_id

    apply_stock_transaction(
        db,
        med,
        tx_type="DOSE_CONFIRMED",
        qty_delta=-payload.actual_qty,
        notes=f"Dose confirmed ({new_status})",
        dose_event_id=dose.id,
        client_event_id=payload.client_event_id,
        clamp_floor_zero=True,
    )

    db.commit()
    db.refresh(dose)
    db.refresh(med)
    return DoseActionResponse(
        dose=_build_daily_item(dose, med),
        updated_confirmed_stock=med.confirmed_stock,
        idempotent_replay=False,
        stock_reconciliation_recommended=reconciliation_needed,
    )


def skip_dose(
    db: Session, user: User, dose_id: UUID, payload: DoseSkipRequest
) -> DoseActionResponse:
    """Explicitly skip a dose with zero stock deduction."""
    if payload.client_event_id is not None:
        existing_dose = db.scalar(
            select(DoseEvent).where(
                DoseEvent.client_event_id == payload.client_event_id,
                DoseEvent.user_id == user.id,
            )
        )
        if existing_dose is not None:
            med = get_owned_medicine(db, user, existing_dose.personal_med_id)
            return DoseActionResponse(
                dose=_build_daily_item(existing_dose, med),
                updated_confirmed_stock=med.confirmed_stock,
                idempotent_replay=True,
            )

    dose, med = _get_owned_dose(db, user, dose_id)
    if dose.status in CONFIRMED_DOSE_STATUSES:
        raise AppError(
            409,
            "DOSE_ALREADY_CONFIRMED",
            "Dose was already confirmed; use the correction endpoint to change it to skipped",
        )

    dose.status = "explicitly_skipped"
    dose.confirmed_qty = Decimal("0.00")
    dose.actioned_at = datetime.now(UTC)
    dose.snoozed_until = None
    dose.client_event_id = payload.client_event_id
    db.commit()
    db.refresh(dose)
    return DoseActionResponse(
        dose=_build_daily_item(dose, med),
        updated_confirmed_stock=med.confirmed_stock,
        idempotent_replay=False,
    )


def snooze_dose(
    db: Session, user: User, dose_id: UUID, payload: DoseSnoozeRequest
) -> DoseActionResponse:
    """Snooze a pending or already-snoozed dose reminder."""
    dose, med = _get_owned_dose(db, user, dose_id)
    if dose.status not in {"pending", "snoozed"}:
        raise AppError(409, "INVALID_DOSE_STATE", f"Cannot snooze a dose in status '{dose.status}'")

    now = datetime.now(UTC)
    dose.status = "snoozed"
    dose.snoozed_until = now + timedelta(minutes=payload.minutes)
    db.commit()
    db.refresh(dose)
    return DoseActionResponse(
        dose=_build_daily_item(dose, med),
        updated_confirmed_stock=med.confirmed_stock,
    )


def correct_dose(
    db: Session, user: User, dose_id: UUID, payload: DoseCorrectRequest
) -> DoseActionResponse:
    """Correct an accidental dose confirmation or skip, reversing/adjusting stock with audit log."""
    dose, med = _get_owned_dose(db, user, dose_id)
    old_status = dose.status
    old_qty = dose.confirmed_qty

    prev_net_delta = db.scalar(
        select(func.coalesce(func.sum(StockTransaction.qty_delta), 0)).where(
            StockTransaction.dose_event_id == dose.id,
            StockTransaction.user_id == user.id,
        )
    )
    prev_net_dec = Decimal(str(prev_net_delta or 0)).quantize(Decimal("0.01"))
    target_net_dec = (
        -payload.new_qty if payload.new_status != "explicitly_skipped" else Decimal("0.00")
    ).quantize(Decimal("0.01"))
    adjustment_delta = (target_net_dec - prev_net_dec).quantize(Decimal("0.01"))

    reconciliation_needed = False
    if adjustment_delta != Decimal("0.00"):
        if adjustment_delta < 0 and med.confirmed_stock < abs(adjustment_delta):
            reconciliation_needed = True
        apply_stock_transaction(
            db,
            med,
            tx_type="CORRECTION_REVERSAL",
            qty_delta=adjustment_delta,
            notes=f"Audited dose correction ({old_status} -> {payload.new_status}): {payload.reason}",
            dose_event_id=dose.id,
            clamp_floor_zero=True,
        )

    dose.status = payload.new_status
    dose.confirmed_qty = payload.new_qty
    dose.actioned_at = datetime.now(UTC)

    db.add(
        AuditLog(
            user_id=user.id,
            actor_role=user.role,
            entity_type="dose_event",
            entity_id=dose.id,
            action="DOSE_CONFIRMATION_CORRECTED",
            metadata_json={
                "old_status": old_status,
                "new_status": payload.new_status,
                "old_qty": str(old_qty),
                "new_qty": str(payload.new_qty),
                "stock_delta": str(adjustment_delta),
                "reason": payload.reason,
            },
        )
    )

    db.commit()
    db.refresh(dose)
    db.refresh(med)
    return DoseActionResponse(
        dose=_build_daily_item(dose, med),
        updated_confirmed_stock=med.confirmed_stock,
        stock_reconciliation_recommended=reconciliation_needed,
    )
