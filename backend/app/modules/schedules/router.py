"""REST API routes for medication schedule versions and adherence dose actions."""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.auth.dependencies import require_role
from app.modules.auth.models import User
from app.modules.schedules import service
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

schedules_router = APIRouter(prefix="/medicines", tags=["Medication Schedules"])
doses_router = APIRouter(prefix="/doses", tags=["Medication Adherence"])


@schedules_router.post(
    "/{med_id}/schedules",
    response_model=ScheduleVersionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_schedule(
    med_id: UUID,
    payload: ScheduleCreateRequest,
    current_user: User = Depends(require_role("patient")),
    db: Session = Depends(get_db),
) -> ScheduleVersionResponse:
    """Create a new immutable schedule version and materialize upcoming dose events."""
    return service.create_schedule_version(db, current_user, med_id, payload)


@schedules_router.get("/{med_id}/schedules", response_model=list[ScheduleVersionResponse])
def list_schedules(
    med_id: UUID,
    current_user: User = Depends(require_role("patient")),
    db: Session = Depends(get_db),
) -> list[ScheduleVersionResponse]:
    """List active and historical schedule versions for a medicine."""
    return service.list_schedule_versions(db, current_user, med_id)


@doses_router.get("/daily", response_model=list[DailyDoseItemResponse])
def get_daily_doses(
    target_date: date | None = Query(default=None, alias="date"),
    current_user: User = Depends(require_role("patient")),
    db: Session = Depends(get_db),
) -> list[DailyDoseItemResponse]:
    """Return chronological dose schedule for a date after running lazy expiry check."""
    return service.get_daily_schedule(db, current_user, target_date=target_date)


@doses_router.post("/{dose_id}/confirm", response_model=DoseActionResponse)
def confirm_dose(
    dose_id: UUID,
    payload: DoseConfirmRequest,
    current_user: User = Depends(require_role("patient")),
    db: Session = Depends(get_db),
) -> DoseActionResponse:
    """Confirm a dose as taken on time, taken late, or partially taken."""
    return service.confirm_dose(db, current_user, dose_id, payload)


@doses_router.post("/{dose_id}/skip", response_model=DoseActionResponse)
def skip_dose(
    dose_id: UUID,
    payload: DoseSkipRequest,
    current_user: User = Depends(require_role("patient")),
    db: Session = Depends(get_db),
) -> DoseActionResponse:
    """Explicitly skip a scheduled dose without deducting inventory."""
    return service.skip_dose(db, current_user, dose_id, payload)


@doses_router.post("/{dose_id}/snooze", response_model=DoseActionResponse)
def snooze_dose(
    dose_id: UUID,
    payload: DoseSnoozeRequest,
    current_user: User = Depends(require_role("patient")),
    db: Session = Depends(get_db),
) -> DoseActionResponse:
    """Snooze a pending or snoozed dose reminder."""
    return service.snooze_dose(db, current_user, dose_id, payload)


@doses_router.post("/{dose_id}/correct", response_model=DoseActionResponse)
def correct_dose(
    dose_id: UUID,
    payload: DoseCorrectRequest,
    current_user: User = Depends(require_role("patient")),
    db: Session = Depends(get_db),
) -> DoseActionResponse:
    """Correct an accidental dose confirmation or skip with full audit trail."""
    return service.correct_dose(db, current_user, dose_id, payload)
