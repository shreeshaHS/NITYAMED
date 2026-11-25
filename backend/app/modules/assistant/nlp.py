"""Language detection, normalization, safety rules, ML intent routing, and entity extraction."""

from decimal import Decimal
from functools import lru_cache
from pathlib import Path
import re

import joblib

from app.modules.medicines.models import PersonalMedicine

MODEL_PATH = Path(__file__).resolve().parents[3] / "ml" / "artifacts" / "intent_classifier.joblib"
OOS_CONFIDENCE_THRESHOLD = 0.25

_SPELLING_FIXES: dict[str, str] = {
    "tablt": "tablet",
    "tablts": "tablets",
    "medicin": "medicine",
    "medicins": "medicines",
    "medcine": "medicine",
    "mrng": "morning",
    "mrning": "morning",
    "evng": "evening",
    "inventry": "inventory",
    "skedule": "schedule",
    "refil": "refill",
    "stok": "stock",
    "purchsed": "purchased",
    "updat": "update",
    "tday": "today",
    "wen": "when",
    "shud": "should",
    "wich": "which",
    "nxt": "next",
    "hav": "have",
    "hv": "have",
    "takn": "taken",
}

_NUMBER_WORDS: dict[str, int] = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "ten": 10,
    "fifteen": 15,
    "twenty": 20,
    "ek": 1,
    "do": 2,
    "teen": 3,
    "das": 10,
    "ondu": 1,
    "eradu": 2,
    "mooru": 3,
    "hattu": 10,
    "एक": 1,
    "दो": 2,
    "दस": 10,
    "ಒಂದು": 1,
    "ಎರಡು": 2,
    "ಹತ್ತು": 10,
}

_CLINICAL_UNSAFE_PATTERNS: tuple[str, ...] = (
    r"\b(stop|quit|discontinue)\b.*\b(tablet|pill|medicine|dose|drug)\b",
    r"\b(double|increase|decrease|change)\b.*\b(dose|dosage)\b",
    r"\b(diagnose|prescribe|recommend)\b",
    r"\bdo i have\b(?!.*\b(left|remaining|stock|balance)\b).*\b(diabetes|hypertension|bp|disease|infection|cancer|heart|illness|symptom|pain)\b",
    r"\b(which|what)\b.*\b(antibiotic|painkiller|medicine)\b.*\b(buy|take for)\b",
    r"(band kar|bandh kar|nilisabahuda|ನಿಲ್ಲಿಸಬಹುದಾ|बंद कर दूं)",
    r"(kaunsi nayi dawai|yava antibiotic|दो गुना|ಜಾಸ್ತಿ ಮಾಡ)",
)


def detect_language(text: str, fallback: str = "en") -> str:
    """Detect Kannada, Hindi, or English (with romanized fallback preference)."""
    if re.search(r"[\u0C80-\u0CFF]", text):
        return "kn"
    if re.search(r"[\u0900-\u097F]", text):
        return "hi"
    return fallback if fallback in {"en", "kn", "hi"} else "en"


def normalize_text(text: str) -> str:
    """Clean whitespace and normalize common ASR/spelling errors without touching Unicode scripts."""
    cleaned = re.sub(r"\s+", " ", text.strip().lower())
    tokens = cleaned.split(" ")
    normalized_tokens = [_SPELLING_FIXES.get(tok.strip("?.!,"), tok.strip("?.!,")) for tok in tokens]
    return " ".join(t for t in normalized_tokens if t)


def is_unsafe_clinical_query(norm_text: str) -> bool:
    """Detect clinical diagnosis, prescribing, or dose-alteration questions for strict refusal."""
    return any(re.search(pat, norm_text, re.IGNORECASE) for pat in _CLINICAL_UNSAFE_PATTERNS)


@lru_cache(maxsize=1)
def load_intent_model():
    """Load trained joblib intent classifier artifact once per process."""
    if not MODEL_PATH.exists():
        return None
    return joblib.load(MODEL_PATH)


def classify_intent(norm_text: str) -> tuple[str, float, str]:
    """Classify user query using safety rules, fast deterministic rules, then custom ML model.

    Returns (intent, confidence, source).
    """
    if is_unsafe_clinical_query(norm_text):
        return "out_of_scope_clinical", 1.0, "safety_guard"

    # Fast unambiguous rule shortcuts for critical follow-up / clear commands
    if re.search(r"\b(weather|cricket|song|cab|joke|rain)\b", norm_text):
        return "out_of_scope", 0.99, "rule"

    model = load_intent_model()
    if model is not None:
        probs = model.predict_proba([norm_text])[0]
        best_idx = int(probs.argmax())
        intent = str(model.classes_[best_idx])
        conf = float(probs[best_idx])
        if conf < OOS_CONFIDENCE_THRESHOLD:
            return "out_of_scope", conf, "ml_model"
        return intent, round(conf, 4), "ml_model"

    return "out_of_scope", 0.0, "clarification"


def extract_time_window(norm_text: str) -> str | None:
    """Extract daypart hint across English, Kannada, and Hindi."""
    if any(w in norm_text for w in ("morning", "beligge", "ಬೆಳಗಿನ", "ಬೆಳಗ್ಗೆ", "subah", "सुबह")):
        return "morning"
    if any(w in norm_text for w in ("afternoon", "madhyahna", "ಮಧ್ಯಾಹ್ನ", "dopahar", "दोपहर")):
        return "afternoon"
    if any(w in norm_text for w in ("evening", "sanje", "ಸಂಜೆ", "sham", "शाम")):
        return "evening"
    if any(w in norm_text for w in ("night", "tonight", "ratri", "ರಾತ್ರಿ", "raat", "रात")):
        return "night"
    return None


def extract_quantity_and_unit(norm_text: str) -> tuple[Decimal | None, bool]:
    """Extract numeric quantity and whether the user specified packs/strips."""
    is_pack = any(w in norm_text for w in ("strip", "strips", "pack", "packs", "patta", "पत्ता", "ಸ್ಟ್ರಿಪ್"))
    digit_match = re.search(r"\b(\d+(?:\.\d+)?)\b", norm_text)
    if digit_match:
        return Decimal(digit_match.group(1)), is_pack

    for word, val in _NUMBER_WORDS.items():
        if re.search(rf"(?:^|\s){re.escape(word)}(?:\s|$)", norm_text):
            return Decimal(val), is_pack

    if is_pack:
        return Decimal("1"), True
    return None, False


def match_user_medicines(
    norm_text: str, user_meds: list[PersonalMedicine]
) -> list[PersonalMedicine]:
    """Find user-owned medicines mentioned in the utterance."""
    matches: list[PersonalMedicine] = []
    for med in user_meds:
        candidates = [med.display_name.lower()]
        if med.generic_name:
            candidates.append(med.generic_name.lower())
        tokens = {
            tok
            for c in candidates
            for tok in re.split(r"[\s\-]+", c)
            if len(tok) >= 3 and not tok.isdigit() and tok not in {"tablet", "syrup", "mg", "mcg"}
        }
        if any(c in norm_text for c in candidates) or any(
            re.search(rf"\b{re.escape(tok)}\b", norm_text) for tok in tokens
        ):
            matches.append(med)
    return matches
