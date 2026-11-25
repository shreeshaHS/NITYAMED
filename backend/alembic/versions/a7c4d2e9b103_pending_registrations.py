"""pending_registrations

Revision ID: a7c4d2e9b103
Revises: f8659b6763f0
Create Date: 2026-11-25 12:10:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a7c4d2e9b103"
down_revision: Union[str, Sequence[str], None] = "f8659b6763f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "pending_registrations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("preferred_lang", sa.String(length=5), nullable=False),
        sa.Column("code_hash", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("preferred_lang IN ('en', 'kn', 'hi')", name="ck_pending_reg_lang"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_pending_registrations_email"), "pending_registrations", ["email"], unique=True
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_pending_registrations_email"), table_name="pending_registrations")
    op.drop_table("pending_registrations")
