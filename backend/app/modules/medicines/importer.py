"""Bulk CSV and JSON importer for open-source Indian medicine datasets."""

import csv
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
import re

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.medicines.models import MedicineCatalogue

VALID_FORMS = {"tablet", "capsule", "syrup", "injection", "inhaler", "drops", "other"}

FORM_ALIASES: tuple[tuple[str, str], ...] = (
    ("tablet", "tablet"),
    ("tab", "tablet"),
    ("capsule", "capsule"),
    ("cap", "capsule"),
    ("rotacap", "capsule"),
    ("syrup", "syrup"),
    ("suspension", "syrup"),
    ("solution", "syrup"),
    ("liquid", "syrup"),
    ("injection", "injection"),
    ("inj", "injection"),
    ("inhaler", "inhaler"),
    ("inhalation", "inhaler"),
    ("drop", "drops"),
)

_COMPOSITION_RE = re.compile(r"^\s*([^(]+?)\s*\(([^)]+)\)\s*$")
_PACK_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*(tablet|tablets|capsule|capsules|cap|caps|ml|puff|puffs|vial|vials|drop|drops)\b",
    re.IGNORECASE,
)


@dataclass(slots=True)
class ImportSummary:
    """Counts summarizing a bulk catalogue import run."""

    inserted: int
    skipped_duplicates: int
    skipped_invalid: int


def normalize_dosage_form(raw_form: str | None) -> str:
    """Normalize dataset dosage form labels to NityaMed's constrained vocabulary."""
    cleaned = (raw_form or "").strip().lower()
    if cleaned in VALID_FORMS:
        return cleaned
    for alias, target in FORM_ALIASES:
        if alias in cleaned:
            return target
    return "other"


def _parse_pack_size(raw_value: str | int | float | None) -> Decimal | None:
    """Extract a positive numeric pack size if present."""
    if raw_value is None:
        return None
    text = str(raw_value).strip()
    if not text:
        return None
    try:
        val = Decimal(text)
        return val if val > 0 else None
    except InvalidOperation:
        return None


def _parse_pack_label(label: str | None) -> tuple[Decimal | None, str | None, str | None]:
    """Parse Indian pack labels like 'strip of 10 tablets' or 'bottle of 100 ml syrup'."""
    if not label:
        return None, None, None
    match = _PACK_RE.search(label)
    if not match:
        return None, None, normalize_dosage_form(label) if label.strip() else None

    qty = _parse_pack_size(match.group(1))
    raw_unit = match.group(2).lower()
    form = normalize_dosage_form(f"{raw_unit} {label}")
    unit_map = {
        "tablets": "tablet",
        "tablet": "tablet",
        "capsules": "capsule",
        "capsule": "capsule",
        "caps": "capsule",
        "cap": "capsule",
        "ml": "ml",
        "puffs": "puff",
        "puff": "puff",
        "vials": "vial",
        "vial": "vial",
        "drops": "drop",
        "drop": "drop",
    }
    return qty, unit_map.get(raw_unit, raw_unit), form


def _split_composition_parts(parts: list[str]) -> tuple[str, str]:
    """Split 'Name (Strength)' entries into combined generic_name and strength."""
    names: list[str] = []
    strengths: list[str] = []
    for part in parts:
        match = _COMPOSITION_RE.match(part)
        if match:
            names.append(match.group(1).strip())
            strengths.append(match.group(2).strip())
        else:
            names.append(part.strip())
    return " + ".join(n for n in names if n), " + ".join(s for s in strengths if s)


def _parse_composition(raw: dict) -> tuple[str, str, str]:
    """Extract generic_name, active_ingredients, and strength from standard or Kaggle columns."""
    explicit_generic = str(raw.get("generic_name") or "").strip()
    explicit_strength = str(raw.get("strength") or "").strip()
    comp1 = str(raw.get("short_composition1") or "").strip()
    comp2 = str(raw.get("short_composition2") or "").strip()
    salt_comp = str(raw.get("salt_composition") or "").strip()

    generic = explicit_generic
    strength = explicit_strength

    if not generic:
        if comp1:
            parts = [c for c in (comp1, comp2) if c]
            parsed_name, parsed_strength = _split_composition_parts(parts)
            generic = parsed_name
            if not strength:
                strength = parsed_strength
        elif salt_comp:
            parts = [p.strip() for p in salt_comp.split("+") if p.strip()]
            parsed_name, parsed_strength = _split_composition_parts(parts)
            generic = parsed_name
            if not strength:
                strength = parsed_strength

    active_ingredients = str(raw.get("active_ingredients") or "").strip() or (
        " + ".join(p for p in (comp1, comp2) if p) or salt_comp or generic
    )
    return generic, active_ingredients, strength or "Standard"


def _is_discontinued(raw: dict) -> bool:
    """Return True if a dataset row is marked discontinued."""
    flag = raw.get("Is_discontinued") if "Is_discontinued" in raw else raw.get("is_discontinued")
    if isinstance(flag, bool):
        return flag
    return str(flag or "").strip().lower() in {"true", "1", "yes"}


def import_catalogue_records(db: Session, rows: list[dict], batch_size: int = 5000) -> ImportSummary:
    """Idempotently import normalized or raw Kaggle Indian medicine rows into medicine_catalogue."""
    inserted = 0
    skipped_duplicates = 0
    skipped_invalid = 0

    existing_keys = {
        (b.lower(), s.lower(), f)
        for b, s, f in db.execute(
            select(
                MedicineCatalogue.brand_name,
                MedicineCatalogue.strength,
                MedicineCatalogue.dosage_form,
            )
        ).all()
    }

    pending_objects: list[MedicineCatalogue] = []
    for raw in rows:
        if _is_discontinued(raw):
            skipped_invalid += 1
            continue

        brand = str(raw.get("brand_name") or raw.get("name") or "").strip()
        generic, active_ingredients, strength = _parse_composition(raw)
        if not brand or not generic:
            skipped_invalid += 1
            continue

        pack_qty, pack_unit, pack_form = _parse_pack_label(raw.get("pack_size_label"))
        explicit_form = raw.get("dosage_form") or (
            raw.get("type") if str(raw.get("type") or "").lower() not in {"allopathy", "ayurveda"} else None
        )
        dosage_form = (
            normalize_dosage_form(str(explicit_form))
            if explicit_form
            else (pack_form or normalize_dosage_form(brand))
        )

        key = (brand[:200].lower(), strength[:100].lower(), dosage_form)
        if key in existing_keys:
            skipped_duplicates += 1
            continue
        existing_keys.add(key)

        standard_pack_size = (
            _parse_pack_size(raw.get("standard_pack_size") or raw.get("pack_size")) or pack_qty
        )
        resolved_pack_unit = (
            str(raw["pack_unit"]).strip()[:30] if raw.get("pack_unit") else pack_unit
        )
        manufacturer = str(
            raw.get("manufacturer") or raw.get("manufacturer_name") or ""
        ).strip() or None

        pending_objects.append(
            MedicineCatalogue(
                brand_name=brand[:200],
                generic_name=generic[:200],
                active_ingredients=active_ingredients[:500],
                strength=strength[:100],
                dosage_form=dosage_form,
                standard_pack_size=standard_pack_size,
                pack_unit=resolved_pack_unit,
                manufacturer=manufacturer[:200] if manufacturer else None,
                is_verified=bool(raw.get("is_verified", True)),
            )
        )
        inserted += 1

        if len(pending_objects) >= batch_size:
            db.add_all(pending_objects)
            db.commit()
            pending_objects.clear()

    if pending_objects:
        db.add_all(pending_objects)
        db.commit()

    return ImportSummary(
        inserted=inserted,
        skipped_duplicates=skipped_duplicates,
        skipped_invalid=skipped_invalid,
    )


def import_from_file(db: Session, file_path: Path) -> ImportSummary:
    """Import Indian medicine dataset entries from a CSV or JSON file."""
    suffix = file_path.suffix.lower()
    if suffix == ".json":
        payload = json.loads(file_path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise ValueError("JSON dataset must contain a top-level array of medicine objects")
        return import_catalogue_records(db, payload)

    if suffix == ".csv":
        with file_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            return import_catalogue_records(db, list(reader))

    raise ValueError(f"Unsupported dataset format: {suffix}")
