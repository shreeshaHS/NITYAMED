"""Tests for Phase 3 scheduling, adherence state machine, inventory ledger, and refill prediction."""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.audit.models import AuditLog
from app.modules.inventory.models import StockTransaction
from app.modules.schedules.models import DoseEvent


def _auth_header(client: TestClient, email: str) -> dict[str, str]:
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "StrongPassword123",
            "display_name": "Phase3 Patient",
            "preferred_lang": "en",
        },
    )
    assert resp.status_code == 201
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _create_custom_med(
    client: TestClient,
    headers: dict[str, str],
    name: str,
    initial_loose: str = "10.00",
    units_per_pack: str | None = "10.00",
    low_threshold: str | None = None,
) -> dict:
    payload: dict = {
        "is_custom": True,
        "display_name": name,
        "strength": "500 mg",
        "dosage_form": "tablet",
        "dose_per_intake": "1.00",
        "dose_unit": "tablet",
        "stock_unit": "tablet",
        "initial_loose_units": initial_loose,
    }
    if units_per_pack is not None:
        payload["units_per_pack"] = units_per_pack
    if low_threshold is not None:
        payload["low_stock_threshold"] = low_threshold
    resp = client.post("/api/v1/medicines", headers=headers, json=payload)
    assert resp.status_code == 201
    return resp.json()


def test_schedule_versioning_preserves_history_and_generates_varying_doses(
    client: TestClient,
) -> None:
    headers = _auth_header(client, "sched@example.com")
    med = _create_custom_med(client, headers, "Metformin 500", initial_loose="20.00")
    today = datetime.now(ZoneInfo("Asia/Kolkata")).date()

    v1 = client.post(
        f"/api/v1/medicines/{med['id']}/schedules",
        headers=headers,
        json={
            "frequency_type": "varying_dose",
            "times": [{"time": "08:00", "dose": "1.00"}, {"time": "20:00", "dose": "0.50"}],
            "start_date": today.isoformat(),
            "horizon_days": 7,
        },
    )
    assert v1.status_code == 201
    assert v1.json()["version_number"] == 1

    daily = client.get(f"/api/v1/doses/daily?date={today.isoformat()}", headers=headers)
    assert daily.status_code == 200
    assert len(daily.json()) == 2
    assert daily.json()[0]["expected_qty"] == "1.00"
    assert daily.json()[1]["expected_qty"] == "0.50"

    # Confirm the morning dose before changing schedule version
    morning_id = daily.json()[0]["id"]
    confirm_resp = client.post(
        f"/api/v1/doses/{morning_id}/confirm",
        headers=headers,
        json={
            "actual_qty": "1.00",
            "actioned_at": daily.json()[0]["scheduled_at"],
            "client_event_id": str(uuid4()),
        },
    )
    assert confirm_resp.status_code == 200
    assert confirm_resp.json()["dose"]["status"] == "taken_on_time"

    # Creating v2 supersedes v1 without deleting the confirmed historical dose
    v2 = client.post(
        f"/api/v1/medicines/{med['id']}/schedules",
        headers=headers,
        json={
            "frequency_type": "once_daily",
            "times": [{"time": "09:00", "dose": "1.00"}],
            "start_date": today.isoformat(),
            "horizon_days": 5,
        },
    )
    assert v2.status_code == 201
    assert v2.json()["version_number"] == 2

    versions = client.get(f"/api/v1/medicines/{med['id']}/schedules", headers=headers).json()
    assert len(versions) == 2
    assert versions[0]["effective_to"] is None
    assert versions[1]["effective_to"] is not None


def test_adherence_states_idempotency_and_audited_correction(
    client: TestClient, db_session: Session
) -> None:
    headers = _auth_header(client, "adherence@example.com")
    med = _create_custom_med(client, headers, "Amlong 5", initial_loose="10.00")
    today = datetime.now(ZoneInfo("Asia/Kolkata")).date()

    client.post(
        f"/api/v1/medicines/{med['id']}/schedules",
        headers=headers,
        json={
            "frequency_type": "multiple_daily",
            "times": [{"time": "08:00", "dose": "2.00"}, {"time": "20:00", "dose": "2.00"}],
            "start_date": today.isoformat(),
            "horizon_days": 3,
        },
    )

    doses = client.get(f"/api/v1/doses/daily?date={today.isoformat()}", headers=headers).json()
    first_dose = doses[0]
    second_dose = doses[1]

    # Partial intake deducts exact confirmed qty (1 instead of 2)
    cid = str(uuid4())
    partial = client.post(
        f"/api/v1/doses/{first_dose['id']}/confirm",
        headers=headers,
        json={
            "actual_qty": "1.00",
            "actioned_at": first_dose["scheduled_at"],
            "client_event_id": cid,
        },
    )
    assert partial.status_code == 200
    assert partial.json()["dose"]["status"] == "partially_taken"
    assert partial.json()["updated_confirmed_stock"] == "9.00"

    # Replaying exact same client_event_id does not deduct again
    replay = client.post(
        f"/api/v1/doses/{first_dose['id']}/confirm",
        headers=headers,
        json={
            "actual_qty": "1.00",
            "actioned_at": first_dose["scheduled_at"],
            "client_event_id": cid,
        },
    )
    assert replay.status_code == 200
    assert replay.json()["idempotent_replay"] is True
    assert replay.json()["updated_confirmed_stock"] == "9.00"

    # Confirming same dose with new client_event_id fails with 409
    dup_confirm = client.post(
        f"/api/v1/doses/{first_dose['id']}/confirm",
        headers=headers,
        json={"actual_qty": "1.00", "client_event_id": str(uuid4())},
    )
    assert dup_confirm.status_code == 409

    # Audited accidental correction: partial -> explicitly_skipped restores +1 tablet
    corrected = client.post(
        f"/api/v1/doses/{first_dose['id']}/correct",
        headers=headers,
        json={
            "new_status": "explicitly_skipped",
            "new_qty": "0.00",
            "reason": "Tapped confirm by mistake",
        },
    )
    assert corrected.status_code == 200
    assert corrected.json()["dose"]["status"] == "explicitly_skipped"
    assert corrected.json()["updated_confirmed_stock"] == "10.00"
    assert db_session.query(AuditLog).count() == 1

    # Snooze then skip second dose (0 deduction)
    snoozed = client.post(
        f"/api/v1/doses/{second_dose['id']}/snooze",
        headers=headers,
        json={"minutes": 15},
    )
    assert snoozed.status_code == 200
    assert snoozed.json()["dose"]["status"] == "snoozed"

    skipped = client.post(
        f"/api/v1/doses/{second_dose['id']}/skip",
        headers=headers,
        json={"client_event_id": str(uuid4())},
    )
    assert skipped.status_code == 200
    assert skipped.json()["dose"]["status"] == "explicitly_skipped"
    assert skipped.json()["updated_confirmed_stock"] == "10.00"


def test_overdue_doses_become_expired_unconfirmed_and_zero_stock_confirm_allowed(
    client: TestClient, db_session: Session
) -> None:
    headers = _auth_header(client, "expiry@example.com")
    med = _create_custom_med(client, headers, "Telma 40", initial_loose="0.00")
    yesterday = (datetime.now(UTC) - timedelta(days=1)).date()

    client.post(
        f"/api/v1/medicines/{med['id']}/schedules",
        headers=headers,
        json={
            "frequency_type": "once_daily",
            "times": [{"time": "08:00", "dose": "1.00"}],
            "start_date": yesterday.isoformat(),
            "horizon_days": 3,
        },
    )

    # Backdate first dose in DB so it exceeds the 4-hour cutoff
    past_dose = db_session.scalars(select(DoseEvent).order_by(DoseEvent.scheduled_at.asc())).first()
    assert past_dose is not None
    backdated_utc = datetime.now(UTC) - timedelta(hours=6)
    past_dose.scheduled_at = backdated_utc
    db_session.commit()

    daily = client.get(
        f"/api/v1/doses/daily?date={backdated_utc.astimezone(ZoneInfo('Asia/Kolkata')).date().isoformat()}",
        headers=headers,
    )
    assert daily.status_code == 200
    assert daily.json()[0]["status"] == "expired_unconfirmed"

    # Patient can still log late dose manually even when recorded stock is 0 (reconciliation prompted)
    late_confirm = client.post(
        f"/api/v1/doses/{past_dose.id}/confirm",
        headers=headers,
        json={"actual_qty": "1.00", "actioned_at": datetime.now(UTC).isoformat()},
    )
    assert late_confirm.status_code == 200
    assert late_confirm.json()["dose"]["status"] == "taken_late"
    assert late_confirm.json()["updated_confirmed_stock"] == "0.00"
    assert late_confirm.json()["stock_reconciliation_recommended"] is True


def test_inventory_operations_and_deterministic_refill_predictions(
    client: TestClient,
) -> None:
    headers = _auth_header(client, "inventory@example.com")
    today = datetime.now(ZoneInfo("Asia/Kolkata")).date()

    # 1. Active alternate-day medicine with 6 tablets (3 active doses over 5 days)
    alt_med = _create_custom_med(client, headers, "Warfarin 2", initial_loose="4.00")
    client.post(
        f"/api/v1/medicines/{alt_med['id']}/schedules",
        headers=headers,
        json={
            "frequency_type": "alternate_day",
            "times": [{"time": "18:00", "dose": "1.00"}],
            "interval_days": 2,
            "start_date": today.isoformat(),
            "horizon_days": 14,
        },
    )

    # Purchase 1 strip of 10 -> 14 tablets, then lose 2 -> 12, reconcile to 10 -> -2 delta
    purch = client.post(
        f"/api/v1/inventory/{alt_med['id']}/purchase",
        headers=headers,
        json={"packs": 1, "loose_units": "0.00", "client_event_id": str(uuid4())},
    )
    assert purch.status_code == 200
    assert purch.json()["balance_after"] == "14.00"

    loss = client.post(
        f"/api/v1/inventory/{alt_med['id']}/adjust",
        headers=headers,
        json={"tx_type": "EXPIRED_DAMAGED_LOST", "qty_delta": "-2.00", "notes": "2 tablets damaged"},
    )
    assert loss.status_code == 200
    assert loss.json()["balance_after"] == "12.00"

    reconcile = client.post(
        f"/api/v1/inventory/{alt_med['id']}/reconcile",
        headers=headers,
        json={"actual_counted_stock": "10.00", "notes": "Physical count"},
    )
    assert reconcile.status_code == 200
    assert reconcile.json()["qty_delta"] == "-2.00"
    assert reconcile.json()["balance_after"] == "10.00"

    # Inventory summary separates confirmed stock from projected estimate
    summary = client.get("/api/v1/inventory/summary?horizon_days=7", headers=headers).json()
    assert summary[0]["confirmed_stock"] == "10.00"
    assert summary[0]["is_estimate"] is True
    assert Decimal(summary[0]["projected_stock_balance"]) <= Decimal("10.00")

    # 2. Fixed course (5 days, 1/day, stock 10) -> should NOT alert for refill
    fixed_med = _create_custom_med(client, headers, "Azithral 500", initial_loose="10.00")
    client.post(
        f"/api/v1/medicines/{fixed_med['id']}/schedules",
        headers=headers,
        json={
            "frequency_type": "fixed_course",
            "times": [{"time": "09:00", "dose": "1.00"}],
            "start_date": today.isoformat(),
            "end_date": (today + timedelta(days=4)).isoformat(),
            "horizon_days": 5,
        },
    )

    # 3. PRN medicine -> never assumes daily burn; triggers only on low_stock_threshold
    prn_med = _create_custom_med(
        client, headers, "Asthalin PRN", initial_loose="3.00", units_per_pack=None, low_threshold="5.00"
    )
    client.post(
        f"/api/v1/medicines/{prn_med['id']}/schedules",
        headers=headers,
        json={"frequency_type": "as_needed", "start_date": today.isoformat()},
    )

    preds = {p["display_name"]: p for p in client.get("/api/v1/refills/predictions", headers=headers).json()}
    assert preds["Azithral 500"]["should_alert_now"] is False
    assert preds["Asthalin PRN"]["prediction_mode"] == "as_needed_threshold_only"
    assert preds["Asthalin PRN"]["estimated_remaining_days"] is None
    assert preds["Asthalin PRN"]["should_alert_now"] is True
    assert preds["Warfarin 2"]["prediction_mode"] == "scheduled_deterministic"
    assert preds["Warfarin 2"]["projected_depletion_date"] is not None
