"""Password hashing, JWT access tokens, and opaque refresh token helpers."""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from pwdlib import PasswordHash

from app.core.config import get_settings

password_hasher = PasswordHash.recommended()


def hash_password(plain_password: str) -> str:
    """Hash a plaintext password using Argon2id."""
    return password_hasher.hash(plain_password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Verify a plaintext password against its stored Argon2id hash."""
    return password_hasher.verify(plain_password, password_hash)


def create_access_token(user_id: UUID, role: str) -> str:
    """Issue a short-lived signed JWT access token."""
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "role": role,
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    """Decode and validate a JWT access token."""
    settings = get_settings()
    payload = jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
    )
    if payload.get("type") != "access" or "sub" not in payload:
        raise jwt.InvalidTokenError("Invalid access token claims")
    return payload


def generate_refresh_token() -> str:
    """Generate a cryptographically random opaque refresh token."""
    return secrets.token_urlsafe(48)


def hash_token(raw_token: str) -> str:
    """Hash an opaque refresh token with SHA-256 before database persistence."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
