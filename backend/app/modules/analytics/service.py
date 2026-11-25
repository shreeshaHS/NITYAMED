"""Service layer computing transparent adherence reports and non-diagnostic patterns."""

from collections import defaultdict
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.analytics.schemas import AdherenceReportResponse, MedicineAdherenceBreakdown
from app.modules.auth.models import PatientProfile, User
from app.modules.medicines.models import PersonalMedicine
from app.modules.schedules.models import DoseEvent
from app.modules.schedules.service import expire_overdue_doses

FORMULA_NOTES = {
    "confirmed_adherence_rate": (
        "(taken_on_time + taken_late + partially_taken) / closed_scheduled_count * 100"
    ),
    "on_time_rate": "taken_on_time / closed_scheduled_count * 100",
    "unconfirmed_rate": "expired_unconfirmed / closed_scheduled_count * 100",
    "policy": (
        "Unanswered past-cutoff doses remain 'expired_unconfirmed' and are never treated as "
        "confirmed missed or skipped doses. Future pending doses are excluded from closed counts."
    ),
}


def _pct(numerator: int, denominator: int) -> float | None:
    """Compute percentage rounded to 2 decimals, or None if denominator is zero."""
    if denominator <= 0:
        return None
    return round((numerator / denominator) * 100.0, 2)


def _time_bucket(local_hour: int) -> str:
    """Group local hour into patient-friendly daypart."""
    if 5 <= local_hour < 12:
        return "morning"
    if 12 <= local_hour < 17:
        return "afternoon"
    if 17 <= local_hour < 22:
        return "evening"
    return "night"


def compute_adherence_report(
    db: Session, user: User, days: int = 30
) -> AdherenceReportResponse:
    """Compute adherence counts, per-medicine breakdown, and non-diagnostic patterns."""
    now = datetime.now(UTC)
    expire_overdue_doses(db, user_id=user.id, now=now)

    profile = db.get(PatientProfile, user.id)
    tz = ZoneInfo(profile.timezone if profile else "Asia/Kolkata")
    window_start = now - timedelta(days=days)

    rows = db.execute(
        select(DoseEvent, PersonalMedicine)
        .join(PersonalMedicine, DoseEvent.personal_med_id == PersonalMedicine.id)
        .where(
            DoseEvent.user_id == user.id,
            DoseEvent.scheduled_at >= window_start,
        )
        .order_by(DoseEvent.scheduled_at.asc())
    ).all()

    counts = {
        "taken_on_time": 0,
        "taken_late": 0,
        "partially_taken": 0,
        "explicitly_skipped": 0,
        "expired_unconfirmed": 0,
    }
    upcoming_pending = 0
    late_by_bucket: dict[str, int] = defaultdict(int)
    med_buckets: dict = {}

    for dose, med in rows:
        if dose.status in {"pending", "snoozed"}:
            upcoming_pending += 1
            continue

        if med.id not in med_buckets:
            med_buckets[med.id] = {
                "display_name": med.display_name,
                "taken_on_time": 0,
                "taken_late": 0,
                "partially_taken": 0,
                "explicitly_skipped": 0,
                "expired_unconfirmed": 0,
            }

        if dose.status in counts:
            counts[dose.status] += 1
            med_buckets[med.id][dose.status] += 1

        if dose.status == "taken_late":
            sched_utc = (
                dose.scheduled_at
                if dose.scheduled_at.tzinfo is not None
                else dose.scheduled_at.replace(tzinfo=UTC)
            )
            bucket = _time_bucket(sched_utc.astimezone(tz).hour)
            late_by_bucket[bucket] += 1

    closed_total = sum(counts.values())
    taken_total = counts["taken_on_time"] + counts["taken_late"] + counts["partially_taken"]

    per_medicine: list[MedicineAdherenceBreakdown] = []
    patterns: list[str] = []

    for med_id, stats in sorted(med_buckets.items(), key=lambda kv: kv[1]["display_name"]):
        med_closed = (
            stats["taken_on_time"]
            + stats["taken_late"]
            + stats["partially_taken"]
            + stats["explicitly_skipped"]
            + stats["expired_unconfirmed"]
        )
        med_taken = stats["taken_on_time"] + stats["taken_late"] + stats["partially_taken"]
        per_medicine.append(
            MedicineAdherenceBreakdown(
                personal_med_id=med_id,
                display_name=stats["display_name"],
                closed_scheduled_count=med_closed,
                taken_on_time=stats["taken_on_time"],
                taken_late=stats["taken_late"],
                partially_taken=stats["partially_taken"],
                explicitly_skipped=stats["explicitly_skipped"],
                expired_unconfirmed=stats["expired_unconfirmed"],
                confirmed_adherence_rate=_pct(med_taken, med_closed),
                unconfirmed_rate=_pct(stats["expired_unconfirmed"], med_closed),
            )
        )
        if stats["expired_unconfirmed"] >= 3:
            patterns.append(
                f"{stats['display_name']} had {stats['expired_unconfirmed']} unconfirmed doses in the last {days} days."
            )
        if stats["explicitly_skipped"] >= 3:
            patterns.append(
                f"{stats['display_name']} was explicitly skipped {stats['explicitly_skipped']} times in the last {days} days."
            )

    for bucket, late_count in sorted(late_by_bucket.items()):
        if late_count >= 3:
            patterns.append(
                f"Frequent late confirmations during the {bucket} window ({late_count} doses taken late)."
            )

    return AdherenceReportResponse(
        window_days=days,
        closed_scheduled_count=closed_total,
        upcoming_pending_count=upcoming_pending,
        taken_on_time=counts["taken_on_time"],
        taken_late=counts["taken_late"],
        partially_taken=counts["partially_taken"],
        explicitly_skipped=counts["explicitly_skipped"],
        expired_unconfirmed=counts["expired_unconfirmed"],
        confirmed_adherence_rate=_pct(taken_total, closed_total),
        on_time_rate=_pct(counts["taken_on_time"], closed_total),
        unconfirmed_rate=_pct(counts["expired_unconfirmed"], closed_total),
        formula_notes=FORMULA_NOTES,
        per_medicine=per_medicine,
        irregular_patterns=patterns,
    )
