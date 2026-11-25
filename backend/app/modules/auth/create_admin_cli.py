"""CLI script to securely create or promote a System Administrator account."""

import argparse

from sqlalchemy import select

from app.core.database import Base, SessionLocal, engine
from app.core.security import hash_password
import app.modules.auth.models  # noqa: F401
from app.modules.auth.models import User


def main() -> None:
    """Create or promote a verified system administrator account."""
    parser = argparse.ArgumentParser(description="Create a NityaMed System Administrator")
    parser.add_argument("--email", required=True, help="Admin email address")
    parser.add_argument("--password", required=True, help="Admin password (min 8 chars)")
    args = parser.parse_args()

    if len(args.password) < 8:
        raise SystemExit("Password must be at least 8 characters.")

    normalized_email = args.email.strip().lower()
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        existing = db.scalar(select(User).where(User.email == normalized_email))
        if existing is not None:
            existing.role = "admin"
            existing.password_hash = hash_password(args.password)
            existing.is_active = True
            existing.is_email_verified = True
            db.commit()
            print(f"Updated existing user to verified admin: {normalized_email}")
            return

        db.add(
            User(
                email=normalized_email,
                password_hash=hash_password(args.password),
                role="admin",
                is_active=True,
                is_email_verified=True,
            )
        )
        db.commit()
        print(f"Created verified admin account: {normalized_email}")


if __name__ == "__main__":
    main()
