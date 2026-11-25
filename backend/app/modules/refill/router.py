"""REST API routes for refill predictions and alerts."""

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.auth.dependencies import require_role
from app.modules.auth.models import User
from app.modules.refill import service
from app.modules.refill.schemas import RefillPredictionItem

refill_router = APIRouter(prefix="/refills", tags=["Refill Predictions"])


@refill_router.get("/predictions", response_model=list[RefillPredictionItem])
def get_refill_predictions(
    as_of: date | None = Query(default=None),
    current_user: User = Depends(require_role("patient")),
    db: Session = Depends(get_db),
) -> list[RefillPredictionItem]:
    """Return deterministic depletion dates and refill alert recommendations."""
    return service.get_refill_predictions(db, current_user, reference_date=as_of)
