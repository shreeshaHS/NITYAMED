"""REST API routes for patient adherence analytics and reports."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.analytics import service
from app.modules.analytics.schemas import AdherenceReportResponse
from app.modules.auth.dependencies import require_role
from app.modules.auth.models import User

analytics_router = APIRouter(prefix="/analytics", tags=["Adherence Analytics"])


@analytics_router.get("/adherence", response_model=AdherenceReportResponse)
def get_adherence_report(
    days: int = Query(default=30, ge=1, le=365),
    current_user: User = Depends(require_role("patient")),
    db: Session = Depends(get_db),
) -> AdherenceReportResponse:
    """Return documented adherence rates, per-medicine breakdown, and irregular patterns."""
    return service.compute_adherence_report(db, current_user, days=days)
