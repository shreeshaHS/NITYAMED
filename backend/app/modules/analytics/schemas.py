"""Pydantic schemas for adherence analytics and irregular pattern summaries."""

from uuid import UUID

from pydantic import BaseModel


class MedicineAdherenceBreakdown(BaseModel):
    """Per-medicine adherence metrics over the requested time window."""

    personal_med_id: UUID
    display_name: str
    closed_scheduled_count: int
    taken_on_time: int
    taken_late: int
    partially_taken: int
    explicitly_skipped: int
    expired_unconfirmed: int
    confirmed_adherence_rate: float | None
    unconfirmed_rate: float | None


class AdherenceReportResponse(BaseModel):
    """Patient adherence report with transparent metric definitions and non-clinical notes."""

    window_days: int
    closed_scheduled_count: int
    upcoming_pending_count: int
    taken_on_time: int
    taken_late: int
    partially_taken: int
    explicitly_skipped: int
    expired_unconfirmed: int
    confirmed_adherence_rate: float | None
    on_time_rate: float | None
    unconfirmed_rate: float | None
    formula_notes: dict[str, str]
    per_medicine: list[MedicineAdherenceBreakdown]
    irregular_patterns: list[str]
    disclaimer: str = (
        "Adherence analytics summarize your recorded routine only and do not provide clinical diagnoses or treatment advice."
    )
