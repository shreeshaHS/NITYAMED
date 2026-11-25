"""SQLAlchemy model for the append-only stock transaction ledger."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Numeric, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.modules.auth.models import utcnow

TX_TYPES_SQL = (
    "('INITIAL', 'DOSE_CONFIRMED', 'PURCHASE', "
    "'MANUAL_ADJUSTMENT', 'EXPIRED_DAMAGED_LOST', 'RECONCILIATION', 'CORRECTION_REVERSAL')"
)


class StockTransaction(Base):
    """Append-only inventory transaction ledger for confirmed stock auditing."""

    __tablename__ = "stock_transactions"
    __table_args__ = (
        CheckConstraint(f"tx_type IN {TX_TYPES_SQL}", name="ck_stock_tx_type"),
        CheckConstraint("balance_after >= 0", name="ck_stock_tx_balance_nonneg"),
        Index("idx_stock_tx_med_time", "personal_med_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    personal_med_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("personal_medicines.id", ondelete="CASCADE"), nullable=False
    )
    # Linked once Phase 3 introduces dose_events; nullable for non-dose transactions.
    dose_event_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    tx_type: Mapped[str] = mapped_column(String(30), nullable=False)
    qty_delta: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    balance_after: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    client_event_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, unique=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
