"""Idempotent seeder for the curated Indian medicine reference catalogue."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.medicines.models import MedicineCatalogue, MedicineEducation
from app.modules.medicines.seed_data import DEFAULT_SOURCE_NAME, SEED_MEDICINES, VERIFIED_DATE


def seed_medicine_catalogue(db: Session) -> int:
    """Insert missing curated medicines and education entries idempotently.

    Returns the count of newly inserted catalogue entries.
    """
    inserted = 0
    for item in SEED_MEDICINES:
        existing = db.scalar(
            select(MedicineCatalogue).where(
                MedicineCatalogue.brand_name == item["brand_name"],
                MedicineCatalogue.strength == item["strength"],
                MedicineCatalogue.dosage_form == item["dosage_form"],
            )
        )
        if existing is not None:
            continue

        catalogue_row = MedicineCatalogue(
            brand_name=item["brand_name"],
            generic_name=item["generic_name"],
            active_ingredients=item["active_ingredients"],
            strength=item["strength"],
            dosage_form=item["dosage_form"],
            standard_pack_size=item["standard_pack_size"],
            pack_unit=item["pack_unit"],
            manufacturer=item["manufacturer"],
            is_verified=True,
        )
        db.add(catalogue_row)
        db.flush()

        edu = item["education"]
        db.add(
            MedicineEducation(
                catalogue_id=catalogue_row.id,
                category=edu["category"],
                common_uses=edu["common_uses"],
                mechanism=edu["mechanism"],
                side_effects=edu["side_effects"],
                precautions=edu["precautions"],
                source_name=DEFAULT_SOURCE_NAME,
                source_url=None,
                verified_at=VERIFIED_DATE,
            )
        )
        inserted += 1

    if inserted > 0:
        db.commit()
    return inserted
