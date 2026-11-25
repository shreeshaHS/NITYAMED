"""System administrator services for catalogue curation and anonymized metrics."""

from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.modules.admin.schemas import (
    AdminCatalogueCreateRequest,
    AdminCatalogueListItem,
    AdminCatalogueUpdateRequest,
    AdminHealthMetricsResponse,
    AdminTestEmailResponse,
)
from app.modules.assistant.nlp import MODEL_PATH
from app.modules.auth.email_service import send_email_detailed
from app.modules.auth.models import PatientProfile, User
from app.modules.medicines.models import MedicineCatalogue, MedicineEducation, PersonalMedicine
from app.modules.medicines.schemas import CatalogueItemResponse
from app.modules.notifications.models import Notification
from app.modules.schedules.models import DoseEvent


def create_catalogue_entry(
    db: Session, payload: AdminCatalogueCreateRequest
) -> CatalogueItemResponse:
    """Create a verified medicine catalogue record and its education entry."""
    item = MedicineCatalogue(
        brand_name=payload.brand_name.strip(),
        generic_name=payload.generic_name.strip(),
        active_ingredients=payload.active_ingredients,
        strength=payload.strength.strip(),
        dosage_form=payload.dosage_form,
        standard_pack_size=payload.standard_pack_size,
        pack_unit=payload.pack_unit,
        manufacturer=payload.manufacturer,
        is_verified=True,
    )
    db.add(item)
    db.flush()

    edu = payload.education
    db.add(
        MedicineEducation(
            catalogue_id=item.id,
            category=edu.category.strip(),
            common_uses=edu.common_uses.strip(),
            mechanism=edu.mechanism.strip(),
            side_effects=edu.side_effects.strip(),
            precautions=edu.precautions.strip(),
            additional_notes=edu.additional_notes,
            source_name=edu.source_name.strip(),
            source_url=edu.source_url,
            verified_at=edu.verified_at,
        )
    )
    db.commit()
    db.refresh(item)
    return CatalogueItemResponse.model_validate(item)


def update_catalogue_entry(
    db: Session, catalogue_id: UUID, payload: AdminCatalogueUpdateRequest
) -> CatalogueItemResponse:
    """Update or deprecate an existing medicine catalogue entry."""
    item = db.get(MedicineCatalogue, catalogue_id)
    if item is None:
        raise AppError(404, "CATALOGUE_ITEM_NOT_FOUND", "Catalogue item not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)

    db.commit()
    db.refresh(item)
    return CatalogueItemResponse.model_validate(item)


def list_catalogue_entries(
    db: Session,
    query: str = "",
    include_deprecated: bool = True,
    status_filter: str = "all",
    limit: int = 30,
) -> list[AdminCatalogueListItem]:
    """List or search shared catalogue entries for system administration."""
    stmt = select(MedicineCatalogue)
    if status_filter == "active":
        stmt = stmt.where(MedicineCatalogue.is_deprecated.is_(False))
    elif status_filter == "deprecated":
        stmt = stmt.where(MedicineCatalogue.is_deprecated.is_(True))
    elif status_filter == "unverified":
        stmt = stmt.where(MedicineCatalogue.is_verified.is_(False))
    elif not include_deprecated:
        stmt = stmt.where(MedicineCatalogue.is_deprecated.is_(False))
    cleaned = query.strip()
    if cleaned:
        pat = f"%{cleaned}%"
        stmt = stmt.where(
            or_(
                MedicineCatalogue.brand_name.ilike(pat),
                MedicineCatalogue.generic_name.ilike(pat),
            )
        )
    rows = db.scalars(stmt.order_by(MedicineCatalogue.brand_name.asc()).limit(limit)).all()
    return [
        AdminCatalogueListItem(
            id=str(r.id),
            brand_name=r.brand_name,
            generic_name=r.generic_name,
            strength=r.strength,
            dosage_form=r.dosage_form,  # type: ignore[arg-type]
            standard_pack_size=r.standard_pack_size,
            manufacturer=r.manufacturer,
            is_verified=r.is_verified,
            is_deprecated=r.is_deprecated,
        )
        for r in rows
    ]


def get_anonymized_metrics(db: Session) -> AdminHealthMetricsResponse:
    """Return aggregate system counts without exposing any patient PII."""
    settings = get_settings()
    total_users = db.scalar(select(func.count(User.id))) or 0
    verified_users = (
        db.scalar(select(func.count(User.id)).where(User.is_email_verified.is_(True))) or 0
    )
    email_opt_ins = (
        db.scalar(
            select(func.count(PatientProfile.user_id)).where(
                PatientProfile.email_reminders_enabled.is_(True)
            )
        )
        or 0
    )
    active_meds = (
        db.scalar(select(func.count(PersonalMedicine.id)).where(PersonalMedicine.status == "active"))
        or 0
    )
    total_doses = db.scalar(select(func.count(DoseEvent.id))) or 0
    confirmed_doses = (
        db.scalar(
            select(func.count(DoseEvent.id)).where(
                DoseEvent.status.in_(("taken_on_time", "taken_late", "partially_taken"))
            )
        )
        or 0
    )
    expired_doses = (
        db.scalar(
            select(func.count(DoseEvent.id)).where(DoseEvent.status == "expired_unconfirmed")
        )
        or 0
    )
    total_catalogue = db.scalar(select(func.count(MedicineCatalogue.id))) or 0
    verified_catalogue = (
        db.scalar(
            select(func.count(MedicineCatalogue.id)).where(
                MedicineCatalogue.is_verified.is_(True),
                MedicineCatalogue.is_deprecated.is_(False),
            )
        )
        or 0
    )
    deprecated_catalogue = (
        db.scalar(
            select(func.count(MedicineCatalogue.id)).where(
                MedicineCatalogue.is_deprecated.is_(True)
            )
        )
        or 0
    )
    total_notifications = db.scalar(select(func.count(Notification.id))) or 0
    smtp_configured = bool(
        settings.brevo_api_key
        or settings.resend_api_key
        or (settings.smtp_host and settings.smtp_user and settings.smtp_password)
    )
    ml_ready = MODEL_PATH.exists()

    return AdminHealthMetricsResponse(
        total_users=total_users,
        verified_users=verified_users,
        email_backup_opt_in_users=email_opt_ins,
        active_personal_medicines=active_meds,
        total_dose_events=total_doses,
        confirmed_dose_events=confirmed_doses,
        expired_unconfirmed_events=expired_doses,
        total_catalogue_items=total_catalogue,
        verified_catalogue_items=verified_catalogue,
        deprecated_catalogue_items=deprecated_catalogue,
        total_notifications=total_notifications,
        smtp_configured=smtp_configured,
        require_email_verification=settings.require_email_verification,
        ml_model_ready=ml_ready,
        ml_model_name="hybrid_tfidf_logreg" if ml_ready else None,
    )


def send_admin_test_email(recipient_email: str) -> AdminTestEmailResponse:
    """Trigger a non-sensitive diagnostic email via configured email provider."""
    sent, detail = send_email_detailed(
        recipient_email,
        "NityaMed Admin — Email Delivery Test",
        "This is a system health verification email from the NityaMed Admin Console.",
    )
    return AdminTestEmailResponse(sent=sent, detail=detail)
