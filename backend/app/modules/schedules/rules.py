"""Pure deterministic schedule rule evaluation shared by adherence and refill engines."""

from datetime import date, time
from decimal import Decimal


def parse_hhmm(raw_time: str) -> time:
    """Parse an HH:MM 24-hour string into a time object."""
    hour_str, minute_str = raw_time.strip().split(":")
    return time(hour=int(hour_str), minute=int(minute_str))


def daily_slots_for_date(
    frequency_type: str,
    schedule_rules: dict,
    start_date: date,
    end_date: date | None,
    is_prn: bool,
    target_date: date,
) -> list[tuple[time, Decimal]]:
    """Return ordered (local_time, dose_qty) slots scheduled for target_date."""
    if is_prn or frequency_type == "as_needed":
        return []
    if target_date < start_date:
        return []
    if end_date is not None and target_date > end_date:
        return []

    days_since_start = (target_date - start_date).days
    active_on_day = False

    if frequency_type in {"once_daily", "multiple_daily", "varying_dose", "fixed_course"}:
        active_on_day = True
    elif frequency_type == "alternate_day":
        interval = max(1, int(schedule_rules.get("interval_days", 2)))
        active_on_day = days_since_start % interval == 0
    elif frequency_type == "weekly":
        active_on_day = days_since_start % 7 == 0
    elif frequency_type == "selected_weekdays":
        weekdays = {int(w) for w in schedule_rules.get("weekdays", [])}
        active_on_day = target_date.weekday() in weekdays

    if not active_on_day:
        return []

    slots: list[tuple[time, Decimal]] = []
    for entry in schedule_rules.get("times", []):
        slot_time = parse_hhmm(str(entry["time"]))
        slot_dose = Decimal(str(entry["dose"]))
        slots.append((slot_time, slot_dose))

    slots.sort(key=lambda item: item[0])
    return slots
