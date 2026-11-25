"""SQLAlchemy models for users, refresh tokens, and patient profiles."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, SmallInteger, String, Text, Uuid, false
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def utcnow() -> datetime:
    """Return timezone-aware current UTC timestamp."""
    return datetime.now(UTC)


class User(Base):
    """Registered NityaMed user account (patient or system administrator)."""

    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role IN ('patient', 'admin')", name="ck_users_role"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="patient")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_email_verified: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )

    profile: Mapped["PatientProfile | None"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    verification_codes: Mapped[list["EmailVerificationCode"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class EmailVerificationCode(Base):
    """Hashed 6-digit OTP codes for email verification and password reset."""

    __tablename__ = "email_verification_codes"
    __table_args__ = (
        CheckConstraint("purpose IN ('email_verify', 'password_reset')", name="ck_otp_purpose"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    purpose: Mapped[str] = mapped_column(
        String(20), nullable=False, default="email_verify", server_default="email_verify"
    )
    code_hash: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    user: Mapped["User"] = relationship(back_populates="verification_codes")


class RefreshToken(Base):
    """Revocable hashed refresh token for session continuity."""

    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    token_hash: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    user: Mapped["User"] = relationship(back_populates="refresh_tokens")


class PatientProfile(Base):
    """Patient localization, privacy, and scheduling preference settings."""

    __tablename__ = "patient_profiles"
    __table_args__ = (
        CheckConstraint("preferred_lang IN ('en', 'kn', 'hi')", name="ck_profile_lang"),
        CheckConstraint("default_snooze_min BETWEEN 5 AND 60", name="ck_profile_snooze"),
        CheckConstraint("ontime_window_min BETWEEN 10 AND 120", name="ck_profile_ontime"),
        CheckConstraint("expiry_cutoff_hours BETWEEN 1 AND 12", name="ck_profile_expiry"),
        CheckConstraint("refill_alert_days BETWEEN 1 AND 30", name="ck_profile_refill_days"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    preferred_lang: Mapped[str] = mapped_column(String(5), nullable=False, default="en")
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="Asia/Kolkata")
    lockscreen_privacy: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    email_reminders_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )
    default_snooze_min: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=15)
    ontime_window_min: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=30)
    expiry_cutoff_hours: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=4)
    refill_alert_days: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=5)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )

    user: Mapped["User"] = relationship(back_populates="profile")
