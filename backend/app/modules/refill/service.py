"""Deterministic day-by-day refill depletion and alert predictor."""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.auth.models import PatientProfile, User
from app.modules.medicines.models import PersonalMedicine
from app.modules.refill.schemas import RefillPredictionItem
from app.modules.schedules.models import ScheduleVersion
from app.modules.schedules.rules import daily_slots_for_date


def predict_medicine_refill(
    med: PersonalMedicine,
    active_schedule: ScheduleVersion | None,
    refill_alert_days: int,
    today_local: date,
    max_horizon_days: int = 365,
) -> RefillPredictionItem:
    """Compute deterministic depletion and refill alert dates without ML guesswork."""
    if med.status != "active":
        return RefillPredictionItem(
            personal_med_id=med.id,
            display_name=med.display_name,
            confirmed_stock=med.confirmed_stock,
            stock_unit=med.stock_unit,
            prediction_mode="not_applicable",
            estimated_remaining_days=None,
            projected_depletion_date=None,
            suggested_refill_alert_date=None,
            should_alert_now=False,
            reason=f"Course status is '{med.status}'; refill alerts suppressed.",
        )

    threshold_triggered = (
        med.low_stock_threshold is not None and med.confirmed_stock <= med.low_stock_threshold
    )

    if active_schedule is None:
        return RefillPredictionItem(
            personal_med_id=med.id,
            display_name=med.display_name,
            confirmed_stock=med.confirmed_stock,
            stock_unit=med.stock_unit,
            prediction_mode="no_active_schedule",
            estimated_remaining_days=None,
            projected_depletion_date=None,
            suggested_refill_alert_date=None,
            should_alert_now=threshold_triggered,
            reason="No active schedule; static low-stock threshold evaluated.",
        )

    if active_schedule.is_prn or active_schedule.frequency_type == "as_needed":
        return RefillPredictionItem(
            personal_med_id=med.id,
            display_name=med.display_name,
            confirmed_stock=med.confirmed_stock,
            stock_unit=med.stock_unit,
            prediction_mode="as_needed_threshold_only",
            estimated_remaining_days=None,
            projected_depletion_date=None,
            suggested_refill_alert_date=None,
            should_alert_now=threshold_triggered,
            reason="As-needed (PRN) medicine does not assume fixed daily consumption.",
        )

    if active_schedule.end_date is not None and active_schedule.end_date < today_local:
        return RefillPredictionItem(
            personal_med_id=med.id,
            display_name=med.display_name,
            confirmed_stock=med.confirmed_stock,
            stock_unit=med.stock_unit,
            prediction_mode="not_applicable",
            estimated_remaining_days=None,
            projected_depletion_date=None,
            suggested_refill_alert_date=None,
            should_alert_now=False,
            reason="Fixed course end date has passed; refill alerts suppressed.",
        )

    if med.confirmed_stock <= Decimal("0.00"):
        return RefillPredictionItem(
            personal_med_id=med.id,
            display_name=med.display_name,
            confirmed_stock=med.confirmed_stock,
            stock_unit=med.stock_unit,
            prediction_mode="scheduled_deterministic",
            estimated_remaining_days=0,
            projected_depletion_date=today_local,
            suggested_refill_alert_date=today_local,
            should_alert_now=True,
            reason="Confirmed stock is currently empty.",
        )

    remaining = med.confirmed_stock
    depletion_date: date | None = None
    last_sim_date = today_local + timedelta(days=max_horizon_days)
    if active_schedule.end_date is not None and active_schedule.end_date < last_sim_date:
        last_sim_date = active_schedule.end_date

    cursor = today_local
    while cursor <= last_sim_date:
        slots = daily_slots_for_date(
            frequency_type=active_schedule.frequency_type,
            schedule_rules=active_schedule.schedule_rules,
            start_date=active_schedule.start_date,
            end_date=active_schedule.end_date,
            is_prn=active_schedule.is_prn,
            target_date=cursor,
        )
        day_consumption = sum((dose for _, dose in slots), Decimal("0.00"))
        if day_consumption > 0:
            remaining -= day_consumption
            if remaining <= Decimal("0.00"):
                depletion_date = cursor
                break
        cursor += timedelta(days=1)

    if depletion_date is None:
        if active_schedule.end_date is not None:
            return RefillPredictionItem(
                personal_med_id=med.id,
                display_name=med.display_name,
                confirmed_stock=med.confirmed_stock,
                stock_unit=med.stock_unit,
                prediction_mode="scheduled_deterministic",
                estimated_remaining_days=None,
                projected_depletion_date=None,
                suggested_refill_alert_date=None,
                should_alert_now=False,
                reason="Current confirmed stock covers the remaining fixed course.",
            )
        return RefillPredictionItem(
            personal_med_id=med.id,
            display_name=med.display_name,
            confirmed_stock=med.confirmed_stock,
            stock_unit=med.stock_unit,
            prediction_mode="scheduled_deterministic",
            estimated_remaining_days=max_horizon_days,
            projected_depletion_date=None,
            suggested_refill_alert_date=None,
            should_alert_now=threshold_triggered,
            reason=f"Supply exceeds {max_horizon_days}-day prediction window.",
        )

    remaining_days = max(0, (depletion_date - today_local).days)
    alert_date = depletion_date - timedelta(days=refill_alert_days)
    should_alert = (today_local >= alert_date) or threshold_triggered
    return RefillPredictionItem(
        personal_med_id=med.id,
        display_name=med.display_name,
        confirmed_stock=med.confirmed_stock,
        stock_unit=med.stock_unit,
        prediction_mode="scheduled_deterministic",
        estimated_remaining_days=remaining_days,
        projected_depletion_date=depletion_date,
        suggested_refill_alert_date=alert_date,
        should_alert_now=should_alert,
        reason=f"Deterministic schedule simulation depletes stock on {depletion_date.isoformat()}.",
    )


def get_refill_predictions(
    db: Session, user: User, reference_date: date | None = None
) -> list[RefillPredictionItem]:
    """Compute refill predictions across all personal medicines for the current patient."""
    profile = db.get(PatientProfile, user.id)
    tz_name = profile.timezone if profile else "Asia/Kolkata"
    refill_days = profile.refill_alert_days if profile else 5
    today_local = reference_date or datetime.now(UTC).astimezone(ZoneInfo(tz_name)).date()

    meds = db.scalars(
        select(PersonalMedicine)
        .where(PersonalMedicine.user_id == user.id)
        .order_by(PersonalMedicine.display_name.asc())
    ).all()

    results: list[RefillPredictionItem] = []
    for med in meds:
        active_sched = db.scalar(
            select(ScheduleVersion).where(
                ScheduleVersion.personal_med_id == med.id,
                ScheduleVersion.effective_to.is_(None),
            )
        )
        results.append(predict_medicine_refill(med, active_sched, refill_days, today_local))
    return results
