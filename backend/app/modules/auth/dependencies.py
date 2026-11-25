"""FastAPI authentication and role-based authorization dependencies."""

from collections.abc import Callable
from uuid import UUID

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import AppError
from app.core.security import decode_access_token
from app.modules.auth.models import User

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Validate Bearer JWT and return the active authenticated user."""
    if credentials is None or not credentials.credentials:
        raise AppError(401, "AUTH_REQUIRED", "Authentication credentials were not provided")

    try:
        payload = decode_access_token(credentials.credentials)
        user_id = UUID(payload["sub"])
    except (jwt.PyJWTError, ValueError) as exc:
        raise AppError(401, "INVALID_TOKEN", "Access token is invalid or expired") from exc

    user = db.get(User, user_id)
    if user is None or not user.is_active or user.deleted_at is not None:
        raise AppError(401, "USER_INACTIVE", "User account is inactive or unavailable")

    return user


def require_role(*allowed_roles: str) -> Callable[[User], User]:
    """Return a FastAPI dependency restricting access to specified user roles."""

    def _role_guard(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise AppError(403, "INSUFFICIENT_PERMISSION", "You do not have permission for this action")
        return current_user

    return _role_guard
