"""OpenAI/Gemini-compatible function schemas and grounded executors for the NityaMed AI agent."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
import uuid
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.assistant.nlp import match_user_medicines, normalize_text
from app.modules.auth.models import PatientProfile, User
from app.modules.medicines.models import MedicineCatalogue, PersonalMedicine
from app.modules.medicines.service import _ensure_catalogue_education, search_catalogue
from app.modules.refill.service import get_refill_predictions
from app.modules.schedules import service as schedules_service
from app.modules.schedules.models import DoseEvent
from app.modules.schedules.schemas import DoseSnoozeRequest

ASSISTANT_TOOLS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "get_today_schedule",
            "description": "Get all scheduled doses for today with statuses and times.",
            "parameters": {
                "type": "object",
                "properties": {
                    "time_window": {
                        "type": "string",
                        "enum": ["morning", "afternoon", "evening", "night"],
                        "description": "Optional daypart filter.",
                    }
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_user_medicines",
            "description": "Get all active user medicines with strength, dose per intake, and confirmed stock.",
            "parameters": {
                "type": "object",
                "properties": {
                    "include_paused": {"type": "boolean", "default": False}
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_refill_predictions",
            "description": "Get estimated remaining days and depletion dates for medicines.",
            "parameters": {
                "type": "object",
                "properties": {
                    "medicine_name": {"type": "string"}
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_next_dose",
            "description": "Get the user's next upcoming scheduled or snoozed dose.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_adherence_status",
            "description": "Check whether today's scheduled doses were already taken, pending, snoozed, or skipped.",
            "parameters": {
                "type": "object",
                "properties": {
                    "time_window": {
                        "type": "string",
                        "enum": ["morning", "afternoon", "evening", "night"],
                    }
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_medicine_catalogue",
            "description": "Search NityaMed's verified Indian medicine catalogue by brand/salt name and/or pharma company/manufacturer.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "manufacturer": {"type": "string"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_medicine_education",
            "description": "Get verified clinical uses, mechanism, side effects, and precautions for an active or verified catalogue medicine.",
            "parameters": {
                "type": "object",
                "properties": {
                    "medicine_name": {"type": "string"}
                },
                "required": ["medicine_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "stage_confirm_dose",
            "description": "Stage a pending dose confirmation for explicit user approval (does not commit until user confirms).",
            "parameters": {
                "type": "object",
                "properties": {
                    "medicine_name": {"type": "string"},
                    "time_window": {
                        "type": "string",
                        "enum": ["morning", "afternoon", "evening", "night"],
                    },
                    "actual_quantity": {"type": "number"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "stage_stock_purchase",
            "description": "Stage a medicine purchase stock update (packs or loose units) for explicit user approval.",
            "parameters": {
                "type": "object",
                "properties": {
                    "medicine_name": {"type": "string"},
                    "packs": {"type": "integer", "default": 0},
                    "loose_units": {"type": "number", "default": 0},
                },
                "required": ["medicine_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "stage_skip_dose",
            "description": "Stage marking a pending dose today as explicitly skipped for user confirmation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "medicine_name": {"type": "string"},
                    "time_window": {
                        "type": "string",
                        "enum": ["morning", "afternoon", "evening", "night"],
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "snooze_dose_reminder",
            "description": "Snooze an active pending/snoozed dose reminder by N minutes (5 to 120, default 15).",
            "parameters": {
                "type": "object",
                "properties": {
                    "medicine_name": {"type": "string"},
                    "minutes": {"type": "integer", "default": 15},
                },
            },
        },
    },
]


def to_gemini_function_declarations() -> list[dict]:
    """Convert OpenAI-style tool definitions into Gemini `functionDeclarations` format."""
    decls = []
    for item in ASSISTANT_TOOLS:
        fn = item["function"]
        params = dict(fn.get("parameters") or {"type": "object", "properties": {}})
        decl: dict = {
            "name": fn["name"],
            "description": fn["description"],
        }
        if params.get("properties"):
            decl["parameters"] = params
        decls.append(decl)
    return decls


def _as_utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


def _time_bucket(hour: int) -> str:
    if 5 <= hour < 12:
        return "morning"
    if 12 <= hour < 17:
        return "afternoon"
    if 17 <= hour < 22:
        return "evening"
    return "night"


@dataclass
class ToolExecutionContext:
    """Mutable per-turn execution context holding user ownership, staged writes, and trace."""

    db: Session
    user: User
    profile: PatientProfile | None
    tz: ZoneInfo
    active_meds: list[PersonalMedicine]
    staged_actions: list[dict] = field(default_factory=list)
    called_tools: list[str] = field(default_factory=list)
    med_id_context: uuid.UUID | None = None


def _match_owned(name_hint: str | None, active_meds: list[PersonalMedicine]) -> list[PersonalMedicine]:
    if not name_hint:
        return []
    return match_user_medicines(normalize_text(name_hint), active_meds)


def execute_assistant_tool(name: str, args: dict, ctx: ToolExecutionContext) -> dict:
    """Execute a single validated tool call strictly scoped to ctx.user."""
    ctx.called_tools.append(name)
    args = args or {}

    if name in {"get_today_schedule", "get_adherence_status"}:
        today_local = datetime.now(UTC).astimezone(ctx.tz).date()
        daily = schedules_service.get_daily_schedule(ctx.db, ctx.user, target_date=today_local)
        window = args.get("time_window")
        if window in {"morning", "afternoon", "evening", "night"}:
            daily = [d for d in daily if _time_bucket(d.scheduled_at.astimezone(ctx.tz).hour) == window]
        return {
            "date": today_local.isoformat(),
            "doses": [
                {
                    "dose_id": str(d.id),
                    "medicine": d.display_name,
                    "expected_qty": str(d.expected_qty),
                    "unit": d.dose_unit,
                    "time": d.scheduled_at.astimezone(ctx.tz).strftime("%H:%M"),
                    "bucket": _time_bucket(d.scheduled_at.astimezone(ctx.tz).hour),
                    "status": d.status,
                }
                for d in daily
            ],
        }

    if name == "get_user_medicines":
        meds = ctx.active_meds
        if args.get("include_paused"):
            meds = list(
                ctx.db.scalars(
                    select(PersonalMedicine).where(
                        PersonalMedicine.user_id == ctx.user.id,
                        PersonalMedicine.status != "archived",
                    )
                ).all()
            )
        return {
            "medicines": [
                {
                    "id": str(m.id),
                    "name": m.display_name,
                    "generic_name": m.generic_name,
                    "strength": m.strength,
                    "dose_per_intake": str(m.dose_per_intake),
                    "confirmed_stock": str(m.confirmed_stock),
                    "stock_unit": m.stock_unit,
                    "units_per_pack": str(m.units_per_pack) if m.units_per_pack else None,
                    "status": m.status,
                }
                for m in meds
            ]
        }

    if name == "get_refill_predictions":
        preds = get_refill_predictions(ctx.db, ctx.user)
        med_hint = args.get("medicine_name")
        if med_hint:
            matched = _match_owned(str(med_hint), ctx.active_meds)
            ids = {m.id for m in matched}
            if ids:
                preds = [p for p in preds if p.personal_med_id in ids]
        return {
            "predictions": [
                {
                    "medicine": p.display_name,
                    "estimated_remaining_days": p.estimated_remaining_days,
                    "projected_depletion_date": (
                        p.projected_depletion_date.isoformat() if p.projected_depletion_date else None
                    ),
                    "should_alert_now": p.should_alert_now,
                    "reason": p.reason,
                }
                for p in preds
            ]
        }

    if name == "get_next_dose":
        now = datetime.now(UTC)
        schedules_service.expire_overdue_doses(ctx.db, user_id=ctx.user.id, now=now)
        row = ctx.db.execute(
            select(DoseEvent, PersonalMedicine)
            .join(PersonalMedicine, DoseEvent.personal_med_id == PersonalMedicine.id)
            .where(
                DoseEvent.user_id == ctx.user.id,
                DoseEvent.status.in_(("pending", "snoozed")),
                DoseEvent.scheduled_at >= now - timedelta_1h(),
            )
            .order_by(DoseEvent.scheduled_at.asc())
        ).first()
        if row is None:
            return {"next_dose": None}
        dose, med = row
        ctx.med_id_context = med.id
        local_dt = _as_utc(dose.scheduled_at).astimezone(ctx.tz)
        return {
            "next_dose": {
                "dose_id": str(dose.id),
                "medicine": med.display_name,
                "expected_qty": str(dose.expected_qty),
                "unit": med.dose_unit,
                "scheduled_at_local": local_dt.strftime("%Y-%m-%d %H:%M"),
                "status": dose.status,
            }
        }

    if name == "search_medicine_catalogue":
        query = str(args.get("query") or "").strip()
        mfg = str(args.get("manufacturer") or "").strip() or None
        hits = search_catalogue(ctx.db, query=query, manufacturer=mfg, limit=6, include_external=False)
        return {
            "results": [
                {
                    "catalogue_id": str(h.id),
                    "brand_name": h.brand_name,
                    "generic_name": h.generic_name,
                    "strength": h.strength,
                    "dosage_form": h.dosage_form,
                    "manufacturer": h.manufacturer,
                    "standard_pack_size": str(h.standard_pack_size) if h.standard_pack_size else None,
                }
                for h in hits
            ]
        }

    if name == "get_medicine_education":
        med_name = str(args.get("medicine_name") or "").strip()
        if not med_name:
            return {"error": "medicine_name is required"}
        owned = _match_owned(med_name, ctx.active_meds)
        cat: MedicineCatalogue | None = None
        label = med_name
        if owned:
            m = owned[0]
            ctx.med_id_context = m.id
            label = m.display_name
            if m.catalogue_id:
                cat = ctx.db.get(MedicineCatalogue, m.catalogue_id)
        if cat is None:
            hits = search_catalogue(ctx.db, query=med_name, limit=1, include_external=False)
            if hits:
                cat = hits[0]
                label = cat.brand_name
        if cat is None:
            return {"error": f"No verified medicine found matching '{med_name}'."}
        edu = _ensure_catalogue_education(ctx.db, cat)
        if edu is None:
            return {"error": f"Educational details unavailable for '{label}'."}
        return {
            "medicine": label,
            "category": edu.category,
            "common_uses": edu.common_uses,
            "mechanism": edu.mechanism,
            "side_effects": edu.side_effects,
            "precautions": edu.precautions,
            "source": edu.source_name,
            "verified_at": edu.verified_at.isoformat(),
        }

    if name in {"stage_confirm_dose", "stage_skip_dose"}:
        today_local = datetime.now(UTC).astimezone(ctx.tz).date()
        daily = schedules_service.get_daily_schedule(ctx.db, ctx.user, target_date=today_local)
        pending = [d for d in daily if d.status in {"pending", "snoozed"}]
        med_hint = args.get("medicine_name")
        if med_hint:
            matched = _match_owned(str(med_hint), ctx.active_meds)
            ids = {m.id for m in matched}
            pending = [d for d in pending if d.personal_med_id in ids]
        window = args.get("time_window")
        if window in {"morning", "afternoon", "evening", "night"} and len(pending) > 1:
            windowed = [d for d in pending if _time_bucket(d.scheduled_at.astimezone(ctx.tz).hour) == window]
            if windowed:
                pending = windowed
        if not pending:
            return {"staged": False, "error": "No matching pending or snoozed dose found today."}
        if len(pending) > 1:
            return {
                "staged": False,
                "needs_clarification": True,
                "candidates": [
                    f"{d.display_name} at {d.scheduled_at.astimezone(ctx.tz).strftime('%H:%M')}"
                    for d in pending[:4]
                ],
            }
        target = pending[0]
        ctx.med_id_context = target.personal_med_id
        if name == "stage_confirm_dose":
            raw_qty = args.get("actual_quantity")
            qty_dec = (
                Decimal(str(raw_qty)).quantize(Decimal("0.01"))
                if raw_qty is not None and Decimal(str(raw_qty)) > 0
                else target.expected_qty
            )
            action = {
                "action_type": "confirm_dose",
                "dose_event_id": str(target.id),
                "personal_med_id": str(target.personal_med_id),
                "medicine_name": target.display_name,
                "actual_qty": str(qty_dec),
                "unit": target.dose_unit,
            }
            ctx.staged_actions.append(action)
            return {
                "staged": True,
                "requires_confirmation": True,
                "action": f"Confirm {target.display_name} ({qty_dec} {target.dose_unit})",
            }
        time_label = _as_utc(target.scheduled_at).astimezone(ctx.tz).strftime("%H:%M")
        action = {
            "action_type": "skip_dose",
            "dose_event_id": str(target.id),
            "personal_med_id": str(target.personal_med_id),
            "medicine_name": target.display_name,
            "time": time_label,
        }
        ctx.staged_actions.append(action)
        return {
            "staged": True,
            "requires_confirmation": True,
            "action": f"Skip {target.display_name} ({time_label})",
        }

    if name == "stage_stock_purchase":
        med_hint = str(args.get("medicine_name") or "").strip()
        matched = _match_owned(med_hint, ctx.active_meds)
        if not matched:
            return {"staged": False, "error": f"Active medicine '{med_hint}' not found in your medicines."}
        med = matched[0]
        ctx.med_id_context = med.id
        packs = max(0, int(args.get("packs") or 0))
        loose = Decimal(str(args.get("loose_units") or 0)).quantize(Decimal("0.01"))
        if packs <= 0 and loose <= 0:
            return {"staged": False, "needs_clarification": True, "error": "Specify number of packs or loose units purchased."}
        if packs > 0 and med.units_per_pack is None and loose <= 0:
            return {"staged": False, "error": f"Pack size is not configured for {med.display_name}; please give exact {med.stock_unit} count."}
        total = ((Decimal(packs) * (med.units_per_pack or Decimal("0"))) + loose).quantize(Decimal("0.01"))
        action = {
            "action_type": "update_stock_purchase",
            "personal_med_id": str(med.id),
            "medicine_name": med.display_name,
            "packs": packs,
            "loose_units": str(loose),
            "total_units_to_add": str(total),
            "unit": med.stock_unit,
        }
        ctx.staged_actions.append(action)
        return {
            "staged": True,
            "requires_confirmation": True,
            "action": f"Add +{total} {med.stock_unit} to {med.display_name} stock",
        }

    if name == "snooze_dose_reminder":
        today_local = datetime.now(UTC).astimezone(ctx.tz).date()
        daily = schedules_service.get_daily_schedule(ctx.db, ctx.user, target_date=today_local)
        pending = [d for d in daily if d.status in {"pending", "snoozed"}]
        med_hint = args.get("medicine_name")
        if med_hint:
            matched = _match_owned(str(med_hint), ctx.active_meds)
            ids = {m.id for m in matched}
            pending = [d for d in pending if d.personal_med_id in ids]
        if not pending:
            return {"snoozed": False, "error": "No pending dose found to snooze right now."}
        mins = max(5, min(120, int(args.get("minutes") or 15)))
        target = pending[0]
        res = schedules_service.snooze_dose(ctx.db, ctx.user, target.id, DoseSnoozeRequest(minutes=mins))
        ctx.med_id_context = target.personal_med_id
        until_local = _as_utc(res.dose.snoozed_until or res.dose.scheduled_at).astimezone(ctx.tz).strftime("%H:%M")
        return {
            "snoozed": True,
            "medicine": target.display_name,
            "minutes": mins,
            "snoozed_until_local": until_local,
        }

    return {"error": f"Unknown tool '{name}'"}


def timedelta_1h():
    from datetime import timedelta

    return timedelta(hours=1)
