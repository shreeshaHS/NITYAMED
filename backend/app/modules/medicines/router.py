"""REST API routes for medicine catalogue search, verified education, and personal medicines."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.auth.dependencies import require_role
from app.modules.auth.models import User
from app.modules.medicines import service
from app.modules.medicines.schemas import (
    CatalogueItemResponse,
    CatalogueVerificationRequest,
    DosageForm,
    MedicineEducationResponse,
    MedicineStatus,
    PersonalMedicineCreateRequest,
    PersonalMedicineDetailResponse,
    PersonalMedicineResponse,
    PersonalMedicineUpdateRequest,
)

catalogue_router = APIRouter(prefix="/catalogue", tags=["Medicine Catalogue"])
medicines_router = APIRouter(prefix="/medicines", tags=["Personal Medicines"])


@catalogue_router.get("/search", response_model=list[CatalogueItemResponse])
def search_catalogue(
    q: str = Query(default="", max_length=100),
    form: DosageForm | None = None,
    manufacturer: str | None = Query(default=None, max_length=100),
    limit: int = Query(default=20, ge=1, le=50),
    include_external: bool = Query(default=True),
    _: User = Depends(require_role("patient", "admin")),
    db: Session = Depends(get_db),
) -> list[CatalogueItemResponse]:
    """Search verified catalogue medicines by brand, composition, or manufacturer company."""
    return service.search_catalogue(
        db,
        query=q,
        dosage_form=form,
        manufacturer=manufacturer,
        limit=limit,
        include_external=include_external,
    )


@catalogue_router.post(
    "/requests", response_model=CatalogueItemResponse, status_code=status.HTTP_201_CREATED
)
def request_catalogue_verification(
    payload: CatalogueVerificationRequest,
    _: User = Depends(require_role("patient", "admin")),
    db: Session = Depends(get_db),
) -> CatalogueItemResponse:
    """Submit a missing medicine as unverified for administrator regulatory review."""
    return service.submit_catalogue_verification_request(db, payload)


@catalogue_router.get("/{catalogue_id}/education", response_model=MedicineEducationResponse)
def get_education(
    catalogue_id: UUID,
    _: User = Depends(require_role("patient", "admin")),
    db: Session = Depends(get_db),
) -> MedicineEducationResponse:
    """Return verified patient education with source and verification date."""
    return service.get_catalogue_education(db, catalogue_id)


@medicines_router.get("", response_model=list[PersonalMedicineResponse])
def list_medicines(
    status_filter: MedicineStatus | None = Query(default=None, alias="status"),
    current_user: User = Depends(require_role("patient")),
    db: Session = Depends(get_db),
) -> list[PersonalMedicineResponse]:
    """List personal medicines owned by the authenticated patient."""
    return service.list_personal_medicines(db, current_user, status_filter)


@medicines_router.post(
    "", response_model=PersonalMedicineResponse, status_code=status.HTTP_201_CREATED
)
def create_medicine(
    payload: PersonalMedicineCreateRequest,
    current_user: User = Depends(require_role("patient")),
    db: Session = Depends(get_db),
) -> PersonalMedicineResponse:
    """Add a catalogue-linked or custom personal medicine."""
    return service.create_personal_medicine(db, current_user, payload)


@medicines_router.get("/{med_id}", response_model=PersonalMedicineDetailResponse)
def get_medicine_detail(
    med_id: UUID,
    current_user: User = Depends(require_role("patient")),
    db: Session = Depends(get_db),
) -> PersonalMedicineDetailResponse:
    """Return medicine details and verified education (or unverified custom notice)."""
    return service.get_personal_medicine_detail(db, current_user, med_id)


@medicines_router.patch("/{med_id}", response_model=PersonalMedicineResponse)
def update_medicine(
    med_id: UUID,
    payload: PersonalMedicineUpdateRequest,
    current_user: User = Depends(require_role("patient")),
    db: Session = Depends(get_db),
) -> PersonalMedicineResponse:
    """Update medicine instructions, thresholds, or active/paused/completed status."""
    return service.update_personal_medicine(db, current_user, med_id, payload)
