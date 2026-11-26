"""Tests for Phase 2 medicine catalogue, verified education, personal medicines, and admin routes."""

from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password
from app.modules.auth.models import User
from app.modules.inventory.models import StockTransaction
from app.modules.medicines.seed import seed_medicine_catalogue


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


def test_seed_catalogue_is_idempotent_and_searchable(
    client: TestClient, db_session: Session
) -> None:
    first_count = seed_medicine_catalogue(db_session)
    second_count = seed_medicine_catalogue(db_session)
    assert first_count == 16
    assert second_count == 0

    headers = _auth_header(client, "patient1@example.com")

    dolo_search = client.get(
        "/api/v1/catalogue/search?q=Dolo&include_external=false", headers=headers
    )
    assert dolo_search.status_code == 200
    items = dolo_search.json()
    assert len(items) == 1
    assert items[0]["generic_name"] == "Paracetamol (Acetaminophen)"

    # Company-only search when user doesn't remember brand or salt name
    company_search = client.get(
        "/api/v1/catalogue/search?q=Micro%20Labs&include_external=false", headers=headers
    )
    assert company_search.status_code == 200
    assert any(item["brand_name"] == "Dolo 650" for item in company_search.json())

    inhaler_search = client.get("/api/v1/catalogue/search?form=inhaler", headers=headers)
    assert inhaler_search.status_code == 200
    assert inhaler_search.json()[0]["brand_name"] == "Asthalin Inhaler"

    edu_resp = client.get(f"/api/v1/catalogue/{items[0]['id']}/education", headers=headers)
    assert edu_resp.status_code == 200
    edu = edu_resp.json()
    assert edu["source_name"]
    assert edu["verified_at"]
    assert "does not diagnose" in edu["disclaimer"]


def test_personal_medicine_strip_and_loose_stock_separation(
    client: TestClient, db_session: Session
) -> None:
    seed_medicine_catalogue(db_session)
    headers = _auth_header(client, "patient2@example.com")

    catalogue_id = client.get(
        "/api/v1/catalogue/search?q=Dolo&include_external=false", headers=headers
    ).json()[0]["id"]
    event_id = str(uuid4())

    create_resp = client.post(
        "/api/v1/medicines",
        headers=headers,
        json={
            "catalogue_id": catalogue_id,
            "dose_per_intake": "1.00",
            "dose_unit": "tablet",
            "stock_unit": "tablet",
            "initial_packs": 1,
            "initial_loose_units": "4.00",
            "instructions": "After food if fever",
            "client_event_id": event_id,
        },
    )
    assert create_resp.status_code == 201
    med = create_resp.json()
    # 1 strip of 15 + 4 loose = 19 tablets, strictly separate from 1 tablet per intake
    assert med["dose_per_intake"] == "1.00"
    assert med["confirmed_stock"] == "19.00"
    assert med["units_per_pack"] == "15.00"

    # Replaying the same client_event_id does not duplicate medicine or stock
    replay_resp = client.post(
        "/api/v1/medicines",
        headers=headers,
        json={
            "catalogue_id": catalogue_id,
            "dose_per_intake": "1.00",
            "dose_unit": "tablet",
            "stock_unit": "tablet",
            "initial_packs": 1,
            "initial_loose_units": "4.00",
            "client_event_id": event_id,
        },
    )
    assert replay_resp.status_code == 201
    assert replay_resp.json()["id"] == med["id"]

    tx_rows = db_session.scalars(select(StockTransaction)).all()
    assert len(tx_rows) == 1
    assert tx_rows[0].tx_type == "INITIAL"
    assert str(tx_rows[0].balance_after) == "19.00"

    detail = client.get(f"/api/v1/medicines/{med['id']}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["education"] is not None
    assert detail.json()["education_notice"] is None


def test_verified_only_policy_and_ownership_isolation(
    client: TestClient, db_session: Session
) -> None:
    seed_medicine_catalogue(db_session)
    headers_a = _auth_header(client, "owner@example.com")
    headers_b = _auth_header(client, "other@example.com")

    # 1. Direct unauthorized/unverified custom medicine scheduling must be blocked (403)
    blocked_custom = client.post(
        "/api/v1/medicines",
        headers=headers_a,
        json={
            "is_custom": True,
            "display_name": "Unauthorized Compound X",
            "strength": "10 ml",
            "dosage_form": "syrup",
            "dose_per_intake": "5.00",
            "dose_unit": "ml",
            "stock_unit": "ml",
            "initial_loose_units": "100.00",
        },
    )
    assert blocked_custom.status_code == 403
    assert blocked_custom.json()["error"]["code"] == "UNAUTHORIZED_MEDICINE_NOT_ALLOWED"

    # 2. Prohibited/banned substance in verification request must be blocked by policy (403)
    banned_req = client.post(
        "/api/v1/catalogue/requests",
        headers=headers_a,
        json={
            "brand_name": "Sibutramine Slim 15",
            "generic_name": "Sibutramine",
            "strength": "15 mg",
            "dosage_form": "capsule",
        },
    )
    assert banned_req.status_code == 403
    assert banned_req.json()["error"]["code"] == "REGULATORY_POLICY_VIOLATION"

    # 3. Legitimate missing medicine submitted for review stays unverified & unschedulable until Admin approves
    req_resp = client.post(
        "/api/v1/catalogue/requests",
        headers=headers_a,
        json={
            "brand_name": "Triphala Churna Verified Test",
            "generic_name": "Triphala Herbal Blend",
            "strength": "500 mg",
            "dosage_form": "tablet",
            "manufacturer": "Kottakkal",
        },
    )
    assert req_resp.status_code == 201
    pending_cat_id = req_resp.json()["id"]
    assert req_resp.json()["is_verified"] is False
    assert (
        client.get(
            "/api/v1/catalogue/search?q=Triphala&include_external=false", headers=headers_a
        ).json()
        == []
    )
    blocked_unverified = client.post(
        "/api/v1/medicines",
        headers=headers_a,
        json={
            "catalogue_id": pending_cat_id,
            "dose_per_intake": "1.00",
            "dose_unit": "tablet",
            "stock_unit": "tablet",
        },
    )
    assert blocked_unverified.status_code == 403
    assert blocked_unverified.json()["error"]["code"] == "UNVERIFIED_MEDICINE_NOT_ALLOWED"

    # 4. Verified catalogue medicine schedules cleanly and enforces strict user ownership isolation
    cat_id = client.get(
        "/api/v1/catalogue/search?q=Dolo&include_external=false", headers=headers_a
    ).json()[0]["id"]
    med_resp = client.post(
        "/api/v1/medicines",
        headers=headers_a,
        json={
            "catalogue_id": cat_id,
            "dose_per_intake": "1.00",
            "dose_unit": "tablet",
            "stock_unit": "tablet",
            "initial_packs": 1,
        },
    )
    assert med_resp.status_code == 201
    med_id = med_resp.json()["id"]

    # Another user cannot read or update User A's medicine
    assert client.get(f"/api/v1/medicines/{med_id}", headers=headers_b).status_code == 404
    assert (
        client.patch(f"/api/v1/medicines/{med_id}", headers=headers_b, json={"status": "paused"})
        .status_code
        == 404
    )


def test_admin_catalogue_management_and_role_guard(
    client: TestClient, db_session: Session
) -> None:
    patient_headers = _auth_header(client, "regular@example.com")
    assert client.get("/api/v1/admin/health/metrics", headers=patient_headers).status_code == 403

    admin = User(
        email="admin@nityamed.local",
        password_hash=hash_password("AdminSecret123"),
        role="admin",
    )
    db_session.add(admin)
    db_session.commit()
    admin_headers = {"Authorization": f"Bearer {create_access_token(admin.id, admin.role)}"}

    create_cat = client.post(
        "/api/v1/admin/catalogue",
        headers=admin_headers,
        json={
            "brand_name": "Shelcal 500",
            "generic_name": "Calcium + Vitamin D3",
            "strength": "500 mg / 250 IU",
            "dosage_form": "tablet",
            "standard_pack_size": "15",
            "pack_unit": "tablet",
            "manufacturer": "Torrent",
            "education": {
                "category": "Mineral & Vitamin Supplement",
                "common_uses": "Commonly used to support calcium and vitamin D intake.",
                "mechanism": "Provides elemental calcium with vitamin D3 to support absorption.",
                "side_effects": "Mild constipation or bloating.",
                "precautions": "Inform your doctor if you have kidney stones or high blood calcium.",
                "source_name": "National Formulary Reference",
                "verified_at": "2026-11-24",
            },
        },
    )
    assert create_cat.status_code == 201
    cat_id = create_cat.json()["id"]

    # Deprecating hides it from patient search
    deprecate = client.patch(
        f"/api/v1/admin/catalogue/{cat_id}",
        headers=admin_headers,
        json={"is_deprecated": True},
    )
    assert deprecate.status_code == 200
    assert (
        client.get(
            "/api/v1/catalogue/search?q=Shelcal&include_external=false", headers=patient_headers
        ).json()
        == []
    )

    metrics = client.get("/api/v1/admin/health/metrics", headers=admin_headers)
    assert metrics.status_code == 200
    mdata = metrics.json()
    assert "total_users" in mdata
    assert "verified_users" in mdata
    assert "smtp_configured" in mdata
    assert "ml_model_ready" in mdata
    assert "emails" not in mdata

    admin_list = client.get("/api/v1/admin/catalogue?q=Shelcal&status_filter=deprecated", headers=admin_headers)
    assert admin_list.status_code == 200
    assert len(admin_list.json()) == 1
    assert admin_list.json()[0]["is_deprecated"] is True

    sweep = client.post("/api/v1/admin/maintenance/sweep", headers=admin_headers)
    assert sweep.status_code == 200
    assert "expired_doses_marked" in sweep.json()

    smtp_test = client.post(
        "/api/v1/admin/system/test-email",
        headers=admin_headers,
        json={"recipient_email": "admin@example.com"},
    )
    assert smtp_test.status_code == 200
    assert "sent" in smtp_test.json()
