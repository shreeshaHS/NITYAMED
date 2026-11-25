"""REST API routes for notification history, status updates, and Render cron sweeps."""

import secrets
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.exceptions import AppError
from app.modules.auth.dependencies import require_role
from app.modules.auth.models import User
from app.modules.notifications import service
from app.modules.notifications.schemas import (
    NotificationResponse,
    NotificationStatusUpdateRequest,
    SweepSummaryResponse,
)

notifications_router = APIRouter(prefix="/notifications", tags=["Notifications"])
internal_router = APIRouter(prefix="/internal", tags=["Internal Maintenance"])


@notifications_router.get("/history", response_model=list[NotificationResponse])
def get_notification_history(
    limit: int = Query(default=50, ge=1, le=200),
    current_user: User = Depends(require_role("patient")),
    db: Session = Depends(get_db),
) -> list[NotificationResponse]:
    """List reminder and refill notification history for the current patient."""
    return service.list_notification_history(db, current_user, limit=limit)


@notifications_router.post("/refills/check", response_model=list[NotificationResponse])
def check_and_record_refill_alerts(
    current_user: User = Depends(require_role("patient")),
    db: Session = Depends(get_db),
) -> list[NotificationResponse]:
    """Evaluate refill thresholds and return updated notification history."""
    service.generate_refill_alerts_for_user(db, current_user)
    return service.list_notification_history(db, current_user, limit=50)


@notifications_router.patch("/{notif_id}/status", response_model=NotificationResponse)
def update_notification_status(
    notif_id: UUID,
    payload: NotificationStatusUpdateRequest,
    current_user: User = Depends(require_role("patient")),
    db: Session = Depends(get_db),
) -> NotificationResponse:
    """Update notification delivery/dismissed state from the client."""
    return service.update_notification_status(db, current_user, notif_id, payload)


@internal_router.post("/jobs/sweep", response_model=SweepSummaryResponse)
def trigger_maintenance_sweep(
    x_cron_secret: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> SweepSummaryResponse:
    """Protected endpoint for Render/external cron to run overdue expiry and refill alerts."""
    expected = get_settings().cron_secret
    if not x_cron_secret or not secrets.compare_digest(x_cron_secret, expected):
        raise AppError(403, "INVALID_CRON_SECRET", "Invalid maintenance cron secret")
    return service.run_maintenance_sweep(db)
