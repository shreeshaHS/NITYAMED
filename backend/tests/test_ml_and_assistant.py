"""Tests for Phase 5 multilingual ML intent classifier and safety-guarded hybrid assistant."""

from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.main import create_app
from app.modules.assistant.adapters import BoundedLLMAdapter, STTAdapter, STTResult
from app.modules.assistant.router import get_llm_adapter, get_stt_adapter
from app.modules.medicines.seed import seed_medicine_catalogue
from ml.train_and_eval import MODEL_PATH, evaluate_models


def _auth_header(client: TestClient, email: str) -> dict[str, str]:
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "StrongPassword123",
            "display_name": "Assistant Patient",
            "preferred_lang": "en",
        },
    )
    assert resp.status_code == 201
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _setup_dolo_with_schedule(client: TestClient, db_session: Session, headers: dict[str, str]) -> dict:
    seed_medicine_catalogue(db_session)
    cat_id = client.get(
        "/api/v1/catalogue/search?q=Dolo&include_external=false", headers=headers
    ).json()[0]["id"]
    med = client.post(
        "/api/v1/medicines",
        headers=headers,
        json={
            "catalogue_id": cat_id,
            "dose_per_intake": "1.00",
            "dose_unit": "tablet",
            "stock_unit": "tablet",
            "initial_packs": 1,
            "initial_loose_units": "0.00",
        },
    ).json()

    now_ist = datetime.now(ZoneInfo("Asia/Kolkata"))
    today = now_ist.date()
    active_time = now_ist.strftime("%H:%M")
    client.post(
        f"/api/v1/medicines/{med['id']}/schedules",
        headers=headers,
        json={
            "frequency_type": "once_daily",
            "times": [{"time": active_time, "dose": "1.00"}],
            "start_date": today.isoformat(),
            "horizon_days": 5,
        },
    )
    return med


def test_ml_benchmark_and_saved_artifact() -> None:
    assert MODEL_PATH.exists()
    report = evaluate_models()
    assert report["dataset_size"] >= 600
    best_f1 = max(m["macro_f1"] for m in report["models"].values())
    assert best_f1 >= 0.80


def test_assistant_readonly_multilingual_and_dialogue_followup(
    client: TestClient, db_session: Session
) -> None:
    headers = _auth_header(client, "voice_read@example.com")
    _setup_dolo_with_schedule(client, db_session, headers)

    # English stock check
    r1 = client.post(
        "/api/v1/assistant/text",
        headers=headers,
        json={"text": "How many tablets of Dolo do I have left?"},
    )
    assert r1.status_code == 200
    assert r1.json()["intent"] == "check_stock"
    assert "15.00 tablet" in r1.json()["reply_text"]
    assert r1.json()["requires_confirmation"] is False

    # Follow-up without repeating medicine name resolves Dolo from conversation_states
    r_followup = client.post(
        "/api/v1/assistant/text",
        headers=headers,
        json={"text": "When should I refill it?"},
    )
    assert r_followup.status_code == 200
    assert r_followup.json()["intent"] == "refill_check"
    assert "Dolo 650" in r_followup.json()["reply_text"]

    # Romanized Kannada stock check
    r_knr = client.post(
        "/api/v1/assistant/text",
        headers=headers,
        json={"text": "nanna hatra eshtu tablet ulidide"},
    )
    assert r_knr.status_code == 200
    assert r_knr.json()["intent"] == "check_stock"

    # Verified medicine education query
    r_info = client.post(
        "/api/v1/assistant/text",
        headers=headers,
        json={"text": "Why is Dolo used?"},
    )
    assert r_info.status_code == 200
    assert r_info.json()["intent"] == "medicine_info"
    assert "Source:" in r_info.json()["reply_text"]


def test_assistant_safety_refuses_clinical_and_oos_queries(client: TestClient) -> None:
    headers = _auth_header(client, "safety@example.com")

    for prompt in (
        "Should I stop taking my blood pressure tablet?",
        "kya main apni sugar ki goli band kar doon",
        "naanu bp tablet nilisabahuda heli",
    ):
        resp = client.post("/api/v1/assistant/text", headers=headers, json={"text": prompt})
        assert resp.status_code == 200
        assert resp.json()["classification_source"] == "safety_guard"
        assert resp.json()["requires_confirmation"] is False

    oos = client.post(
        "/api/v1/assistant/text",
        headers=headers,
        json={"text": "What is the weather forecast tomorrow?"},
    )
    assert oos.status_code == 200
    assert "out_of_scope" in oos.json()["intent"]


def test_assistant_confirmation_gate_for_stock_and_dose(
    client: TestClient, db_session: Session
) -> None:
    headers = _auth_header(client, "confirm_gate@example.com")
    med = _setup_dolo_with_schedule(client, db_session, headers)

    # Step 1: Request purchase update -> staged only, stock still 15.00
    stage = client.post(
        "/api/v1/assistant/text",
        headers=headers,
        json={"text": "I purchased 1 more strip of Dolo update my stock"},
    )
    assert stage.status_code == 200
    data = stage.json()
    assert data["intent"] == "update_stock_purchase"
    assert data["requires_confirmation"] is True
    assert data["confirmation_token"] is not None
    assert client.get(f"/api/v1/medicines/{med['id']}", headers=headers).json()["medicine"]["confirmed_stock"] == "15.00"

    # Step 2: Explicit confirmation executes +15 -> 30.00
    confirmed = client.post(
        "/api/v1/assistant/confirm",
        headers=headers,
        json={"confirmation_token": data["confirmation_token"], "approved": True},
    )
    assert confirmed.status_code == 200
    assert "30.00" in confirmed.json()["reply_text"]

    # Step 3: Stage dose confirmation and cancel -> stock remains 30.00
    dose_stage = client.post(
        "/api/v1/assistant/text",
        headers=headers,
        json={"text": "I just took my morning tablet of Dolo"},
    )
    assert dose_stage.status_code == 200
    assert dose_stage.json()["intent"] == "confirm_dose"
    assert dose_stage.json()["requires_confirmation"] is True

    cancelled = client.post(
        "/api/v1/assistant/confirm",
        headers=headers,
        json={"confirmation_token": dose_stage.json()["confirmation_token"], "approved": False},
    )
    assert cancelled.status_code == 200
    assert "cancelled" in cancelled.json()["reply_text"].lower()
    assert client.get(f"/api/v1/medicines/{med['id']}", headers=headers).json()["medicine"]["confirmed_stock"] == "30.00"


def test_assistant_voice_endpoint_with_mocked_stt(db_session: Session) -> None:
    class FakeHindiSTT(STTAdapter):
        def transcribe(self, audio_bytes: bytes, filename: str, language_hint: str | None = None) -> STTResult:
            return STTResult(transcript="आज मुझे कौन सी दवाइयां लेनी हैं", detected_language="hi")

    app = create_app()
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_stt_adapter] = lambda: FakeHindiSTT()

    with TestClient(app) as custom_client:
        headers = _auth_header(custom_client, "voice_hi@example.com")
        _setup_dolo_with_schedule(custom_client, db_session, headers)

        resp = custom_client.post(
            "/api/v1/assistant/voice",
            headers=headers,
            files={"audio": ("query.wav", b"RIFF0000", "audio/wav")},
        )
        assert resp.status_code == 200
        assert resp.json()["language"] == "hi"
        assert resp.json()["intent"] == "today_schedule"
        assert "Dolo 650" in resp.json()["reply_text"]


def test_kundapura_kannada_dialect_and_llm_fallback(
    client: TestClient, db_session: Session
) -> None:
    headers = _auth_header(client, "kundapura@example.com")
    _setup_dolo_with_schedule(client, db_session, headers)

    # Kundapura / Coastal Kannada dialect query handled directly with native Kannada reply
    resp_kn = client.post(
        "/api/v1/assistant/text",
        headers=headers,
        json={"text": "ನನ್ ಹತ್ರ ಎಷ್ಟ್ ಗುಳಿಗೆ ಉಂಟು"},
    )
    assert resp_kn.status_code == 200
    assert resp_kn.json()["language"] == "kn"
    assert resp_kn.json()["intent"] == "check_stock"
    assert "ದೃಢೀಕೃತ ಸ್ಟಾಕ್" in resp_kn.json()["reply_text"]

    # Unseen rare regional phrasing with low ML confidence falls back safely to BoundedLLMAdapter
    class FakeDialectLLM(BoundedLLMAdapter):
        def classify_dialect_intent(self, text: str) -> tuple[str, float] | None:
            return ("today_schedule", 0.88)

    app = create_app()
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_llm_adapter] = lambda: FakeDialectLLM()

    with TestClient(app) as llm_client:
        llm_headers = _auth_header(llm_client, "dialect_llm@example.com")
        _setup_dolo_with_schedule(llm_client, db_session, llm_headers)

        # Coastal/Mangalore phrasing predicted directly by custom ML model
        resp_ml = llm_client.post(
            "/api/v1/assistant/text",
            headers=llm_headers,
            json={"text": "ivatt enu gulige tinbeku marre"},
        )
        assert resp_ml.status_code == 200
        assert resp_ml.json()["intent"] == "today_schedule"

        # Truly unseen phrasing with low ML confidence falls back safely to BoundedLLMAdapter
        resp_fb = llm_client.post(
            "/api/v1/assistant/text",
            headers=llm_headers,
            json={"text": "ee hottu oushadha thinnodaithe yavdu"},
        )
        assert resp_fb.status_code == 200
        assert resp_fb.json()["intent"] == "today_schedule"
        assert resp_fb.json()["classification_source"] == "llm_fallback"
        assert "Dolo 650" in resp_fb.json()["reply_text"]


def test_real_world_hands_free_voice_confirmation_and_localized_replies(
    client: TestClient, db_session: Session
) -> None:
    headers = _auth_header(client, "handsfree@example.com")
    med = _setup_dolo_with_schedule(client, db_session, headers)

    # Voice wake-word + ASR typo query resolves cleanly
    asr_q = client.post(
        "/api/v1/assistant/text",
        headers=headers,
        json={"text": "Hey NityaMed, how mny tablts of Dolo hv i left?"},
    )
    assert asr_q.status_code == 200
    assert asr_q.json()["intent"] == "check_stock"
    assert "15.00" in asr_q.json()["reply_text"]

    # Native Kannada info + Hindi refill replies respond in native scripts
    kn_info = client.post(
        "/api/v1/assistant/text",
        headers=headers,
        json={"text": "ಡೋಲೋ ಮಾತ್ರೆಯ ಉಪಯೋಗ ಏನು"},
    )
    assert kn_info.status_code == 200
    assert kn_info.json()["language"] == "kn"
    assert kn_info.json()["intent"] == "medicine_info"
    assert "ಮೂಲ:" in kn_info.json()["reply_text"]

    hi_ref = client.post(
        "/api/v1/assistant/text",
        headers=headers,
        json={"text": "मुझे अपनी दवाई कब रीफिल करनी चाहिए"},
    )
    assert hi_ref.status_code == 200
    assert hi_ref.json()["language"] == "hi"
    assert hi_ref.json()["intent"] == "refill_check"
    assert "रीफिल सारांश" in hi_ref.json()["reply_text"]

    # Hands-free voice confirmation: stage dose, then speak "ಹೌದು" (yes) -> commits -1 tablet
    staged = client.post(
        "/api/v1/assistant/text",
        headers=headers,
        json={"text": "ನಾನು ಈಗಷ್ಟೇ ಡೋಲೋ ಮಾತ್ರೆ ತೆಗೆದುಕೊಂಡೆ"},
    )
    assert staged.status_code == 200
    assert staged.json()["intent"] == "confirm_dose"
    assert staged.json()["requires_confirmation"] is True

    spoken_yes = client.post(
        "/api/v1/assistant/text",
        headers=headers,
        json={"text": "ಹೌದು"},
    )
    assert spoken_yes.status_code == 200
    assert spoken_yes.json()["intent"] == "confirm_dose"
    assert spoken_yes.json()["requires_confirmation"] is False
    assert "14.00" in spoken_yes.json()["reply_text"]
    assert client.get(f"/api/v1/medicines/{med['id']}", headers=headers).json()["medicine"]["confirmed_stock"] == "14.00"


def test_huggingface_whisper_and_bounded_dialect_adapters(monkeypatch) -> None:
    import httpx
    from app.core.config import get_settings
    from app.modules.assistant.adapters import BoundedLLMAdapter, STTAdapter

    monkeypatch.setenv("HF_TOKEN", "hf_test_token")
    get_settings.cache_clear()

    class _FakeResp:
        def __init__(self, payload: dict):
            self._payload = payload

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return self._payload

    def _fake_hf_post(url: str, **kwargs):
        if "hf-inference/models" in url:
            return _FakeResp({"text": "how many dolo left"})
        if "v1/chat/completions" in url:
            return _FakeResp({
                "choices": [{"message": {"content": '{"intent": "check_stock", "confidence": 0.91}'}}]
            })
        return _FakeResp({"intent": "today_schedule", "confidence": 0.94})

    monkeypatch.setattr(httpx, "post", _fake_hf_post)

    stt = STTAdapter().transcribe(b"RIFF0000", "query.wav", "en")
    assert stt.transcript == "how many dolo left"

    llm_intent = BoundedLLMAdapter().classify_dialect_intent("dolo eshtide heli")
    assert llm_intent == ("check_stock", 0.91)

    # Disallowed/unsafe intent returned by an LLM must be rejected
    monkeypatch.setattr(
        httpx,
        "post",
        lambda url, **kwargs: _FakeResp({
            "choices": [{"message": {"content": '{"intent": "prescribe_drug", "confidence": 0.99}'}}]
        }),
    )
    assert BoundedLLMAdapter().classify_dialect_intent("give medicine") is None

    # Optional self-hosted MuRIL HF Space takes precedence when configured
    monkeypatch.setenv("HF_SPACE_URL", "https://demo-user-nityamed-muril.hf.space")
    get_settings.cache_clear()
    monkeypatch.setattr(httpx, "post", _fake_hf_post)
    assert BoundedLLMAdapter().classify_dialect_intent("ivatt enu tinbeku") == ("today_schedule", 0.94)
    get_settings.cache_clear()
