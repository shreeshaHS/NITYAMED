# REST API Design Specification: NityaMed

**Project:** NityaMed — Medicine Continuity Management System (MCMS)  
**Base URL:** `/api/v1`  
**Protocol:** HTTPS + JSON (`application/json`; `multipart/form-data` for voice audio)  
**Authentication:** Bearer JWT (`Authorization: Bearer <access_token>`)  

---

## 1. Cross-Cutting API Conventions

### 1.1 Standard Error Format
Every non-2xx response returns a consistent envelope:
```json
{
  "error": {
    "code": "INSUFFICIENT_PERMISSION",
    "message": "Human-readable message suitable for client mapping",
    "details": {}
  }
}
```

### 1.2 Idempotency & Ownership
- **Ownership Enforcement:** Every patient endpoint injects `current_user` from the verified JWT and filters queries by `user_id == current_user.id`. Accessing another user's resource ID returns `404` or `403`.
- **Idempotency:** All mutating offline-capable endpoints (`confirm`, `skip`, `stock`, `sync`) require a UUID `client_event_id` (in body or `X-Idempotency-Key` header). Replaying the same `client_event_id` returns `200 OK` with `"idempotent_replay": true` and performs zero duplicate database mutations.

---

## 2. Endpoint Catalogue by Module

### 2.1 Auth & Profile (`/auth`, `/profile`)

| Method | Endpoint | Auth | Purpose |
| :--- | :--- | :--- | :--- |
| `POST` | `/auth/register` | Public | Register new patient (`email`, `password`, `display_name`, `preferred_lang`). |
| `POST` | `/auth/login` | Public | Authenticate via email + password; returns `access_token` + `refresh_token`. |
| `POST` | `/auth/refresh` | Public | Rotate refresh token and issue new access token. |
| `POST` | `/auth/logout` | Patient/Admin | Revoke current refresh token. |
| `GET` | `/profile` | Patient | Fetch profile settings (`preferred_lang`, `lockscreen_privacy`, `ontime_window_min`, etc.). |
| `PATCH` | `/profile` | Patient | Update language, timezone, snooze/window thresholds, or privacy preferences. |
| `GET` | `/profile/export` | Patient | Export personal medicines, schedules, dose history, and stock ledger (JSON/CSV). |
| `DELETE` | `/profile` | Patient | Permanently delete account (requires password re-confirmation). |

### 2.2 Medicine Catalogue & Education (`/catalogue`)

| Method | Endpoint | Auth | Purpose |
| :--- | :--- | :--- | :--- |
| `GET` | `/catalogue/search?q=&form=&limit=20` | Patient/Admin | Search verified Indian seed catalogue by brand name, generic name, or ingredient. |
| `GET` | `/catalogue/{catalogue_id}/education?lang=en` | Patient/Admin | Retrieve verified medicine education with `source_name`, `verified_at`, and non-diagnostic disclaimer. |

### 2.3 Personal Medicines & Schedules (`/medicines`, `/schedules`)

| Method | Endpoint | Auth | Purpose |
| :--- | :--- | :--- | :--- |
| `GET` | `/medicines?status=active` | Patient | List user's personal medicines with confirmed stock and refill summary. |
| `POST` | `/medicines` | Patient | Add personal medicine (catalogue-linked or `is_custom=true`), initial stock (`INITIAL` tx), and optional initial schedule. |
| `GET` | `/medicines/{med_id}` | Patient | Get full medicine details, active schedule version, and linked education (or unverified fallback notice). |
| `PATCH` | `/medicines/{med_id}` | Patient | Update instructions, thresholds, or pause/complete/archive status. |
| `POST` | `/medicines/{med_id}/schedules` | Patient | Create a new immutable `schedule_version` (closes prior version cleanly) and materialize upcoming `dose_events`. |
| `GET` | `/medicines/{med_id}/schedules` | Patient | View current and historical schedule versions. |

### 2.4 Adherence & Daily Schedule (`/doses`)

| Method | Endpoint | Auth | Purpose |
| :--- | :--- | :--- | :--- |
| `GET` | `/doses/daily?date=YYYY-MM-DD` | Patient | Return chronological daily agenda; runs lazy expiry check on overdue past-cutoff doses first. |
| `POST` | `/doses/{dose_id}/confirm` | Patient | Confirm dose (`taken_on_time` / `taken_late` / `partially_taken`) with `actual_qty`, `actioned_at`, `client_event_id`. Atomically deducts `confirmed_stock`. |
| `POST` | `/doses/{dose_id}/skip` | Patient | Mark dose `explicitly_skipped` (`0` stock deduction) with `client_event_id`. |
| `POST` | `/doses/{dose_id}/snooze` | Patient | Snooze dose by `minutes` and return updated `snoozed_until`. |
| `POST` | `/doses/{dose_id}/correct` | Patient | Audited accidental confirmation correction; reverses or adjusts prior `stock_transactions` entry and logs to `audit_logs`. |

### 2.5 Inventory & Refill Prediction (`/inventory`, `/refills`)

| Method | Endpoint | Auth | Purpose |
| :--- | :--- | :--- | :--- |
| `GET` | `/inventory/summary` | Patient | Return **Confirmed Stock Balance** vs. **Projected Stock Balance (Estimate)** for all active medicines. |
| `GET` | `/inventory/{med_id}/transactions?limit=50` | Patient | Paginated append-only stock ledger for a medicine. |
| `POST` | `/inventory/{med_id}/purchase` | Patient | Add purchased stock (supports `strips` + `loose_units` conversion) with `client_event_id`. |
| `POST` | `/inventory/{med_id}/adjust` | Patient | Record manual adjustment or `EXPIRED_DAMAGED_LOST` stock deduction. |
| `POST` | `/inventory/{med_id}/reconcile` | Patient | Submit physical counted stock; computes delta and appends `RECONCILIATION` ledger entry. |
| `GET` | `/refills/predictions` | Patient | Return deterministic remaining days, depletion date, and refill alert flags (excluding completed & PRN daily burn). |

### 2.6 Offline Sync (`/sync`)

| Method | Endpoint | Auth | Purpose |
| :--- | :--- | :--- | :--- |
| `POST` | `/sync/events` | Patient | Accept ordered batch of offline `DOSE_ACTION`, `DOSE_CORRECTION`, and `STOCK_TX` events; processes each idempotently inside transactions and returns per-event status (`applied`, `duplicate_ignored`, `rejected`). |
| `GET` | `/sync/bootstrap?since=ISO8601` | Patient | Pull updated medicines, active schedule versions, and upcoming 14-day / past 30-day dose events for local SQLite hydration. |

**Sync Batch Request Example:**
```json
{
  "events": [
    {
      "client_event_id": "9f23a8c1-7c21-4e20-b6d1-1c93f8e21001",
      "event_type": "DOSE_ACTION",
      "dose_event_id": "2c8d1120-...",
      "action": "confirm",
      "actual_qty": 1.0,
      "actioned_at": "2026-11-24T08:05:00+05:30"
    }
  ]
}
```

### 2.7 Hybrid Voice & Text Assistant (`/assistant`)

| Method | Endpoint | Auth | Purpose |
| :--- | :--- | :--- | :--- |
| `POST` | `/assistant/text` | Patient | Run `Normalize -> Rules -> Custom ML Intent -> Entity/Dialogue -> Safety Guardrails -> Verified Read OR Pending Confirmation Token`. |
| `POST` | `/assistant/voice` | Patient | Accepts audio upload (`multipart/form-data`), runs `STT -> Text Pipeline -> TTS`, returns transcript, intent, text reply, audio URL/bytes, and optional `confirmation_token`. |
| `POST` | `/assistant/confirm` | Patient | Executes a staged mutation (`confirmation_token`, `approved: true/false`) after explicit user confirmation. |

**Assistant Safety Response Shape (Confirmation Gate):**
```json
{
  "reply_text": "Do you want to add 15 tablets to Dolo 650 mg?",
  "language": "en",
  "intent": "update_stock_purchase",
  "requires_confirmation": true,
  "confirmation_token": "e4d12a78-...",
  "proposed_action": {
    "medicine_id": "7a11...",
    "medicine_name": "Dolo 650 mg",
    "qty_to_add": 15,
    "unit": "tablet"
  },
  "tts_audio_base64": "..."
}
```

### 2.8 Analytics & Notifications (`/analytics`, `/notifications`)

| Method | Endpoint | Auth | Purpose |
| :--- | :--- | :--- | :--- |
| `GET` | `/analytics/adherence?days=30` | Patient | Returns counts, documented formulas (`Confirmed Adherence Rate`, `Unconfirmed Rate`), per-medicine breakdown, and non-clinical pattern observations. |
| `GET` | `/notifications/history` | Patient | List notification delivery & refill alert history. |

### 2.9 System Admin & Internal Maintenance (`/admin`, `/internal`)

| Method | Endpoint | Auth | Purpose |
| :--- | :--- | :--- | :--- |
| `POST` | `/admin/catalogue` | Admin | Create verified catalogue + education entry with source & verification date. |
| `PATCH` | `/admin/catalogue/{catalogue_id}` | Admin | Update or deprecate catalogue/education entry (audit-logged). |
| `GET` | `/admin/health/metrics` | Admin | Anonymized platform counts (total users, active jobs, ML inference error rate—zero patient PII). |
| `POST` | `/internal/jobs/sweep` | Cron Secret Header | Triggered by external scheduler (for Render free tier) to expire stale doses and generate refill alert records idempotently. |

---

## 3. Rate Limiting & Security Controls (API Layer)
- `/auth/login`, `/auth/register`: Strict IP/account rate limit (e.g., `10 req/min`) to block brute-force attempts.
- `/assistant/*`: Per-user rate limit (e.g., `20 req/min`) to control external STT/TTS/LLM API quotas.
- `/internal/jobs/sweep`: Protected by constant-time comparison against `CRON_SECRET` environment variable (never exposed to patient/admin roles).
