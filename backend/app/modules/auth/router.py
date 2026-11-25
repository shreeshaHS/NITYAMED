"""REST API routes for authentication and patient profile management."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.auth import service
from app.modules.auth.dependencies import get_current_user, require_role
from app.modules.auth.models import User
from app.modules.auth.schemas import (
    AuthMeResponse,
    DeleteAccountRequest,
    ForgotPasswordRequest,
    LoginRequest,
    ProfileResponse,
    ProfileUpdateRequest,
    RefreshRequest,
    RegisterRequest,
    ResendVerificationRequest,
    ResetPasswordRequest,
    TokenResponse,
    VerifyEmailRequest,
)

auth_router = APIRouter(prefix="/auth", tags=["Authentication"])
profile_router = APIRouter(prefix="/profile", tags=["Patient Profile"])


@auth_router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """Register a new patient account."""
    return service.register_patient(db, payload)


@auth_router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """Authenticate with email and password."""
    return service.login_user(db, payload)


@auth_router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """Rotate refresh token and issue a new token pair."""
    return service.rotate_refresh_token(db, payload.refresh_token)


@auth_router.post("/verify-email", response_model=TokenResponse)
def verify_email(payload: VerifyEmailRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """Verify email ownership using a 6-digit OTP and issue tokens."""
    return service.verify_email_otp(db, payload.email, payload.otp_code)


@auth_router.post("/resend-verification")
def resend_verification(
    payload: ResendVerificationRequest, db: Session = Depends(get_db)
) -> dict:
    """Resend a fresh 6-digit verification code."""
    return service.resend_verification_otp(db, payload.email)


@auth_router.post("/forgot-password")
def forgot_password(
    payload: ForgotPasswordRequest, db: Session = Depends(get_db)
) -> dict:
    """Send a 6-digit password-reset code if the email exists."""
    return service.request_password_reset(db, payload.email)


@auth_router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
def reset_password(
    payload: ResetPasswordRequest, db: Session = Depends(get_db)
) -> None:
    """Reset password using a valid 6-digit email OTP."""
    service.reset_password_with_otp(db, payload.email, payload.otp_code, payload.new_password)


@auth_router.get("/me", response_model=AuthMeResponse)
def get_me(current_user: User = Depends(get_current_user)) -> AuthMeResponse:
    """Return current user's role and email verification status."""
    return service.build_auth_me(current_user)


@auth_router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    payload: RefreshRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Revoke the provided refresh token for the current session."""
    service.revoke_refresh_token(db, current_user, payload.refresh_token)


@profile_router.get("", response_model=ProfileResponse)
def get_profile(current_user: User = Depends(require_role("patient"))) -> ProfileResponse:
    """Return the authenticated patient's profile and settings."""
    return service.build_profile_response(current_user)


@profile_router.patch("", response_model=ProfileResponse)
def patch_profile(
    payload: ProfileUpdateRequest,
    current_user: User = Depends(require_role("patient")),
    db: Session = Depends(get_db),
) -> ProfileResponse:
    """Update the authenticated patient's profile and preferences."""
    return service.update_patient_profile(db, current_user, payload)


@profile_router.get("/export")
def export_profile_data(
    current_user: User = Depends(require_role("patient")),
    db: Session = Depends(get_db),
) -> dict:
    """Export the authenticated patient's personal data."""
    return service.export_patient_data(db, current_user)


@profile_router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def delete_profile(
    payload: DeleteAccountRequest,
    current_user: User = Depends(require_role("patient")),
    db: Session = Depends(get_db),
) -> None:
    """Permanently delete the authenticated patient's account."""
    service.delete_patient_account(db, current_user, payload.password)
