"""Tests for live external openFDA/RxNorm client, caching, offline safety, and bulk importer."""

from datetime import date
from pathlib import Path

from fastapi.testclient import TestClient
import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.medicines import external_api, service
from app.modules.medicines.importer import import_from_file
from app.modules.medicines.models import MedicineCatalogue, MedicineEducation


def _auth_header(client: TestClient, email: str) -> dict[str, str]:
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "StrongPassword123",
            "display_name": "Test Patient",
            "preferred_lang": "en",
        },
    )
    assert resp.status_code == 201
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def test_openfda_parsing_inn_alias_and_rxnorm_fallback() -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        if "approximateTerm.json" in str(request.url):
            return httpx.Response(
                200,
                json={"approximateGroup": {"candidate": [{"name": "ibuprofen"}]}},
            )
        search_param = request.url.params.get("search", "")
        if "acetaminophen" in search_param or "ibuprofen" in search_param:
            return httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "set_id": "abc-123",
                            "effective_time": "20260515",
                            "openfda": {
                                "brand_name": ["Advil"],
                                "generic_name": ["IBUPROFEN"],
                                "substance_name": ["IBUPROFEN"],
                                "manufacturer_name": ["Haleon"],
                                "pharm_class_epc": ["Nonsteroidal Anti-inflammatory Drug"],
                                "route": ["ORAL"],
                                "product_type": ["HUMAN OTC DRUG"],
                            },
                            "active_ingredient": ["Ibuprofen 200 mg"],
                            "dosage_and_administration": ["Take 1 tablet every 4 to 6 hours."],
                            "indications_and_usage": ["Temporarily relieves minor aches and pains."],
                            "mechanism_of_action": ["Inhibits cyclooxygenase enzyme activity."],
                            "adverse_reactions": ["Mild stomach upset or heartburn."],
                            "warnings": ["Do not exceed 6 tablets in 24 hours."],
                        }
                    ]
                },
            )
        return httpx.Response(404, json={"error": {"code": "NOT_FOUND"}})

    mock_http = httpx.Client(transport=httpx.MockTransport(handler))

    # Paracetamol translates to acetaminophen automatically
    paracetamol_hits = external_api.fetch_external_medicines("paracetamol", client=mock_http)
    assert len(paracetamol_hits) == 1
    assert paracetamol_hits[0].dosage_form == "tablet"
    assert paracetamol_hits[0].source_name == "U.S. FDA / openFDA Drug Label"
    assert paracetamol_hits[0].verified_at == date(2026, 5, 15)

    # Misspelling triggers RxNorm approximateTerm fallback -> ibuprofen
    typo_hits = external_api.fetch_external_medicines("ibuprofn", client=mock_http)
    assert len(typo_hits) == 1
    assert any("approximateTerm.json" in url for url in calls)


def test_live_search_caches_into_local_catalogue_and_handles_offline(
    client: TestClient, db_session: Session, monkeypatch
) -> None:
    headers = _auth_header(client, "live@example.com")

    sample_record = external_api.ExternalMedicineRecord(
        brand_name="Glucophage",
        generic_name="Metformin Hydrochloride",
        active_ingredients="METFORMIN HYDROCHLORIDE",
        strength="500 mg",
        dosage_form="tablet",
        manufacturer="Merck",
        category="Biguanide",
        common_uses="Supports glycemic control in type 2 diabetes.",
        mechanism="Decreases hepatic glucose production.",
        side_effects="Mild GI upset.",
        precautions="Take with meals.",
        source_name="U.S. FDA / openFDA Drug Label",
        source_url="https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=xyz",
        verified_at=date(2026, 11, 1),
    )

    monkeypatch.setattr(service, "fetch_external_medicines", lambda q, limit=5: [sample_record])

    resp = client.get("/api/v1/catalogue/search?q=metformin", headers=headers)
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1
    assert items[0]["brand_name"] == "Glucophage"

    # Cached in DB so second search (even offline) returns it directly
    assert db_session.query(MedicineCatalogue).count() == 1
    assert db_session.query(MedicineEducation).count() == 1

    monkeypatch.setattr(service, "fetch_external_medicines", lambda q, limit=5: [])
    offline_resp = client.get(
        "/api/v1/catalogue/search?q=metformin&include_external=false", headers=headers
    )
    assert offline_resp.status_code == 200
    assert len(offline_resp.json()) == 1


def test_network_error_returns_empty_safely() -> None:
    def failing_handler(_: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("Offline simulated")

    mock_http = httpx.Client(transport=httpx.MockTransport(failing_handler))
    assert external_api.fetch_external_medicines("ibuprofen", client=mock_http) == []


def test_bulk_indian_dataset_csv_and_json_importer(
    db_session: Session, tmp_path: Path
) -> None:
    csv_file = tmp_path / "indian_drugs.csv"
    csv_file.write_text(
        "brand_name,generic_name,strength,dosage_form,standard_pack_size,pack_unit,manufacturer\n"
        "Crocin Advance,Paracetamol,500 mg,Tab,15,tablet,Haleon\n"
        "Augmentin 625 Duo,Amoxycillin + Clavulanic Acid,625 mg,Tablets,10,tablet,GSK\n"
        ",Missing Brand,10 mg,tablet,10,tablet,Unknown\n",
        encoding="utf-8",
    )

    summary_csv = import_from_file(db_session, csv_file)
    assert summary_csv.inserted == 2
    assert summary_csv.skipped_invalid == 1
    assert summary_csv.skipped_duplicates == 0

    # Re-importing the same CSV skips duplicates cleanly
    summary_repeat = import_from_file(db_session, csv_file)
    assert summary_repeat.inserted == 0
    assert summary_repeat.skipped_duplicates == 2

    rows = db_session.scalars(select(MedicineCatalogue)).all()
    assert all(row.dosage_form == "tablet" for row in rows)


def test_kaggle_indian_csv_fempro_and_auto_generic_enrichment(
    client: TestClient, db_session: Session, tmp_path: Path, monkeypatch
) -> None:
    kaggle_csv = tmp_path / "kaggle_indian_sample.csv"
    kaggle_csv.write_text(
        "name,short_composition1,short_composition2,pack_size_label,manufacturer_name,type,Is_discontinued\n"
        "Fempro Tablet,Letrozole (2.5mg),,strip of 10 tablets,Cipla Ltd,allopathy,FALSE\n"
        "Old Discontinued Tab,Paracetamol (500mg),,strip of 10 tablets,Old Co,allopathy,TRUE\n",
        encoding="utf-8",
    )

    summary = import_from_file(db_session, kaggle_csv)
    assert summary.inserted == 1
    assert summary.skipped_invalid == 1

    fempro = db_session.scalar(
        select(MedicineCatalogue).where(MedicineCatalogue.brand_name == "Fempro Tablet")
    )
    assert fempro is not None
    assert fempro.generic_name == "Letrozole"
    assert fempro.strength == "2.5mg"
    assert fempro.dosage_form == "tablet"
    assert str(fempro.standard_pack_size) == "10.00"
    assert fempro.pack_unit == "tablet"
    assert fempro.manufacturer == "Cipla Ltd"

    # Imported row initially has no education; viewing triggers generic-salt lookup ('Letrozole')
    letrozole_edu = external_api.ExternalMedicineRecord(
        brand_name="Letrozole",
        generic_name="LETROZOLE",
        active_ingredients="LETROZOLE",
        strength="2.5 mg",
        dosage_form="tablet",
        manufacturer="FDA Label",
        category="Aromatase Inhibitor",
        common_uses="Used in hormone-receptor-positive breast cancer management.",
        mechanism="Inhibits aromatase enzyme to lower estrogen levels.",
        side_effects="Hot flashes, joint pain, fatigue.",
        precautions="Use strictly as prescribed.",
        source_name="U.S. FDA / openFDA Drug Label",
        source_url="https://dailymed.nlm.nih.gov/",
        verified_at=date(2026, 6, 1),
    )
    called_terms: list[str] = []

    def fake_fetch(term: str, limit: int = 5):
        called_terms.append(term)
        return [letrozole_edu] if term.lower() == "letrozole" else []

    monkeypatch.setattr(service, "fetch_external_medicines", fake_fetch)

    headers = _auth_header(client, "fempro@example.com")
    edu_resp = client.get(f"/api/v1/catalogue/{fempro.id}/education", headers=headers)
    assert edu_resp.status_code == 200
    assert edu_resp.json()["category"] == "Aromatase Inhibitor"
    assert called_terms == ["Letrozole"]

    # Second call uses cached DB row without hitting external API again
    edu_cached = client.get(f"/api/v1/catalogue/{fempro.id}/education", headers=headers)
    assert edu_cached.status_code == 200
    assert len(called_terms) == 1
