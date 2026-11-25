"""Service layer for medicine catalogue search, education lookup, and personal medicines."""

from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.modules.auth.models import User
from app.modules.inventory.models import StockTransaction
from app.modules.medicines.external_api import ExternalMedicineRecord, fetch_external_medicines
from app.modules.medicines.models import MedicineCatalogue, MedicineEducation, PersonalMedicine
from app.modules.medicines.schemas import (
    CUSTOM_EDUCATION_NOTICE,
    CatalogueItemResponse,
    MedicineEducationResponse,
    PersonalMedicineCreateRequest,
    PersonalMedicineDetailResponse,
    PersonalMedicineResponse,
    PersonalMedicineUpdateRequest,
)


def _cache_external_records(db: Session, records: list[ExternalMedicineRecord]) -> list[MedicineCatalogue]:
    """Persist newly fetched openFDA records into the local catalogue idempotently."""
    cached: list[MedicineCatalogue] = []
    for rec in records:
        existing = db.scalar(
            select(MedicineCatalogue).where(
                func.lower(MedicineCatalogue.brand_name) == rec.brand_name.lower(),
                func.lower(MedicineCatalogue.strength) == rec.strength.lower(),
                MedicineCatalogue.dosage_form == rec.dosage_form,
            )
        )
        if existing is not None:
            cached.append(existing)
            continue

        row = MedicineCatalogue(
            brand_name=rec.brand_name,
            generic_name=rec.generic_name,
            active_ingredients=rec.active_ingredients,
            strength=rec.strength,
            dosage_form=rec.dosage_form,
            standard_pack_size=None,
            pack_unit=None,
            manufacturer=rec.manufacturer,
            is_verified=True,
        )
        db.add(row)
        db.flush()

        db.add(
            MedicineEducation(
                catalogue_id=row.id,
                category=rec.category,
                common_uses=rec.common_uses,
                mechanism=rec.mechanism,
                side_effects=rec.side_effects,
                precautions=rec.precautions,
                source_name=rec.source_name,
                source_url=rec.source_url,
                verified_at=rec.verified_at,
            )
        )
        cached.append(row)

    if cached:
        db.commit()
        for item in cached:
            db.refresh(item)
    return cached


def search_catalogue(
    db: Session,
    query: str = "",
    dosage_form: str | None = None,
    limit: int = 20,
    include_external: bool = True,
) -> list[CatalogueItemResponse]:
    """Search local catalogue first and enrich from live openFDA/RxNorm APIs if needed."""
    stmt = select(MedicineCatalogue).where(MedicineCatalogue.is_deprecated.is_(False))
    cleaned_q = query.strip()
    if cleaned_q:
        pattern = f"%{cleaned_q}%"
        stmt = stmt.where(
            or_(
                MedicineCatalogue.brand_name.ilike(pattern),
                MedicineCatalogue.generic_name.ilike(pattern),
                MedicineCatalogue.active_ingredients.ilike(pattern),
            )
        )
    if dosage_form:
        stmt = stmt.where(MedicineCatalogue.dosage_form == dosage_form)

    local_rows = list(db.scalars(stmt.order_by(MedicineCatalogue.brand_name.asc()).limit(limit)).all())

    if include_external and len(cleaned_q) >= 2 and len(local_rows) < min(limit, 5):
        ext_records = fetch_external_medicines(cleaned_q, limit=min(limit, 5))
        if ext_records:
            cached_rows = _cache_external_records(db, ext_records)
            seen_ids = {row.id for row in local_rows}
            for row in cached_rows:
                if row.id in seen_ids or row.is_deprecated:
                    continue
                if dosage_form and row.dosage_form != dosage_form:
                    continue
                local_rows.append(row)
                seen_ids.add(row.id)
                if len(local_rows) >= limit:
                    break

    return [CatalogueItemResponse.model_validate(row) for row in local_rows]


def _ensure_catalogue_education(
    db: Session, catalogue_item: MedicineCatalogue
) -> MedicineEducation | None:
    """Return existing education or enrich it live from openFDA by generic salt name."""
    edu = db.scalar(
        select(MedicineEducation).where(MedicineEducation.catalogue_id == catalogue_item.id)
    )
    if edu is not None:
        return edu

    # Try each salt in combination products (e.g. Sodium Valproate + Valproic Acid)
    salt_candidates = [s.strip() for s in catalogue_item.generic_name.split("+") if len(s.strip()) >= 2]
    records: list[ExternalMedicineRecord] = []
    for salt in salt_candidates:
        records = fetch_external_medicines(salt, limit=1)
        if records:
            break
    if not records:
        return None

    rec = records[0]
    edu = MedicineEducation(
        catalogue_id=catalogue_item.id,
        category=rec.category,
        common_uses=rec.common_uses,
        mechanism=rec.mechanism,
        side_effects=rec.side_effects,
        precautions=rec.precautions,
        source_name=rec.source_name,
        source_url=rec.source_url,
        verified_at=rec.verified_at,
    )
    db.add(edu)
    db.commit()
    db.refresh(edu)
    return edu


def get_catalogue_education(db: Session, catalogue_id: UUID) -> MedicineEducationResponse:
    """Fetch verified patient education for a catalogue item, enriching via generic salt if needed."""
    catalogue_item = db.get(MedicineCatalogue, catalogue_id)
    if catalogue_item is None or catalogue_item.is_deprecated:
        raise AppError(404, "CATALOGUE_ITEM_NOT_FOUND", "Catalogue item not found")

    edu = _ensure_catalogue_education(db, catalogue_item)
    if edu is None:
        raise AppError(404, "EDUCATION_NOT_FOUND", "Verified medicine education entry not found")
    return MedicineEducationResponse.model_validate(edu)


def create_personal_medicine(
    db: Session, user: User, payload: PersonalMedicineCreateRequest
) -> PersonalMedicineResponse:
    """Create a patient-owned medicine entry and optional INITIAL stock transaction."""
    catalogue_item: MedicineCatalogue | None = None
    if payload.catalogue_id is not None:
        catalogue_item = db.get(MedicineCatalogue, payload.catalogue_id)
        if catalogue_item is None or catalogue_item.is_deprecated:
            raise AppError(404, "CATALOGUE_ITEM_NOT_FOUND", "Selected catalogue medicine was not found")

    display_name = (
        payload.display_name.strip()
        if payload.display_name
        else catalogue_item.brand_name  # type: ignore[union-attr]
    )
    generic_name = (
        payload.generic_name.strip()
        if payload.generic_name
        else (catalogue_item.generic_name if catalogue_item else None)
    )
    strength = (
        payload.strength.strip()
        if payload.strength
        else catalogue_item.strength  # type: ignore[union-attr]
    )
    dosage_form = (
        payload.dosage_form
        if payload.dosage_form
        else catalogue_item.dosage_form  # type: ignore[union-attr]
    )
    units_per_pack = payload.units_per_pack or (
        catalogue_item.standard_pack_size if catalogue_item else None
    )

    if payload.initial_packs > 0 and units_per_pack is None:
        raise AppError(
            422,
            "PACK_SIZE_REQUIRED",
            "units_per_pack is required when initial_packs is greater than 0",
        )

    pack_units = (
        Decimal(payload.initial_packs) * units_per_pack
        if payload.initial_packs > 0 and units_per_pack is not None
        else Decimal("0")
    )
    initial_stock = (pack_units + payload.initial_loose_units).quantize(Decimal("0.01"))

    if payload.client_event_id is not None:
        existing_tx = db.scalar(
            select(StockTransaction).where(
                StockTransaction.client_event_id == payload.client_event_id,
                StockTransaction.user_id == user.id,
            )
        )
        if existing_tx is not None:
            existing_med = db.get(PersonalMedicine, existing_tx.personal_med_id)
            if existing_med is not None:
                return PersonalMedicineResponse.model_validate(existing_med)

    personal_med = PersonalMedicine(
        user_id=user.id,
        catalogue_id=catalogue_item.id if catalogue_item else None,
        is_custom=payload.is_custom,
        display_name=display_name,
        generic_name=generic_name,
        strength=strength,
        dosage_form=dosage_form,
        dose_per_intake=payload.dose_per_intake,
        dose_unit=payload.dose_unit.strip(),
        stock_unit=payload.stock_unit.strip(),
        units_per_pack=units_per_pack,
        confirmed_stock=initial_stock,
        low_stock_threshold=payload.low_stock_threshold,
        instructions=payload.instructions.strip() if payload.instructions else None,
    )
    db.add(personal_med)
    db.flush()

    if initial_stock > 0:
        db.add(
            StockTransaction(
                user_id=user.id,
                personal_med_id=personal_med.id,
                tx_type="INITIAL",
                qty_delta=initial_stock,
                balance_after=initial_stock,
                notes=f"Initial entry ({payload.initial_packs} packs + {payload.initial_loose_units} loose)",
                client_event_id=payload.client_event_id,
            )
        )

    db.commit()
    db.refresh(personal_med)
    return PersonalMedicineResponse.model_validate(personal_med)


def get_owned_medicine(db: Session, user: User, med_id: UUID) -> PersonalMedicine:
    """Fetch a personal medicine and verify ownership by the authenticated user."""
    med = db.get(PersonalMedicine, med_id)
    if med is None or med.user_id != user.id:
        raise AppError(404, "MEDICINE_NOT_FOUND", "Medicine record was not found")
    return med


def list_personal_medicines(
    db: Session, user: User, status_filter: str | None = None
) -> list[PersonalMedicineResponse]:
    """List personal medicines owned by the authenticated patient."""
    stmt = select(PersonalMedicine).where(PersonalMedicine.user_id == user.id)
    if status_filter:
        stmt = stmt.where(PersonalMedicine.status == status_filter)
    rows = db.scalars(stmt.order_by(PersonalMedicine.display_name.asc())).all()
    return [PersonalMedicineResponse.model_validate(row) for row in rows]


def get_personal_medicine_detail(
    db: Session, user: User, med_id: UUID
) -> PersonalMedicineDetailResponse:
    """Return personal medicine details along with verified education or custom fallback notice."""
    med = get_owned_medicine(db, user, med_id)
    med_resp = PersonalMedicineResponse.model_validate(med)

    if med.is_custom or med.catalogue_id is None:
        return PersonalMedicineDetailResponse(
            medicine=med_resp,
            education=None,
            education_notice=CUSTOM_EDUCATION_NOTICE,
        )

    catalogue_item = db.get(MedicineCatalogue, med.catalogue_id)
    edu = _ensure_catalogue_education(db, catalogue_item) if catalogue_item else None
    if edu is None:
        return PersonalMedicineDetailResponse(
            medicine=med_resp,
            education=None,
            education_notice="Verified educational summary is currently unavailable for this item.",
        )

    return PersonalMedicineDetailResponse(
        medicine=med_resp,
        education=MedicineEducationResponse.model_validate(edu),
        education_notice=None,
    )


def update_personal_medicine(
    db: Session, user: User, med_id: UUID, payload: PersonalMedicineUpdateRequest
) -> PersonalMedicineResponse:
    """Update allowed personal medicine settings without altering stock ledger."""
    med = get_owned_medicine(db, user, med_id)
    updates = payload.model_dump(exclude_unset=True)
    for field in ("display_name", "dose_unit", "instructions"):
        if field in updates and updates[field] is not None:
            updates[field] = updates[field].strip()

    for field, value in updates.items():
        setattr(med, field, value)

    db.commit()
    db.refresh(med)
    return PersonalMedicineResponse.model_validate(med)
