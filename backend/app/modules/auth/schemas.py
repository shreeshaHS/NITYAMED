"""Pydantic schemas for authentication and patient profile endpoints."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

SupportedLang = Literal["en", "kn", "hi"]


class RegisterRequest(BaseModel):
    """Payload to register a new patient account."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=1, max_length=120)
    preferred_lang: SupportedLang = "en"


class LoginRequest(BaseModel):
    """Payload for email + password authentication."""

    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class RefreshRequest(BaseModel):
    """Payload to rotate a refresh token."""

    refresh_token: str = Field(min_length=16, max_length=256)


class TokenResponse(BaseModel):
    """JWT access and opaque refresh token pair with optional email-verification flags."""

    access_token: str | None = None
    refresh_token: str | None = None
    token_type: str = "bearer"
    expires_in: int = 0
    verification_required: bool = False
    email_sent: bool = False
    dev_otp_preview: str | None = None


class AuthMeResponse(BaseModel):
    """Authenticated user identity for both patients and administrators."""

    user_id: UUID
    email: str
    role: str
    is_email_verified: bool


class VerifyEmailRequest(BaseModel):
    """Payload to verify a patient's email using the 6-digit OTP."""

    email: EmailStr
    otp_code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


class ResendVerificationRequest(BaseModel):
    """Payload to resend a fresh 6-digit verification OTP."""

    email: EmailStr


class ForgotPasswordRequest(BaseModel):
    """Payload to initiate a password reset via 6-digit email OTP."""

    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Payload to reset password with a valid 6-digit email OTP."""

    email: EmailStr
    otp_code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")
    new_password: str = Field(min_length=8, max_length=128)


class ProfileResponse(BaseModel):
    """Serialized patient profile and account settings."""

    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    email: EmailStr
    role: str
    is_email_verified: bool
    display_name: str
    preferred_lang: SupportedLang
    timezone: str
    lockscreen_privacy: bool
    email_reminders_enabled: bool
    default_snooze_min: int
    ontime_window_min: int
    expiry_cutoff_hours: int
    refill_alert_days: int
    updated_at: datetime


class ProfileUpdateRequest(BaseModel):
    """Partial update payload for patient preferences."""

    display_name: str | None = Field(default=None, min_length=1, max_length=120)
    preferred_lang: SupportedLang | None = None
    timezone: str | None = Field(default=None, min_length=2, max_length=64)
    lockscreen_privacy: bool | None = None
    email_reminders_enabled: bool | None = None
    default_snooze_min: int | None = Field(default=None, ge=5, le=60)
    ontime_window_min: int | None = Field(default=None, ge=10, le=120)
    expiry_cutoff_hours: int | None = Field(default=None, ge=1, le=12)
    refill_alert_days: int | None = Field(default=None, ge=1, le=30)


class DeleteAccountRequest(BaseModel):
    """Password confirmation required before permanent account deletion."""

    password: str = Field(min_length=1, max_length=128)
