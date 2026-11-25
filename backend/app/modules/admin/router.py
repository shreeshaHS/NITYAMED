"""REST API routes restricted to system administrators."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.admin import service
from app.modules.admin.schemas import (
    AdminCatalogueCreateRequest,
    AdminCatalogueListItem,
    AdminCatalogueUpdateRequest,
    AdminHealthMetricsResponse,
    AdminTestEmailRequest,
    AdminTestEmailResponse,
)
from app.modules.auth.dependencies import require_role
from app.modules.auth.models import User
from app.modules.medicines.schemas import CatalogueItemResponse
from app.modules.medicines.seed import seed_medicine_catalogue
from app.modules.notifications.schemas import SweepSummaryResponse
from app.modules.notifications.service import run_maintenance_sweep

admin_router = APIRouter(prefix="/admin", tags=["System Administration"])


@admin_router.get("/catalogue", response_model=list[AdminCatalogueListItem])
def admin_list_catalogue(
    q: str = Query(default="", max_length=100),
    include_deprecated: bool = Query(default=True),
    status_filter: str = Query(default="all", pattern="^(all|active|deprecated|unverified)$"),
    limit: int = Query(default=30, ge=1, le=100),
    _: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> list[AdminCatalogueListItem]:
    """List or search catalogue entries (including deprecated items) for administration."""
    return service.list_catalogue_entries(
        db,
        query=q,
        include_deprecated=include_deprecated,
        status_filter=status_filter,
        limit=limit,
    )


@admin_router.post(
    "/catalogue", response_model=CatalogueItemResponse, status_code=status.HTTP_201_CREATED
)
def admin_create_catalogue(
    payload: AdminCatalogueCreateRequest,
    _: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> CatalogueItemResponse:
    """Create a verified catalogue item and its patient education record."""
    return service.create_catalogue_entry(db, payload)


@admin_router.patch("/catalogue/{catalogue_id}", response_model=CatalogueItemResponse)
def admin_update_catalogue(
    catalogue_id: UUID,
    payload: AdminCatalogueUpdateRequest,
    _: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> CatalogueItemResponse:
    """Update or deprecate a verified catalogue item."""
    return service.update_catalogue_entry(db, catalogue_id, payload)


@admin_router.post("/catalogue/seed")
def admin_seed_catalogue(
    _: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> dict[str, int]:
    """Idempotently load curated seed medicines into the catalogue."""
    inserted = seed_medicine_catalogue(db)
    return {"inserted": inserted}


@admin_router.get("/health/metrics", response_model=AdminHealthMetricsResponse)
def admin_metrics(
    _: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> AdminHealthMetricsResponse:
    """Return anonymized system metrics (no patient PII)."""
    return service.get_anonymized_metrics(db)


@admin_router.post("/maintenance/sweep", response_model=SweepSummaryResponse)
def admin_trigger_sweep(
    _: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> SweepSummaryResponse:
    """Allow an authenticated administrator to run overdue dose expiry & refill alert maintenance."""
    return run_maintenance_sweep(db)


@admin_router.post("/system/test-email", response_model=AdminTestEmailResponse)
def admin_test_email(
    payload: AdminTestEmailRequest,
    _: User = Depends(require_role("admin")),
) -> AdminTestEmailResponse:
    """Send a diagnostic SMTP test email from the Admin Console."""
    return service.send_admin_test_email(payload.recipient_email)
