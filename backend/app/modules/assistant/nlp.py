"""Language detection, normalization, safety rules, ML intent routing, and entity extraction."""

from decimal import Decimal
from difflib import SequenceMatcher
from functools import lru_cache
from pathlib import Path
import re

import joblib

from app.modules.medicines.models import PersonalMedicine

MODEL_PATH = Path(__file__).resolve().parents[3] / "ml" / "artifacts" / "intent_classifier.joblib"
OOS_CONFIDENCE_THRESHOLD = 0.28

_SPELLING_FIXES: dict[str, str] = {
    "tablt": "tablet",
    "tablts": "tablets",
    "tab": "tablet",
    "tabs": "tablets",
    "capsul": "capsule",
    "cap": "capsule",
    "caps": "capsules",
    "syurp": "syrup",
    "med": "medicine",
    "meds": "medicines",
    "medicin": "medicine",
    "medicins": "medicines",
    "medcine": "medicine",
    "mrng": "morning",
    "mrning": "morning",
    "evng": "evening",
    "aftrnoon": "afternoon",
    "nit": "night",
    "nite": "night",
    "inventry": "inventory",
    "invntry": "inventory",
    "skedule": "schedule",
    "shedule": "schedule",
    "remndr": "reminder",
    "refil": "refill",
    "stok": "stock",
    "stck": "stock",
    "remng": "remaining",
    "bttl": "bottle",
    "strp": "strip",
    "purchsed": "purchased",
    "bot": "bought",
    "updat": "update",
    "confrm": "confirm",
    "cnfrm": "confirm",
    "tday": "today",
    "2day": "today",
    "wen": "when",
    "shud": "should",
    "wich": "which",
    "nxt": "next",
    "hav": "have",
    "hv": "have",
    "takn": "taken",
    "tkn": "taken",
}

_NUMBER_WORDS: dict[str, Decimal] = {
    "half": Decimal("0.5"),
    "one": Decimal("1"),
    "two": Decimal("2"),
    "three": Decimal("3"),
    "four": Decimal("4"),
    "five": Decimal("5"),
    "six": Decimal("6"),
    "eight": Decimal("8"),
    "ten": Decimal("10"),
    "fifteen": Decimal("15"),
    "twenty": Decimal("20"),
    "thirty": Decimal("30"),
    "aadha": Decimal("0.5"),
    "ardha": Decimal("0.5"),
    "ek": Decimal("1"),
    "do": Decimal("2"),
    "teen": Decimal("3"),
    "char": Decimal("4"),
    "paanch": Decimal("5"),
    "das": Decimal("10"),
    "ondu": Decimal("1"),
    "eradu": Decimal("2"),
    "mooru": Decimal("3"),
    "naalku": Decimal("4"),
    "aidu": Decimal("5"),
    "hattu": Decimal("10"),
    "एक": Decimal("1"),
    "दो": Decimal("2"),
    "तीन": Decimal("3"),
    "दस": Decimal("10"),
    "आधा": Decimal("0.5"),
    "ಒಂದು": Decimal("1"),
    "ಎರಡು": Decimal("2"),
    "ಮೂರು": Decimal("3"),
    "ಹತ್ತು": Decimal("10"),
    "ಅರ್ಧ": Decimal("0.5"),
}

_AFFIRMATIVE_CONFIRMATIONS = {
    "yes",
    "yeah",
    "yep",
    "yup",
    "confirm",
    "confirmed",
    "ok",
    "okay",
    "sure",
    "approve",
    "yes confirm",
    "confirm it",
    "please confirm",
    "go ahead",
    "haan",
    "han",
    "ha",
    "theek hai",
    "sahi hai",
    "haudu",
    "houdu",
    "sari",
    "ಹೌದು",
    "ಸರಿ",
    "ಕನ್ಫರ್ಮ್",
    "ಕನ್ಫರ್ಮ್ ಮಾಡಿ",
    "हाँ",
    "हां",
    "जी",
    "ठीक है",
    "कन्फर्म",
    "कन्फर्म करो",
}

_NEGATIVE_CONFIRMATIONS = {
    "no",
    "nope",
    "nah",
    "cancel",
    "stop",
    "abort",
    "cancel it",
    "dont",
    "don't",
    "no thanks",
    "nahi",
    "nahin",
    "mat karo",
    "cancel karo",
    "beda",
    "byada",
    "cancel maadi",
    "ಬೇಡ",
    "ಬ್ಯಾಡ",
    "ರದ್ದು",
    "ರದ್ದು ಮಾಡಿ",
    "ನಿಲ್ಲಿಸಿ",
    "नहीं",
    "मत करो",
    "रद्द करो",
    "कैंसल",
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
    """Clean whitespace, strip gentle voice fillers, and fix common ASR/typos safely."""
    cleaned = re.sub(r"\s+", " ", text.strip().lower())
    cleaned = re.sub(r"^(?:hey|ok|okay|hi|hello)\s+(?:nityamed|nitya med|assistant)[,\s]*", "", cleaned)
    tokens = cleaned.split(" ")
    normalized_tokens = [
        _SPELLING_FIXES.get(tok.strip("?.!,;:\"'()"), tok.strip("?.!,;:\"'()"))
        for tok in tokens
    ]
    return " ".join(t for t in normalized_tokens if t)


def parse_voice_confirmation_reply(norm_text: str) -> bool | None:
    """Detect hands-free yes/confirm or no/cancel utterances while a confirmation prompt is active."""
    if norm_text in _AFFIRMATIVE_CONFIRMATIONS:
        return True
    if norm_text in _NEGATIVE_CONFIRMATIONS:
        return False
    return None


def extract_company_query(norm_text: str) -> str | None:
    """Extract a pharmaceutical manufacturer/company token from a conversational query."""
    patterns = (
        r"(?:made by|manufactured by|from company|company named|company)\s+([a-z0-9\s&-]{2,40})",
        r"([a-z0-9&-]{3,25})\s+(?:company|pharma|labs|laboratories|medicines|tablets|pills)",
    )
    for pat in patterns:
        m = re.search(pat, norm_text, re.IGNORECASE)
        if m:
            candidate = re.sub(
                r"\b(company|medicines|medicine|tablets|tablet|pills|capsules|syrup|please|only|remember|name|show|find|which|make|makes|what)\b",
                " ",
                m.group(1),
            )
            cleaned = re.sub(r"\s+", " ", candidate).strip(" ?.,!")
            if len(cleaned) >= 2:
                return cleaned
    return None


def is_greeting_or_help(norm_text: str) -> bool:
    """Detect conversational greetings, gratitude, or help requests."""
    return bool(
        re.fullmatch(
            r"(?:hi|hello|hey|good morning|good afternoon|good evening|namaste|namaskara|vanakkam|"
            r"thanks|thank you|dhanyavad|dhanyavaad|ನಮಸ್ಕಾರ|ಧನ್ಯವಾದ|ಹಾಯ್|ಹಲೋ|नमस्ते|धन्यवाद|हाय|हेलो|"
            r"help|what can you do|who are you|how do you work|sahaya|ಸಹಾಯ|मदद)",
            norm_text,
        )
    )


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

    if is_greeting_or_help(norm_text):
        return "greeting_help", 0.99, "rule"

    # Fast unambiguous rule shortcuts for clear non-medication queries
    if re.search(
        r"\b(weather|cricket|song|songs|music|cab|taxi|joke|rain|movie|news|recipe|pizza|biryani)\b",
        norm_text,
    ):
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
            return val, is_pack

    if is_pack:
        return Decimal("1"), True
    return None, False


_MED_STOPWORDS = {
    "tablet",
    "tablets",
    "capsule",
    "capsules",
    "syrup",
    "injection",
    "inhaler",
    "drops",
    "medicine",
    "medicines",
    "pill",
    "pills",
    "dose",
    "doses",
    "stock",
    "morning",
    "afternoon",
    "evening",
    "night",
    "today",
    "please",
    "check",
    "confirm",
    "taken",
    "dawai",
    "goli",
    "matre",
    "gulige",
    "strip",
    "pack",
}


def match_user_medicines(
    norm_text: str, user_meds: list[PersonalMedicine]
) -> list[PersonalMedicine]:
    """Find user-owned medicines mentioned in the utterance with ASR fuzzy fallback."""
    exact_matches: list[PersonalMedicine] = []
    med_tokens_map: list[tuple[PersonalMedicine, set[str]]] = []

    for med in user_meds:
        candidates = [med.display_name.lower()]
        if med.generic_name:
            candidates.append(med.generic_name.lower())
        tokens = {
            tok
            for c in candidates
            for tok in re.split(r"[\s\-/()]+", c)
            if len(tok) >= 3 and not tok.isdigit() and tok not in _MED_STOPWORDS
        }
        med_tokens_map.append((med, tokens))
        if any(c in norm_text for c in candidates) or any(
            re.search(rf"\b{re.escape(tok)}\b", norm_text) for tok in tokens
        ):
            exact_matches.append(med)

    if exact_matches:
        return exact_matches

    utt_tokens = [
        tok
        for tok in re.findall(r"[a-z0-9\u0900-\u097f\u0c80-\u0cff]{4,}", norm_text)
        if tok not in _MED_STOPWORDS and not tok.isdigit()
    ]
    if not utt_tokens:
        return []

    fuzzy_matches: list[PersonalMedicine] = []
    for med, tokens in med_tokens_map:
        long_tokens = [tok for tok in tokens if len(tok) >= 4]
        if any(
            SequenceMatcher(None, mtok, utok).ratio() >= 0.80
            for mtok in long_tokens
            for utok in utt_tokens
        ):
            fuzzy_matches.append(med)
    return fuzzy_matches
