"""otp_attempt_lockout

Revision ID: c4e9b2f10a11
Revises: a7c4d2e9b103
Create Date: 2026-11-26 11:52:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c4e9b2f10a11"
down_revision: Union[str, Sequence[str], None] = "a7c4d2e9b103"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "email_verification_codes",
        sa.Column("failed_attempts", sa.SmallInteger(), server_default=sa.text("0"), nullable=False),
    )
    op.add_column(
        "pending_registrations",
        sa.Column("failed_attempts", sa.SmallInteger(), server_default=sa.text("0"), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("pending_registrations", "failed_attempts")
    op.drop_column("email_verification_codes", "failed_attempts")
