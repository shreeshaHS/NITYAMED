"""Tests for Phase 4 offline batch sync, deduplicated notifications, cron sweep, and analytics."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.modules.schedules.models import DoseEvent


def _auth_header(client: TestClient, email: str) -> dict[str, str]:
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "StrongPassword123",
            "display_name": "Phase4 Patient",
            "preferred_lang": "en",
        },
    )
    assert resp.status_code == 201
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def test_offline_batch_sync_idempotency_and_bootstrap(client: TestClient) -> None:
    headers = _auth_header(client, "sync@example.com")
    today = datetime.now(ZoneInfo("Asia/Kolkata")).date()

    med = client.post(
        "/api/v1/medicines",
        headers=headers,
        json={
            "is_custom": True,
            "display_name": "Glycomet 500",
            "strength": "500 mg",
            "dosage_form": "tablet",
            "dose_per_intake": "1.00",
            "dose_unit": "tablet",
            "stock_unit": "tablet",
            "units_per_pack": "10.00",
            "initial_loose_units": "5.00",
        },
    ).json()

    client.post(
        f"/api/v1/medicines/{med['id']}/schedules",
        headers=headers,
        json={
            "frequency_type": "once_daily",
            "times": [{"time": "08:00", "dose": "1.00"}],
            "start_date": today.isoformat(),
            "horizon_days": 5,
        },
    )

    bootstrap = client.get("/api/v1/sync/bootstrap", headers=headers)
    assert bootstrap.status_code == 200
    boot_data = bootstrap.json()
    assert len(boot_data["medicines"]) == 1
    assert len(boot_data["active_schedules"]) == 1
    assert len(boot_data["dose_events"]) == 5

    dose_id = boot_data["dose_events"][0]["id"]
    dose_time = boot_data["dose_events"][0]["scheduled_at"]
    cid_dose = str(uuid4())
    cid_purch = str(uuid4())

    batch_payload = {
        "events": [
            {
                "client_event_id": cid_dose,
                "event_type": "DOSE_CONFIRM",
                "dose_event_id": dose_id,
                "payload": {"actual_qty": "1.00", "actioned_at": dose_time},
            },
            {
                "client_event_id": cid_purch,
                "event_type": "STOCK_PURCHASE",
                "personal_med_id": med["id"],
                "payload": {"packs": 1, "loose_units": "0.00"},
            },
            {
                "client_event_id": str(uuid4()),
                "event_type": "DOSE_CONFIRM",
                "dose_event_id": str(uuid4()),
                "payload": {"actual_qty": "1.00"},
            },
        ]
    }

    sync_resp = client.post("/api/v1/sync/events", headers=headers, json=batch_payload)
    assert sync_resp.status_code == 200
    res = sync_resp.json()
    assert res["applied_count"] == 2
    assert res["rejected_count"] == 1
    # 5 - 1 (dose) + 10 (1 pack) = 14
    assert res["results"][1]["updated_confirmed_stock"] == "14.00"

    # Replaying valid items is ignored idempotently
    replay_resp = client.post(
        "/api/v1/sync/events",
        headers=headers,
        json={"events": batch_payload["events"][:2]},
    )
    assert replay_resp.status_code == 200
    assert replay_resp.json()["duplicate_count"] == 2
    assert replay_resp.json()["applied_count"] == 0


def test_notifications_privacy_dedup_and_cron_sweep(
    client: TestClient, db_session: Session
) -> None:
    headers = _auth_header(client, "notif@example.com")
    today = datetime.now(ZoneInfo("Asia/Kolkata")).date()

    med = client.post(
        "/api/v1/medicines",
        headers=headers,
        json={
            "is_custom": True,
            "display_name": "SecretMed 10",
            "strength": "10 mg",
            "dosage_form": "tablet",
            "dose_per_intake": "1.00",
            "dose_unit": "tablet",
            "stock_unit": "tablet",
            "initial_loose_units": "2.00",
        },
    ).json()

    client.post(
        f"/api/v1/medicines/{med['id']}/schedules",
        headers=headers,
        json={
            "frequency_type": "once_daily",
            "times": [{"time": "08:00", "dose": "1.00"}],
            "start_date": today.isoformat(),
            "horizon_days": 5,
        },
    )

    # Backdate one dose so sweep marks it expired_unconfirmed
    past_dose = db_session.scalars(select(DoseEvent).order_by(DoseEvent.scheduled_at.asc())).first()
    assert past_dose is not None
    past_dose.scheduled_at = datetime.now(UTC) - timedelta(hours=8)
    db_session.commit()

    # Unauthorized cron secret rejected
    assert client.post("/api/v1/internal/jobs/sweep").status_code == 403

    # Valid cron secret executes sweep
    cron_secret = get_settings().cron_secret
    sweep = client.post("/api/v1/internal/jobs/sweep", headers={"X-Cron-Secret": cron_secret})
    assert sweep.status_code == 200
    assert sweep.json()["expired_doses_marked"] == 1
    assert sweep.json()["refill_alerts_created"] == 1

    # Second sweep creates 0 duplicate refill alerts
    sweep2 = client.post("/api/v1/internal/jobs/sweep", headers={"X-Cron-Secret": cron_secret})
    assert sweep2.status_code == 200
    assert sweep2.json()["refill_alerts_created"] == 0

    history = client.get("/api/v1/notifications/history", headers=headers).json()
    assert len(history) == 1
    # Lockscreen privacy hides medicine name by default
    assert "SecretMed" not in history[0]["payload_preview"]

    updated = client.patch(
        f"/api/v1/notifications/{history[0]['id']}/status",
        headers=headers,
        json={"delivery_status": "delivered"},
    )
    assert updated.status_code == 200
    assert updated.json()["delivery_status"] == "delivered"
    assert updated.json()["sent_at"] is not None


def test_opt_in_email_dose_and_refill_backup_alerts(
    client: TestClient, db_session: Session, monkeypatch
) -> None:
    from app.modules.notifications import service as notif_service

    sent_emails: list[tuple[str, str, str]] = []

    def fake_send_reminder(to_email: str, subject: str, preview_text: str) -> bool:
        sent_emails.append((to_email, subject, preview_text))
        return True

    monkeypatch.setattr(notif_service, "send_reminder_email", fake_send_reminder)

    headers = _auth_header(client, "mailalert@example.com")
    client.patch("/api/v1/profile", headers=headers, json={"email_reminders_enabled": True})

    today = datetime.now(ZoneInfo("Asia/Kolkata")).date()
    med = client.post(
        "/api/v1/medicines",
        headers=headers,
        json={
            "is_custom": True,
            "display_name": "ConfidentialDrug 500",
            "strength": "500 mg",
            "dosage_form": "tablet",
            "dose_per_intake": "1.00",
            "dose_unit": "tablet",
            "stock_unit": "tablet",
            "initial_loose_units": "1.00",
        },
    ).json()

    client.post(
        f"/api/v1/medicines/{med['id']}/schedules",
        headers=headers,
        json={
            "frequency_type": "once_daily",
            "times": [{"time": "08:00", "dose": "1.00"}],
            "start_date": today.isoformat(),
            "horizon_days": 3,
        },
    )

    due_dose = db_session.scalars(select(DoseEvent).order_by(DoseEvent.scheduled_at.asc())).first()
    assert due_dose is not None
    due_dose.scheduled_at = datetime.now(UTC) + timedelta(minutes=20)
    db_session.commit()

    sweep = client.post(
        "/api/v1/internal/jobs/sweep",
        headers={"X-Cron-Secret": get_settings().cron_secret},
    )
    assert sweep.status_code == 200
    assert sweep.json()["refill_alerts_created"] == 2
    assert len(sent_emails) == 2
    # Sensitive drug name must NEVER appear in email text
    assert all("ConfidentialDrug" not in body for _, _, body in sent_emails)

    # Re-running sweep sends zero duplicate emails
    client.post(
        "/api/v1/internal/jobs/sweep",
        headers={"X-Cron-Secret": get_settings().cron_secret},
    )
    assert len(sent_emails) == 2


def test_adherence_analytics_metrics_and_pattern_detection(
    client: TestClient, db_session: Session
) -> None:
    headers = _auth_header(client, "analytics@example.com")
    today = datetime.now(ZoneInfo("Asia/Kolkata")).date()

    med = client.post(
        "/api/v1/medicines",
        headers=headers,
        json={
            "is_custom": True,
            "display_name": "Atorva 10",
            "strength": "10 mg",
            "dosage_form": "tablet",
            "dose_per_intake": "1.00",
            "dose_unit": "tablet",
            "stock_unit": "tablet",
            "initial_loose_units": "15.00",
        },
    ).json()

    client.post(
        f"/api/v1/medicines/{med['id']}/schedules",
        headers=headers,
        json={
            "frequency_type": "once_daily",
            "times": [{"time": "20:00", "dose": "1.00"}],
            "start_date": today.isoformat(),
            "horizon_days": 8,
        },
    )

    events = db_session.scalars(select(DoseEvent).order_by(DoseEvent.scheduled_at.asc())).all()
    assert len(events) >= 6

    # Shift first 5 events to past days so analytics evaluates closed history cleanly:
    # 3 taken_late in evening, 1 explicitly_skipped, 1 overdue -> expired_unconfirmed
    base_evening_utc = datetime.now(UTC) - timedelta(days=5)
    for idx in range(5):
        events[idx].scheduled_at = (base_evening_utc + timedelta(days=idx)).replace(
            hour=14, minute=30, second=0, microsecond=0  # 20:00 IST
        )
    db_session.commit()

    for idx in range(3):
        late_time = events[idx].scheduled_at + timedelta(hours=2)
        client.post(
            f"/api/v1/doses/{events[idx].id}/confirm",
            headers=headers,
            json={"actual_qty": "1.00", "actioned_at": late_time.isoformat()},
        )

    client.post(f"/api/v1/doses/{events[3].id}/skip", headers=headers, json={})
    # events[4] remains untouched past cutoff -> auto-marked expired_unconfirmed

    report = client.get("/api/v1/analytics/adherence?days=30", headers=headers)
    assert report.status_code == 200
    data = report.json()
    assert data["closed_scheduled_count"] == 5
    assert data["taken_late"] == 3
    assert data["explicitly_skipped"] == 1
    assert data["expired_unconfirmed"] == 1
    assert data["confirmed_adherence_rate"] == 60.0
    assert data["unconfirmed_rate"] == 20.0
    assert any("evening window" in p for p in data["irregular_patterns"])
    assert "do not provide clinical diagnoses" in data["disclaimer"]
