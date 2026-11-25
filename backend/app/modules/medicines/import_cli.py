"""CLI utility to bulk-import an Indian medicine CSV/JSON file into NityaMed's database."""

import argparse
from pathlib import Path

from app.core.database import Base, SessionLocal, engine
import app.modules.auth.models  # noqa: F401
import app.modules.inventory.models  # noqa: F401
import app.modules.medicines.models  # noqa: F401
from app.modules.medicines.importer import import_from_file
from app.modules.medicines.seed import seed_medicine_catalogue


def main() -> None:
    """Parse CLI args and import the provided medicine dataset file."""
    parser = argparse.ArgumentParser(description="Import Indian medicine dataset into NityaMed")
    parser.add_argument("--file", type=Path, required=True, help="Path to .csv or .json dataset")
    args = parser.parse_args()

    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seeded = seed_medicine_catalogue(db)
        summary = import_from_file(db, args.file)
        print(
            f"Seeded starter={seeded}, Imported inserted={summary.inserted}, "
            f"skipped_duplicates={summary.skipped_duplicates}, skipped_invalid={summary.skipped_invalid}"
        )


if __name__ == "__main__":
    main()
