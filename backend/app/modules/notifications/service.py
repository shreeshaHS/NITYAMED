"""Notification deduplication, privacy-safe previews, and maintenance sweep logic."""

from datetime import UTC, datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.modules.auth.email_service import send_reminder_email
from app.modules.auth.models import PatientProfile, User
from app.modules.notifications.models import Notification
from app.modules.notifications.schemas import (
    NotificationResponse,
    NotificationStatusUpdateRequest,
    SweepSummaryResponse,
)
from app.modules.refill.service import get_refill_predictions
from app.modules.schedules.models import DoseEvent
from app.modules.schedules.service import expire_overdue_doses


def format_privacy_preview(
    notif_type: str,
    lockscreen_privacy: bool,
    medicine_name: str | None = None,
) -> str:
    """Build lockscreen-safe notification preview text respecting privacy preference."""
    if lockscreen_privacy:
        if notif_type == "dose_reminder":
            return "NityaMed reminder: Time for your scheduled medicine. Open app to view."
        if notif_type in {"low_stock", "refill_alert"}:
            return "NityaMed alert: Check your medicine stock in the app."
        return "NityaMed notification: Open app to view."

    label = medicine_name or "your medicine"
    if notif_type == "dose_reminder":
        return f"Reminder: Time to take {label}."
    if notif_type in {"low_stock", "refill_alert"}:
        return f"Refill alert: {label} stock is running low."
    return f"NityaMed update for {label}."


def create_dedup_notification(
    db: Session,
    user_id: UUID,
    notif_type: str,
    dedup_key: str,
    scheduled_for: datetime,
    payload_preview: str,
    personal_med_id: UUID | None = None,
) -> Notification | None:
    """Insert a notification only if dedup_key does not already exist."""
    existing = db.scalar(select(Notification).where(Notification.dedup_key == dedup_key))
    if existing is not None:
        return None

    notif = Notification(
        user_id=user_id,
        personal_med_id=personal_med_id,
        notif_type=notif_type,
        dedup_key=dedup_key,
        scheduled_for=scheduled_for,
        delivery_status="scheduled",
        payload_preview=payload_preview[:160],
    )
    db.add(notif)
    db.flush()
    return notif


def generate_refill_alerts_for_user(db: Session, user: User) -> int:
    """Create deduplicated refill/low-stock notification records for active patients."""
    profile = db.get(PatientProfile, user.id)
    tz_name = profile.timezone if profile else "Asia/Kolkata"
    lock_privacy = profile.lockscreen_privacy if profile else True
    now = datetime.now(UTC)
    today_str = now.astimezone(ZoneInfo(tz_name)).date().isoformat()

    created = 0
    predictions = get_refill_predictions(db, user)
    for pred in predictions:
        if not pred.should_alert_now:
            continue
        notif_type = (
            "low_stock" if pred.prediction_mode == "as_needed_threshold_only" else "refill_alert"
        )
        dedup_key = f"{notif_type}:{user.id}:{pred.personal_med_id}:{today_str}"
        preview = format_privacy_preview(notif_type, lock_privacy, pred.display_name)
        created_notif = create_dedup_notification(
            db,
            user_id=user.id,
            notif_type=notif_type,
            dedup_key=dedup_key,
            scheduled_for=now,
            payload_preview=preview,
            personal_med_id=pred.personal_med_id,
        )
        if created_notif is not None:
            created += 1
            if profile and profile.email_reminders_enabled:
                # Always privacy-mask email bodies so sensitive drug names never leak to inboxes.
                email_preview = format_privacy_preview(notif_type, True)
                if send_reminder_email(user.email, "NityaMed — Refill Alert", email_preview):
                    created_notif.delivery_status = "delivered"
                    created_notif.sent_at = now

    if created > 0:
        db.commit()
    return created


def generate_email_dose_backups_for_user(db: Session, user: User) -> int:
    """Send privacy-masked backup reminder emails for doses due in the next 60 minutes."""
    profile = db.get(PatientProfile, user.id)
    if profile is None or not profile.email_reminders_enabled:
        return 0

    now = datetime.now(UTC)
    horizon = now + timedelta(minutes=60)
    due_doses = db.scalars(
        select(DoseEvent).where(
            DoseEvent.user_id == user.id,
            DoseEvent.status.in_(("pending", "snoozed")),
            DoseEvent.scheduled_at >= now - timedelta(minutes=15),
            DoseEvent.scheduled_at <= horizon,
        )
    ).all()

    created = 0
    for dose in due_doses:
        dedup_key = f"email_dose_backup:{dose.id}"
        preview = format_privacy_preview("dose_reminder", True)
        notif = create_dedup_notification(
            db,
            user_id=user.id,
            notif_type="dose_reminder",
            dedup_key=dedup_key,
            scheduled_for=dose.scheduled_at,
            payload_preview=preview,
            personal_med_id=dose.personal_med_id,
        )
        if notif is not None:
            created += 1
            if send_reminder_email(user.email, "NityaMed — Medication Reminder", preview):
                notif.delivery_status = "delivered"
                notif.sent_at = now

    if created > 0:
        db.commit()
    return created


def list_notification_history(
    db: Session, user: User, limit: int = 50
) -> list[NotificationResponse]:
    """Return recent notifications for the authenticated patient."""
    rows = db.scalars(
        select(Notification)
        .where(Notification.user_id == user.id)
        .order_by(Notification.scheduled_for.desc())
        .limit(limit)
    ).all()
    return [NotificationResponse.model_validate(row) for row in rows]


def update_notification_status(
    db: Session,
    user: User,
    notif_id: UUID,
    payload: NotificationStatusUpdateRequest,
) -> NotificationResponse:
    """Mark an owned notification as delivered, dismissed, or failed."""
    notif = db.get(Notification, notif_id)
    if notif is None or notif.user_id != user.id:
        raise AppError(404, "NOTIFICATION_NOT_FOUND", "Notification record was not found")

    notif.delivery_status = payload.delivery_status
    if payload.delivery_status == "delivered" and notif.sent_at is None:
        notif.sent_at = datetime.now(UTC)

    db.commit()
    db.refresh(notif)
    return NotificationResponse.model_validate(notif)


def run_maintenance_sweep(db: Session) -> SweepSummaryResponse:
    """Idempotently expire overdue doses and generate daily refill alerts across active patients."""
    expired_count = expire_overdue_doses(db)
    patients = db.scalars(
        select(User).where(User.role == "patient", User.is_active.is_(True), User.deleted_at.is_(None))
    ).all()

    alerts_created = 0
    for patient in patients:
        alerts_created += generate_refill_alerts_for_user(db, patient)
        alerts_created += generate_email_dose_backups_for_user(db, patient)

    return SweepSummaryResponse(
        expired_doses_marked=expired_count,
        refill_alerts_created=alerts_created,
    )
