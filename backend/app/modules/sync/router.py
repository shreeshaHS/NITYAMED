"""REST API routes for offline mobile synchronization."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.auth.dependencies import require_role
from app.modules.auth.models import User
from app.modules.sync import service
from app.modules.sync.schemas import SyncBatchRequest, SyncBatchResponse, SyncBootstrapResponse

sync_router = APIRouter(prefix="/sync", tags=["Offline Sync"])


@sync_router.post("/events", response_model=SyncBatchResponse)
def sync_offline_events(
    payload: SyncBatchRequest,
    current_user: User = Depends(require_role("patient")),
    db: Session = Depends(get_db),
) -> SyncBatchResponse:
    """Replay queued offline dose and stock events idempotently."""
    return service.process_sync_batch(db, current_user, payload)


@sync_router.get("/bootstrap", response_model=SyncBootstrapResponse)
def bootstrap_offline_cache(
    current_user: User = Depends(require_role("patient")),
    db: Session = Depends(get_db),
) -> SyncBootstrapResponse:
    """Download active medicines, schedules, and 44-day dose window for mobile SQLite."""
    return service.get_bootstrap_snapshot(db, current_user)
