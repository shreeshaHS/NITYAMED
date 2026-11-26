"""Indian CDSCO / regulatory and clinical safety policy checks for medicines."""

import re

# Prohibited/withdrawn molecules under Indian CDSCO / Drugs & Cosmetics Act notifications
# and non-medical illicit controlled substances blocked from scheduling/verification.
PROHIBITED_SUBSTANCES: tuple[tuple[str, str], ...] = (
    ("sibutramine", "Banned anti-obesity drug (withdrawn by CDSCO)"),
    ("rimonabant", "Banned cannabinoid receptor antagonist (withdrawn by CDSCO)"),
    ("cisapride", "Banned prokinetic agent due to cardiac arrhythmia risk (CDSCO)"),
    ("phenylpropanolamine", "Banned decongestant (CDSCO notification)"),
    ("rofecoxib", "Withdrawn COX-2 inhibitor (CDSCO)"),
    ("valdecoxib", "Withdrawn COX-2 inhibitor (CDSCO)"),
    ("tegaserod", "Withdrawn GI motility drug (CDSCO)"),
    ("rosiglitazone", "Suspended/banned thiazolidinedione (CDSCO)"),
    ("astemizole", "Banned antihistamine (CDSCO)"),
    ("terfenadine", "Banned antihistamine (CDSCO)"),
    ("gatifloxacin", "Systemic gatifloxacin banned by CDSCO"),
    ("dexpropoxyphene", "Withdrawn analgesic (CDSCO)"),
    ("heroin", "Prohibited narcotic substance under NDPS Act"),
    ("cocaine", "Prohibited narcotic substance under NDPS Act"),
    ("methamphetamine", "Prohibited psychotropic substance under NDPS Act"),
    ("mdma", "Prohibited psychotropic substance under NDPS Act"),
    ("cannabis", "Prohibited controlled substance unless specially licensed"),
    ("marijuana", "Prohibited controlled substance under NDPS Act"),
    ("lysergic acid", "Prohibited hallucinogen (LSD) under NDPS Act"),
)

_PROHIBITED_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(rf"\b{re.escape(term)}\b", re.IGNORECASE), reason)
    for term, reason in PROHIBITED_SUBSTANCES
]


def check_medicine_policy(
    brand_name: str | None,
    generic_name: str | None = None,
    active_ingredients: str | None = None,
) -> tuple[bool, str | None]:
    """Validate medicine names/compositions against regulatory and prohibited substance rules.

    Returns (is_allowed, violation_reason).
    """
    combined = " ".join(part for part in (brand_name, generic_name, active_ingredients) if part)
    if not combined.strip():
        return False, "Medicine name or composition is required."

    for pattern, reason in _PROHIBITED_PATTERNS:
        if pattern.search(combined):
            return False, f"Restricted under medication safety & regulatory policy: {reason}."

    return True, None
