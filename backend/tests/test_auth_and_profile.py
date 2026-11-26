"""Tests for Phase 1 authentication, token rotation, profile, and role boundaries."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password
from app.modules.auth.models import PendingRegistration, User


def _register_sample_patient(client: TestClient, email: str = "asha@example.com") -> dict:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "StrongPassword123",
            "display_name": "Asha Devi",
            "preferred_lang": "kn",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_health_check(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "nityamed-api"}


def test_register_duplicate_email_normalized(client: TestClient) -> None:
    tokens = _register_sample_patient(client, "Ramesh@Example.com")
    assert "access_token" in tokens
    assert "refresh_token" in tokens

    duplicate = client.post(
        "/api/v1/auth/register",
        json={
            "email": " ramesh@example.com ",
            "password": "StrongPassword123",
            "display_name": "Ramesh",
            "preferred_lang": "hi",
        },
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "EMAIL_ALREADY_EXISTS"


def test_login_and_invalid_password(client: TestClient) -> None:
    _register_sample_patient(client)

    bad_login = client.post(
        "/api/v1/auth/login",
        json={"email": "asha@example.com", "password": "WrongPassword1"},
    )
    assert bad_login.status_code == 401
    assert bad_login.json()["error"]["code"] == "INVALID_CREDENTIALS"

    good_login = client.post(
        "/api/v1/auth/login",
        json={"email": "asha@example.com", "password": "StrongPassword123"},
    )
    assert good_login.status_code == 200
    assert good_login.json()["token_type"] == "bearer"


def test_refresh_token_rotation_and_logout(client: TestClient) -> None:
    tokens = _register_sample_patient(client)

    refreshed = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert refreshed.status_code == 200
    new_tokens = refreshed.json()
    assert new_tokens["refresh_token"] != tokens["refresh_token"]

    # Reusing the rotated token must fail.
    replay = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert replay.status_code == 401

    # Logging out revokes the active refresh token.
    logout = client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {new_tokens['access_token']}"},
        json={"refresh_token": new_tokens["refresh_token"]},
    )
    assert logout.status_code == 204

    post_logout_refresh = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": new_tokens["refresh_token"]},
    )
    assert post_logout_refresh.status_code == 401


def test_profile_update_export_and_delete(client: TestClient) -> None:
    tokens = _register_sample_patient(client)
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    get_resp = client.get("/api/v1/profile", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["preferred_lang"] == "kn"
    assert get_resp.json()["lockscreen_privacy"] is True

    patch_resp = client.patch(
        "/api/v1/profile",
        headers=headers,
        json={"preferred_lang": "hi", "default_snooze_min": 20, "lockscreen_privacy": False},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["preferred_lang"] == "hi"
    assert patch_resp.json()["default_snooze_min"] == 20
    assert patch_resp.json()["lockscreen_privacy"] is False

    export_resp = client.get("/api/v1/profile/export", headers=headers)
    assert export_resp.status_code == 200
    assert export_resp.json()["account"]["email"] == "asha@example.com"

    wrong_delete = client.request(
        "DELETE",
        "/api/v1/profile",
        headers=headers,
        json={"password": "IncorrectPassword"},
    )
    assert wrong_delete.status_code == 401

    delete_resp = client.request(
        "DELETE",
        "/api/v1/profile",
        headers=headers,
        json={"password": "StrongPassword123"},
    )
    assert delete_resp.status_code == 204

    after_delete = client.get("/api/v1/profile", headers=headers)
    assert after_delete.status_code == 401


def test_role_isolation_blocks_admin_from_patient_profile(
    client: TestClient, db_session: Session
) -> None:
    admin = User(
        email="admin@nityamed.local",
        password_hash=hash_password("AdminSecret123"),
        role="admin",
    )
    db_session.add(admin)
    db_session.commit()

    admin_token = create_access_token(admin.id, admin.role)
    resp = client.get(
        "/api/v1/profile",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "INSUFFICIENT_PERMISSION"

    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {admin_token}"})
    assert me.status_code == 200
    assert me.json()["role"] == "admin"


def test_email_verification_otp_flow_with_enforcement(
    client: TestClient, db_session: Session, monkeypatch
) -> None:
    from app.core.config import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "require_email_verification", True)

    reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": "verify@example.com",
            "password": "StrongPassword123",
            "display_name": "Verify User",
            "preferred_lang": "en",
        },
    )
    assert reg.status_code == 201
    reg_data = reg.json()
    assert reg_data["verification_required"] is True
    assert reg_data["access_token"] is None
    # User MUST NOT exist before OTP verification succeeds
    assert db_session.scalar(select(User).where(User.email == "verify@example.com")) is None
    assert (
        db_session.scalar(
            select(PendingRegistration).where(PendingRegistration.email == "verify@example.com")
        )
        is not None
    )

    # Re-registering an unverified email refreshes OTP cleanly instead of blocking with 409
    reg_retry = client.post(
        "/api/v1/auth/register",
        json={
            "email": "verify@example.com",
            "password": "StrongPassword123",
            "display_name": "Verify User Updated",
            "preferred_lang": "en",
        },
    )
    assert reg_retry.status_code == 201
    otp = reg_retry.json()["dev_otp_preview"]
    assert otp and len(otp) == 6
    assert db_session.scalar(select(User).where(User.email == "verify@example.com")) is None

    # Login before verification must be blocked
    blocked_login = client.post(
        "/api/v1/auth/login",
        json={"email": "verify@example.com", "password": "StrongPassword123"},
    )
    assert blocked_login.status_code == 403
    assert blocked_login.json()["error"]["code"] == "EMAIL_NOT_VERIFIED"

    # Wrong OTP fails and still creates no User row
    bad_verify = client.post(
        "/api/v1/auth/verify-email",
        json={"email": "verify@example.com", "otp_code": "000000" if otp != "000000" else "111111"},
    )
    assert bad_verify.status_code == 400
    assert db_session.scalar(select(User).where(User.email == "verify@example.com")) is None

    # Valid OTP creates the User + Profile and returns tokens
    verified = client.post(
        "/api/v1/auth/verify-email",
        json={"email": "verify@example.com", "otp_code": otp},
    )
    assert verified.status_code == 200
    assert verified.json()["access_token"] is not None
    assert db_session.scalar(select(User).where(User.email == "verify@example.com")) is not None
    assert (
        db_session.scalar(
            select(PendingRegistration).where(PendingRegistration.email == "verify@example.com")
        )
        is None
    )

    me = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {verified.json()['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json()["is_email_verified"] is True


def test_register_aborts_when_email_delivery_fails(
    client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    import httpx
    from app.core.config import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "require_email_verification", True)
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "email_webhook_url", "https://script.google.com/macros/s/demo/exec")

    def _timeout(*args, **kwargs):
        raise OSError("timed out")

    monkeypatch.setattr(httpx, "post", _timeout)

    resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": "failed_delivery@example.com",
            "password": "StrongPassword123",
            "display_name": "Blocked User",
            "preferred_lang": "en",
        },
    )
    assert resp.status_code == 502
    assert resp.json()["error"]["code"] == "EMAIL_DELIVERY_FAILED"
    assert db_session.scalar(select(User).where(User.email == "failed_delivery@example.com")) is None
    assert (
        db_session.scalar(
            select(PendingRegistration).where(
                PendingRegistration.email == "failed_delivery@example.com"
            )
        )
        is None
    )


def test_forgot_and_reset_password_revokes_old_sessions(client: TestClient) -> None:
    tokens = _register_sample_patient(client, "reset@example.com")
    old_refresh = tokens["refresh_token"]

    # Unknown email still returns generic 200 (no user enumeration)
    unknown = client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "nobody@example.com"},
    )
    assert unknown.status_code == 200
    assert unknown.json()["dev_otp_preview"] is None

    forgot = client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "reset@example.com"},
    )
    assert forgot.status_code == 200
    reset_otp = forgot.json()["dev_otp_preview"]
    assert reset_otp and len(reset_otp) == 6

    reset_resp = client.post(
        "/api/v1/auth/reset-password",
        json={
            "email": "reset@example.com",
            "otp_code": reset_otp,
            "new_password": "BrandNewPassword999",
        },
    )
    assert reset_resp.status_code == 204

    # Old refresh token must be revoked after password reset
    assert (
        client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh}).status_code == 401
    )

    # Old password fails, new password succeeds
    assert (
        client.post(
            "/api/v1/auth/login",
            json={"email": "reset@example.com", "password": "StrongPassword123"},
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/api/v1/auth/login",
            json={"email": "reset@example.com", "password": "BrandNewPassword999"},
        ).status_code
        == 200
    )


def test_email_webhook_delivery_and_safe_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    import httpx
    from app.core.config import get_settings
    from app.modules.auth.email_service import send_email_detailed

    monkeypatch.setenv("EMAIL_WEBHOOK_URL", "https://script.google.com/macros/s/demo/exec")
    monkeypatch.setenv("EMAIL_WEBHOOK_SECRET", "topsecret")
    get_settings.cache_clear()

    captured: dict = {}

    class _FakeResp:
        status_code = 200

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {"ok": True}

    def _fake_post(url: str, **kwargs):
        captured["url"] = url
        captured["json"] = kwargs.get("json")
        captured["follow_redirects"] = kwargs.get("follow_redirects")
        return _FakeResp()

    monkeypatch.setattr(httpx, "post", _fake_post)
    sent, detail = send_email_detailed("patient@example.com", "Test Subject", "Hello Body")
    assert sent is True
    assert "HTTPS webhook" in detail
    assert captured["follow_redirects"] is True
    assert captured["json"]["secret"] == "topsecret"
    assert captured["json"]["to"] == "patient@example.com"

    def _boom(*args, **kwargs):
        raise OSError("simulated network failure")

    monkeypatch.setattr(httpx, "post", _boom)
    sent_err, detail_err = send_email_detailed("patient@example.com", "Test", "Body")
    assert sent_err is False
    assert "simulated network failure" in detail_err
    get_settings.cache_clear()


def test_otp_lockout_and_auth_rate_limit(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import get_settings
    from app.core.rate_limit import reset_rate_limiter

    settings = get_settings()
    monkeypatch.setattr(settings, "require_email_verification", True)

    reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": "lockout@example.com",
            "password": "StrongPassword123",
            "display_name": "Lockout Test",
            "preferred_lang": "en",
        },
    )
    assert reg.status_code == 201
    otp = reg.json()["dev_otp_preview"]
    wrong = "000000" if otp != "000000" else "111111"

    # 4 wrong guesses return 400; 5th locks out and invalidates the pending OTP with 429
    for _ in range(4):
        assert (
            client.post(
                "/api/v1/auth/verify-email",
                json={"email": "lockout@example.com", "otp_code": wrong},
            ).status_code
            == 400
        )
    fifth = client.post(
        "/api/v1/auth/verify-email",
        json={"email": "lockout@example.com", "otp_code": wrong},
    )
    assert fifth.status_code == 429
    assert fifth.json()["error"]["code"] == "OTP_ATTEMPTS_EXCEEDED"

    # Verify sliding-window rate limiter on /auth/login
    reset_rate_limiter()
    monkeypatch.setattr(settings, "auth_rate_limit_enabled", True)
    monkeypatch.setattr(settings, "auth_rate_limit_max_requests", 3)
    for _ in range(3):
        r = client.post(
            "/api/v1/auth/login",
            json={"email": "nobody@example.com", "password": "StrongPassword123"},
        )
        assert r.status_code == 401
    throttled = client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@example.com", "password": "StrongPassword123"},
    )
    assert throttled.status_code == 429
    assert throttled.json()["error"]["code"] == "RATE_LIMIT_EXCEEDED"
    assert throttled.headers.get("X-Content-Type-Options") == "nosniff"
    reset_rate_limiter()
