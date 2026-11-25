"""Live external medicine lookup client using public openFDA and RxNorm REST APIs."""

from dataclasses import dataclass
from datetime import date, datetime
import re

import httpx

from app.core.config import get_settings

# Map common Indian INN drug names to USAN terms used by U.S. FDA / RxNorm.
PHRASE_ALIASES: dict[str, str] = {
    "sodium valproate": "valproate sodium",
    "clavulanic acid": "clavulanate",
}

INN_TO_USAN_ALIASES: dict[str, str] = {
    "paracetamol": "acetaminophen",
    "salbutamol": "albuterol",
    "frusemide": "furosemide",
    "lignocaine": "lidocaine",
    "adrenaline": "epinephrine",
    "noradrenaline": "norepinephrine",
    "amoxycillin": "amoxicillin",
    "glibenclamide": "glyburide",
}

_DOSAGE_FORM_KEYWORDS: tuple[tuple[str, str], ...] = (
    ("tablet", "tablet"),
    ("caplet", "tablet"),
    ("capsule", "capsule"),
    ("softgel", "capsule"),
    ("gelcap", "capsule"),
    ("syrup", "syrup"),
    ("solution", "syrup"),
    ("suspension", "syrup"),
    ("inhal", "inhaler"),
    ("aerosol", "inhaler"),
    ("ophthalmic", "drops"),
    ("otic", "drops"),
    ("drops", "drops"),
    ("inject", "injection"),
)


@dataclass(slots=True)
class ExternalMedicineRecord:
    """Normalized medicine and verified labeling record returned from public APIs."""

    brand_name: str
    generic_name: str
    active_ingredients: str | None
    strength: str
    dosage_form: str
    manufacturer: str | None
    category: str
    common_uses: str
    mechanism: str
    side_effects: str
    precautions: str
    source_name: str
    source_url: str | None
    verified_at: date


def _first_text(section: list[str] | None, max_len: int = 900) -> str | None:
    """Extract and trim the first non-empty string from an openFDA label field."""
    if not section:
        return None
    cleaned = re.sub(r"\s+", " ", section[0]).strip()
    if not cleaned:
        return None
    if len(cleaned) > max_len:
        return cleaned[: max_len - 3].rstrip() + "..."
    return cleaned


def _map_dosage_form(routes: list[str] | None, product_types: list[str] | None, text_hint: str) -> str:
    """Map FDA route/dosage metadata to NityaMed's supported dosage_form enum."""
    combined = " ".join((routes or []) + (product_types or []) + [text_hint]).lower()
    for keyword, form in _DOSAGE_FORM_KEYWORDS:
        if keyword in combined:
            return form
    return "other"


def _parse_effective_date(raw_date: str | None) -> date:
    """Parse openFDA YYYYMMDD effective_time safely, falling back to today."""
    if raw_date and len(raw_date) >= 8 and raw_date[:8].isdigit():
        try:
            return datetime.strptime(raw_date[:8], "%Y%m%d").date()
        except ValueError:
            pass
    return date.today()


def _normalize_query_term(query: str) -> str:
    """Translate common Indian INN names/phrases to USAN equivalents for FDA/RxNorm lookup."""
    lowered = re.sub(r"\s+", " ", query.lower()).strip()
    for src, dst in PHRASE_ALIASES.items():
        if src in lowered:
            lowered = lowered.replace(src, dst)
    tokens = re.findall(r"[a-zA-Z0-9-]+", lowered)
    mapped = [INN_TO_USAN_ALIASES.get(tok, tok) for tok in tokens]
    return " ".join(mapped).strip()


def _resolve_rxnorm_name(client: httpx.Client, base_url: str, query: str) -> str | None:
    """Query RxNorm approximateTerm to normalize misspelled or brand/generic drug strings."""
    try:
        resp = client.get(
            f"{base_url}/approximateTerm.json",
            params={"term": query, "maxEntries": 1},
        )
        if resp.status_code != 200:
            return None
        candidates = resp.json().get("approximateGroup", {}).get("candidate") or []
        if candidates and candidates[0].get("name"):
            return str(candidates[0]["name"])
    except (httpx.HTTPError, ValueError, KeyError):
        return None
    return None


def _parse_openfda_result(item: dict) -> ExternalMedicineRecord | None:
    """Convert a single openFDA drug label JSON item into ExternalMedicineRecord."""
    openfda = item.get("openfda") or {}
    brands = openfda.get("brand_name") or []
    generics = openfda.get("generic_name") or []
    substances = openfda.get("substance_name") or []
    manufacturers = openfda.get("manufacturer_name") or []
    pharm_classes = openfda.get("pharm_class_epc") or openfda.get("pharm_class_moa") or []
    routes = openfda.get("route") or []
    product_types = openfda.get("product_type") or []
    fda_forms = openfda.get("dosage_form") or []

    generic_name = (generics[0] if generics else (substances[0] if substances else "")).strip()
    brand_name = (brands[0] if brands else generic_name).strip()
    if not brand_name or not generic_name:
        return None

    dosage_and_admin = _first_text(item.get("dosage_and_administration"), max_len=600) or ""
    strength_hint = _first_text(item.get("active_ingredient"), max_len=120)
    strength = strength_hint or "See label"
    if len(strength) > 95:
        strength = strength[:95].rstrip()

    dosage_form = _map_dosage_form(
        routes, product_types + fda_forms, f"{dosage_and_admin} {brand_name}"
    )
    common_uses = _first_text(item.get("indications_and_usage")) or (
        "Official FDA labeling available; consult prescribing details for specific uses."
    )
    mechanism = (
        _first_text(item.get("mechanism_of_action"))
        or _first_text(item.get("clinical_pharmacology"))
        or "Mechanism summary is detailed in the official FDA clinical pharmacology label."
    )
    side_effects = _first_text(item.get("adverse_reactions")) or (
        "Refer to official FDA label adverse reactions or consult your pharmacist."
    )
    precautions = (
        _first_text(item.get("warnings_and_precautions"))
        or _first_text(item.get("warnings"))
        or _first_text(item.get("precautions"))
        or "Follow your prescribed directions and consult a doctor or pharmacist before changes."
    )

    set_id = item.get("set_id")
    source_url = (
        f"https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid={set_id}"
        if set_id
        else "https://open.fda.gov/apis/drug/label/"
    )

    return ExternalMedicineRecord(
        brand_name=brand_name[:200],
        generic_name=generic_name[:200],
        active_ingredients=", ".join(substances)[:500] if substances else None,
        strength=strength[:100],
        dosage_form=dosage_form,
        manufacturer=manufacturers[0][:200] if manufacturers else None,
        category=(pharm_classes[0][:150] if pharm_classes else "FDA Labeled Medication"),
        common_uses=common_uses,
        mechanism=mechanism,
        side_effects=side_effects,
        precautions=precautions,
        source_name="U.S. FDA / openFDA Drug Label",
        source_url=source_url,
        verified_at=_parse_effective_date(item.get("effective_time")),
    )


def fetch_external_medicines(
    query: str,
    limit: int = 5,
    client: httpx.Client | None = None,
) -> list[ExternalMedicineRecord]:
    """Fetch and normalize medicine label entries from openFDA (with RxNorm fallback).

    Returns an empty list cleanly if offline, timed out, or no match exists.
    """
    settings = get_settings()
    if not settings.external_med_api_enabled or len(query.strip()) < 2:
        return []

    normalized = _normalize_query_term(query)
    if not normalized:
        return []

    own_client = client is None
    http = client or httpx.Client(timeout=settings.external_med_timeout_sec)

    try:
        records = _query_openfda(http, settings.openfda_base_url, normalized, limit)
        if not records:
            rx_name = _resolve_rxnorm_name(http, settings.rxnorm_base_url, normalized)
            if rx_name and rx_name.lower() != normalized.lower():
                records = _query_openfda(http, settings.openfda_base_url, rx_name, limit)
        return records
    except (httpx.HTTPError, ValueError):
        return []
    finally:
        if own_client:
            http.close()


def _query_openfda(
    http: httpx.Client, base_url: str, term: str, limit: int
) -> list[ExternalMedicineRecord]:
    """Query openFDA drug label endpoint for matching generic or brand names."""
    safe_term = re.sub(r'["\\]', "", term).strip()
    if not safe_term:
        return []

    search_expr = f'(openfda.generic_name:"{safe_term}" OR openfda.brand_name:"{safe_term}")'
    resp = http.get(
        base_url,
        params={"search": search_expr, "limit": min(limit, 10)},
    )
    if resp.status_code != 200:
        return []

    results = resp.json().get("results") or []
    parsed: list[ExternalMedicineRecord] = []
    seen_keys: set[tuple[str, str, str]] = set()
    for item in results:
        rec = _parse_openfda_result(item)
        if rec is None:
            continue
        dedup = (rec.brand_name.lower(), rec.strength.lower(), rec.dosage_form)
        if dedup in seen_keys:
            continue
        seen_keys.add(dedup)
        parsed.append(rec)
    return parsed
