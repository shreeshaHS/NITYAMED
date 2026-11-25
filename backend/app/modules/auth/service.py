"""Business logic for registration, authentication, token rotation, and profile management."""

from datetime import UTC, datetime, timedelta
import secrets

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.modules.auth.email_service import (
    send_password_reset_email,
    send_verification_email,
)
from app.modules.auth.models import EmailVerificationCode, PatientProfile, RefreshToken, User
from app.modules.auth.schemas import (
    AuthMeResponse,
    LoginRequest,
    ProfileResponse,
    ProfileUpdateRequest,
    RegisterRequest,
    TokenResponse,
)

# Precomputed dummy hash mitigates timing-based email enumeration on login.
_DUMMY_HASH = hash_password("nityamed-dummy-timing-guard")


def _as_utc(dt: datetime) -> datetime:
    """Normalize naive datetimes (e.g. from SQLite) to UTC-aware datetimes."""
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


def _issue_session_tokens(db: Session, user: User) -> TokenResponse:
    """Create a fresh access + refresh token pair and store hashed refresh token."""
    settings = get_settings()
    raw_refresh = generate_refresh_token()
    expires_at = datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days)

    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_token(raw_refresh),
            expires_at=expires_at,
        )
    )
    db.commit()

    return TokenResponse(
        access_token=create_access_token(user.id, user.role),
        refresh_token=raw_refresh,
        expires_in=settings.access_token_expire_minutes * 60,
    )


def _create_and_send_otp(
    db: Session, user: User, purpose: str = "email_verify"
) -> tuple[bool, str | None]:
    """Generate a 6-digit OTP for email verification or password reset and send via SMTP."""
    otp = f"{secrets.randbelow(1000000):06d}"
    db.add(
        EmailVerificationCode(
            user_id=user.id,
            purpose=purpose,
            code_hash=hash_token(otp),
            expires_at=datetime.now(UTC) + timedelta(minutes=15),
        )
    )
    db.flush()
    sent = (
        send_password_reset_email(user.email, otp)
        if purpose == "password_reset"
        else send_verification_email(user.email, otp)
    )
    settings = get_settings()
    dev_preview = otp if (not sent and settings.environment == "development") else None
    return sent, dev_preview


def register_patient(db: Session, payload: RegisterRequest) -> TokenResponse:
    """Register a new patient account, initial profile, and send email verification OTP."""
    settings = get_settings()
    normalized_email = payload.email.strip().lower()
    existing = db.scalar(select(User).where(User.email == normalized_email))
    if existing is not None:
        if settings.require_email_verification and not existing.is_email_verified and existing.role == "patient":
            existing.password_hash = hash_password(payload.password)
            if existing.profile is not None:
                existing.profile.display_name = payload.display_name.strip()
                existing.profile.preferred_lang = payload.preferred_lang
            email_sent, dev_otp = _create_and_send_otp(db, existing)
            db.commit()
            return TokenResponse(
                verification_required=True,
                email_sent=email_sent,
                dev_otp_preview=dev_otp,
            )
        raise AppError(409, "EMAIL_ALREADY_EXISTS", "An account with this email already exists")

    user = User(
        email=normalized_email,
        password_hash=hash_password(payload.password),
        role="patient",
        is_email_verified=False,
    )
    db.add(user)
    db.flush()

    profile = PatientProfile(
        user_id=user.id,
        display_name=payload.display_name.strip(),
        preferred_lang=payload.preferred_lang,
    )
    db.add(profile)

    email_sent, dev_otp = _create_and_send_otp(db, user)
    if settings.require_email_verification:
        db.commit()
        return TokenResponse(
            verification_required=True,
            email_sent=email_sent,
            dev_otp_preview=dev_otp,
        )

    token_resp = _issue_session_tokens(db, user)
    token_resp.email_sent = email_sent
    token_resp.dev_otp_preview = dev_otp
    return token_resp


def login_user(db: Session, payload: LoginRequest) -> TokenResponse:
    """Authenticate an active user with email and password."""
    normalized_email = payload.email.strip().lower()
    user = db.scalar(select(User).where(User.email == normalized_email))

    if user is None:
        verify_password(payload.password, _DUMMY_HASH)
        raise AppError(401, "INVALID_CREDENTIALS", "Invalid email or password")

    if not verify_password(payload.password, user.password_hash):
        raise AppError(401, "INVALID_CREDENTIALS", "Invalid email or password")

    if not user.is_active or user.deleted_at is not None:
        raise AppError(403, "ACCOUNT_DISABLED", "Account is disabled or scheduled for deletion")

    if get_settings().require_email_verification and not user.is_email_verified:
        raise AppError(
            403,
            "EMAIL_NOT_VERIFIED",
            "Please verify your email address using the 6-digit code sent to your inbox.",
        )

    return _issue_session_tokens(db, user)


def verify_email_otp(db: Session, email: str, otp_code: str) -> TokenResponse:
    """Verify a 6-digit email OTP and issue session tokens."""
    normalized_email = email.strip().lower()
    user = db.scalar(select(User).where(User.email == normalized_email))
    if user is None:
        raise AppError(404, "USER_NOT_FOUND", "No account found for this email")

    now = datetime.now(UTC)
    code_record = db.scalar(
        select(EmailVerificationCode)
        .where(
            EmailVerificationCode.user_id == user.id,
            EmailVerificationCode.purpose == "email_verify",
            EmailVerificationCode.code_hash == hash_token(otp_code),
            EmailVerificationCode.used_at.is_(None),
        )
        .order_by(EmailVerificationCode.created_at.desc())
    )
    if code_record is None or _as_utc(code_record.expires_at) <= now:
        raise AppError(400, "INVALID_VERIFICATION_CODE", "Verification code is invalid or expired")

    code_record.used_at = now
    user.is_email_verified = True
    return _issue_session_tokens(db, user)


def request_password_reset(db: Session, email: str) -> dict:
    """Issue a password-reset OTP without leaking whether the email exists."""
    normalized_email = email.strip().lower()
    user = db.scalar(select(User).where(User.email == normalized_email))
    dev_otp: str | None = None
    email_sent = False

    if user is not None and user.is_active and user.deleted_at is None:
        email_sent, dev_otp = _create_and_send_otp(db, user, purpose="password_reset")
        db.commit()

    return {
        "message": "If an account exists for that email, a 6-digit reset code has been sent.",
        "email_sent": email_sent,
        "dev_otp_preview": dev_otp,
    }


def reset_password_with_otp(
    db: Session, email: str, otp_code: str, new_password: str
) -> None:
    """Verify a password-reset OTP, update password hash, and revoke active sessions."""
    normalized_email = email.strip().lower()
    user = db.scalar(select(User).where(User.email == normalized_email))
    if user is None:
        raise AppError(400, "INVALID_RESET_CODE", "Reset code is invalid or expired")

    now = datetime.now(UTC)
    code_record = db.scalar(
        select(EmailVerificationCode)
        .where(
            EmailVerificationCode.user_id == user.id,
            EmailVerificationCode.purpose == "password_reset",
            EmailVerificationCode.code_hash == hash_token(otp_code),
            EmailVerificationCode.used_at.is_(None),
        )
        .order_by(EmailVerificationCode.created_at.desc())
    )
    if code_record is None or _as_utc(code_record.expires_at) <= now:
        raise AppError(400, "INVALID_RESET_CODE", "Reset code is invalid or expired")

    code_record.used_at = now
    user.password_hash = hash_password(new_password)
    # Revoke all existing refresh tokens for security after password change.
    active_tokens = db.scalars(
        select(RefreshToken).where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
    ).all()
    for tok in active_tokens:
        tok.revoked_at = now
    db.commit()


def resend_verification_otp(db: Session, email: str) -> dict:
    """Send a fresh 6-digit email verification code."""
    normalized_email = email.strip().lower()
    user = db.scalar(select(User).where(User.email == normalized_email))
    if user is None:
        raise AppError(404, "USER_NOT_FOUND", "No account found for this email")
    if user.is_email_verified:
        return {"already_verified": True, "email_sent": False, "dev_otp_preview": None}

    email_sent, dev_otp = _create_and_send_otp(db, user)
    db.commit()
    return {"already_verified": False, "email_sent": email_sent, "dev_otp_preview": dev_otp}


def build_auth_me(user: User) -> AuthMeResponse:
    """Return authenticated user role and verification state."""
    return AuthMeResponse(
        user_id=user.id,
        email=user.email,
        role=user.role,
        is_email_verified=user.is_email_verified,
    )


def rotate_refresh_token(db: Session, raw_refresh_token: str) -> TokenResponse:
    """Validate and rotate an active refresh token."""
    token_record = db.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == hash_token(raw_refresh_token))
    )
    now = datetime.now(UTC)

    if (
        token_record is None
        or token_record.revoked_at is not None
        or _as_utc(token_record.expires_at) <= now
    ):
        raise AppError(401, "INVALID_REFRESH_TOKEN", "Refresh token is invalid, revoked, or expired")

    user = db.get(User, token_record.user_id)
    if user is None or not user.is_active or user.deleted_at is not None:
        raise AppError(401, "USER_INACTIVE", "User account is inactive")

    token_record.revoked_at = now
    return _issue_session_tokens(db, user)


def revoke_refresh_token(db: Session, user: User, raw_refresh_token: str) -> None:
    """Revoke the provided refresh token owned by the current user."""
    token_record = db.scalar(
        select(RefreshToken).where(
            RefreshToken.token_hash == hash_token(raw_refresh_token),
            RefreshToken.user_id == user.id,
        )
    )
    if token_record is not None and token_record.revoked_at is None:
        token_record.revoked_at = datetime.now(UTC)
        db.commit()


def build_profile_response(user: User) -> ProfileResponse:
    """Assemble the patient profile response for an authenticated user."""
    if user.profile is None:
        raise AppError(404, "PROFILE_NOT_FOUND", "Patient profile not found")

    return ProfileResponse(
        user_id=user.id,
        email=user.email,
        role=user.role,
        is_email_verified=user.is_email_verified,
        display_name=user.profile.display_name,
        preferred_lang=user.profile.preferred_lang,  # type: ignore[arg-type]
        timezone=user.profile.timezone,
        lockscreen_privacy=user.profile.lockscreen_privacy,
        email_reminders_enabled=user.profile.email_reminders_enabled,
        default_snooze_min=user.profile.default_snooze_min,
        ontime_window_min=user.profile.ontime_window_min,
        expiry_cutoff_hours=user.profile.expiry_cutoff_hours,
        refill_alert_days=user.profile.refill_alert_days,
        updated_at=user.profile.updated_at,
    )


def update_patient_profile(
    db: Session, user: User, payload: ProfileUpdateRequest
) -> ProfileResponse:
    """Update allowed patient profile settings."""
    if user.profile is None:
        raise AppError(404, "PROFILE_NOT_FOUND", "Patient profile not found")

    updates = payload.model_dump(exclude_unset=True)
    if "display_name" in updates and updates["display_name"] is not None:
        updates["display_name"] = updates["display_name"].strip()

    for field, value in updates.items():
        setattr(user.profile, field, value)

    db.commit()
    db.refresh(user)
    return build_profile_response(user)


def export_patient_data(db: Session, user: User) -> dict:
    """Export personal account, profile, medicine, dose, and stock ledger data."""
    from app.modules.inventory.models import StockTransaction
    from app.modules.medicines.models import PersonalMedicine
    from app.modules.schedules.models import DoseEvent

    profile_data = build_profile_response(user).model_dump(mode="json")
    meds = db.scalars(select(PersonalMedicine).where(PersonalMedicine.user_id == user.id)).all()
    doses = db.scalars(select(DoseEvent).where(DoseEvent.user_id == user.id)).all()
    txs = db.scalars(select(StockTransaction).where(StockTransaction.user_id == user.id)).all()

    return {
        "exported_at": datetime.now(UTC).isoformat(),
        "account": {
            "user_id": str(user.id),
            "email": user.email,
            "role": user.role,
            "created_at": _as_utc(user.created_at).isoformat(),
        },
        "profile": profile_data,
        "personal_medicines": [
            {
                "id": str(m.id),
                "display_name": m.display_name,
                "strength": m.strength,
                "dosage_form": m.dosage_form,
                "dose_per_intake": str(m.dose_per_intake),
                "confirmed_stock": str(m.confirmed_stock),
                "status": m.status,
            }
            for m in meds
        ],
        "dose_events": [
            {
                "id": str(d.id),
                "personal_med_id": str(d.personal_med_id),
                "scheduled_at": _as_utc(d.scheduled_at).isoformat(),
                "expected_qty": str(d.expected_qty),
                "confirmed_qty": str(d.confirmed_qty),
                "status": d.status,
            }
            for d in doses
        ],
        "stock_transactions": [
            {
                "id": str(t.id),
                "personal_med_id": str(t.personal_med_id),
                "tx_type": t.tx_type,
                "qty_delta": str(t.qty_delta),
                "balance_after": str(t.balance_after),
                "created_at": _as_utc(t.created_at).isoformat(),
            }
            for t in txs
        ],
    }


def delete_patient_account(db: Session, user: User, password: str) -> None:
    """Permanently delete a user account after password confirmation."""
    if not verify_password(password, user.password_hash):
        raise AppError(401, "INVALID_CREDENTIALS", "Password confirmation failed")

    db.delete(user)
    db.commit()
