# Detailed Database Schema: NityaMed

**Project:** NityaMed — Medicine Continuity Management System (MCMS)  
**Primary DBMS:** PostgreSQL 15+ (Neon / Supabase, UTC timestamps)  
**Mobile Offline DBMS:** SQLite (`expo-sqlite`)  
**Scope:** MVP (Patient + System Admin; Caregiver deferred to Phase 2)

---

## 1. Core Architectural Rules
1. **UTC Everywhere:** All PostgreSQL timestamps use `TIMESTAMPTZ` stored in UTC; client converts to `patient_profiles.timezone` (default `Asia/Kolkata`).
2. **Ownership Isolation:** Every user-owned table carries `user_id` (or joins strictly through an owned parent verified against `current_user.id`).
3. **Append-Only Ledgers:** `stock_transactions` and `audit_logs` are never updated or deleted by application code; corrections append compensating entries.
4. **Historical Integrity:** `schedule_versions` are immutable once materialized into `dose_events`. Editing a schedule closes the active version (`effective_to = NOW()`) and creates `version_number + 1`.
5. **Offline Idempotency:** `dose_events.client_event_id` and `stock_transactions.client_event_id` carry `UNIQUE` constraints so network retries or offline sync replays never double-confirm doses or double-deduct stock.

---

## 2. PostgreSQL Schema (DDL Specification)

### 2.1 Users & Patient Profiles

```sql
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'patient'
        CHECK (role IN ('patient', 'admin')),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    deleted_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE refresh_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash TEXT NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_refresh_tokens_user ON refresh_tokens(user_id);

CREATE TABLE patient_profiles (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    display_name VARCHAR(120) NOT NULL,
    preferred_lang VARCHAR(5) NOT NULL DEFAULT 'en'
        CHECK (preferred_lang IN ('en', 'kn', 'hi')),
    timezone VARCHAR(64) NOT NULL DEFAULT 'Asia/Kolkata',
    lockscreen_privacy BOOLEAN NOT NULL DEFAULT TRUE,
    default_snooze_min SMALLINT NOT NULL DEFAULT 15
        CHECK (default_snooze_min BETWEEN 5 AND 60),
    ontime_window_min SMALLINT NOT NULL DEFAULT 30
        CHECK (ontime_window_min BETWEEN 10 AND 120),
    expiry_cutoff_hours SMALLINT NOT NULL DEFAULT 4
        CHECK (expiry_cutoff_hours BETWEEN 1 AND 12),
    refill_alert_days SMALLINT NOT NULL DEFAULT 5
        CHECK (refill_alert_days BETWEEN 1 AND 30),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### 2.2 Medicine Catalogue & Verified Education

```sql
CREATE TABLE medicine_catalogue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    brand_name VARCHAR(200) NOT NULL,
    generic_name VARCHAR(200) NOT NULL,
    active_ingredients TEXT NULL,
    strength VARCHAR(100) NOT NULL,
    dosage_form VARCHAR(30) NOT NULL
        CHECK (dosage_form IN ('tablet', 'capsule', 'syrup', 'injection', 'inhaler', 'drops', 'other')),
    standard_pack_size NUMERIC(10, 2) NULL
        CHECK (standard_pack_size IS NULL OR standard_pack_size > 0),
    pack_unit VARCHAR(30) NULL,
    manufacturer VARCHAR(200) NULL,
    is_verified BOOLEAN NOT NULL DEFAULT TRUE,
    is_deprecated BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_catalogue_brand ON medicine_catalogue (LOWER(brand_name));
CREATE INDEX idx_catalogue_generic ON medicine_catalogue (LOWER(generic_name));

CREATE TABLE medicine_education (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    catalogue_id UUID NOT NULL REFERENCES medicine_catalogue(id) ON DELETE CASCADE,
    category VARCHAR(150) NOT NULL,
    common_uses TEXT NOT NULL,
    mechanism TEXT NOT NULL,
    side_effects TEXT NOT NULL,
    precautions TEXT NOT NULL,
    additional_notes TEXT NULL,
    source_name VARCHAR(200) NOT NULL,
    source_url TEXT NULL,
    verified_at DATE NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (catalogue_id)
);
```

### 2.3 Personal Medicines & Schedule Versions

```sql
CREATE TABLE personal_medicines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    catalogue_id UUID NULL REFERENCES medicine_catalogue(id) ON DELETE SET NULL,
    is_custom BOOLEAN NOT NULL DEFAULT FALSE,
    display_name VARCHAR(200) NOT NULL,
    generic_name VARCHAR(200) NULL,
    strength VARCHAR(100) NOT NULL,
    dosage_form VARCHAR(30) NOT NULL
        CHECK (dosage_form IN ('tablet', 'capsule', 'syrup', 'injection', 'inhaler', 'drops', 'other')),
    dose_per_intake NUMERIC(10, 2) NOT NULL CHECK (dose_per_intake > 0),
    dose_unit VARCHAR(30) NOT NULL,
    stock_unit VARCHAR(30) NOT NULL,
    units_per_pack NUMERIC(10, 2) NULL CHECK (units_per_pack IS NULL OR units_per_pack > 0),
    confirmed_stock NUMERIC(12, 2) NOT NULL DEFAULT 0 CHECK (confirmed_stock >= 0),
    low_stock_threshold NUMERIC(10, 2) NULL CHECK (low_stock_threshold IS NULL OR low_stock_threshold >= 0),
    instructions TEXT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'paused', 'completed', 'archived')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK ((is_custom = TRUE) OR (catalogue_id IS NOT NULL))
);
CREATE INDEX idx_personal_meds_user_status ON personal_medicines(user_id, status);

CREATE TABLE schedule_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    personal_med_id UUID NOT NULL REFERENCES personal_medicines(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL CHECK (version_number >= 1),
    frequency_type VARCHAR(30) NOT NULL
        CHECK (frequency_type IN (
            'once_daily', 'multiple_daily', 'alternate_day',
            'weekly', 'selected_weekdays', 'varying_dose', 'fixed_course', 'as_needed'
        )),
    -- schedule_rules JSON structure:
    -- e.g. {"times": [{"time": "08:00", "dose": 1.0}, {"time": "20:00", "dose": 0.5}], "weekdays": [1,3,5], "interval_days": 2}
    schedule_rules JSONB NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NULL,
    is_prn BOOLEAN NOT NULL DEFAULT FALSE,
    effective_from TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    effective_to TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (personal_med_id, version_number),
    CHECK (end_date IS NULL OR end_date >= start_date)
);
CREATE INDEX idx_schedule_active ON schedule_versions(personal_med_id) WHERE effective_to IS NULL;
```

### 2.4 Dose Events & Stock Transactions (Idempotent & Append-Only)

```sql
CREATE TABLE dose_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    personal_med_id UUID NOT NULL REFERENCES personal_medicines(id) ON DELETE CASCADE,
    schedule_version_id UUID NOT NULL REFERENCES schedule_versions(id) ON DELETE RESTRICT,
    scheduled_at TIMESTAMPTZ NOT NULL,
    expected_qty NUMERIC(10, 2) NOT NULL CHECK (expected_qty > 0),
    confirmed_qty NUMERIC(10, 2) NOT NULL DEFAULT 0 CHECK (confirmed_qty >= 0),
    status VARCHAR(30) NOT NULL DEFAULT 'pending'
        CHECK (status IN (
            'pending', 'snoozed', 'taken_on_time', 'taken_late',
            'explicitly_skipped', 'partially_taken', 'expired_unconfirmed'
        )),
    snoozed_until TIMESTAMPTZ NULL,
    actioned_at TIMESTAMPTZ NULL,
    client_event_id UUID NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (schedule_version_id, scheduled_at)
);
CREATE INDEX idx_dose_events_user_date ON dose_events(user_id, scheduled_at);
CREATE INDEX idx_dose_events_med_status ON dose_events(personal_med_id, status);

CREATE TABLE stock_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    personal_med_id UUID NOT NULL REFERENCES personal_medicines(id) ON DELETE CASCADE,
    dose_event_id UUID NULL REFERENCES dose_events(id) ON DELETE RESTRICT,
    tx_type VARCHAR(30) NOT NULL
        CHECK (tx_type IN (
            'INITIAL', 'DOSE_CONFIRMED', 'PURCHASE',
            'MANUAL_ADJUSTMENT', 'EXPIRED_DAMAGED_LOST',
            'RECONCILIATION', 'CORRECTION_REVERSAL'
        )),
    qty_delta NUMERIC(12, 2) NOT NULL,
    balance_after NUMERIC(12, 2) NOT NULL CHECK (balance_after >= 0),
    notes TEXT NULL,
    client_event_id UUID NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_stock_tx_med_time ON stock_transactions(personal_med_id, created_at DESC);
```

> **Stock Clamp Rule (`balance_after >= 0`):** As required by `FR-IN-06`, if a user confirms a dose when `confirmed_stock` is `0`, the dose confirmation is still saved, and `DOSE_CONFIRMED` records `qty_delta = 0` (with `notes = 'Confirmed at zero recorded stock; reconciliation prompted'`) so the ledger never breaks into negative inventory while still recording the adherence event accurately.

### 2.5 Notifications, Audit Logs & Assistant State

```sql
CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    personal_med_id UUID NULL REFERENCES personal_medicines(id) ON DELETE CASCADE,
    notif_type VARCHAR(30) NOT NULL
        CHECK (notif_type IN ('dose_reminder', 'low_stock', 'refill_alert', 'system')),
    dedup_key VARCHAR(160) NOT NULL UNIQUE,
    scheduled_for TIMESTAMPTZ NOT NULL,
    sent_at TIMESTAMPTZ NULL,
    delivery_status VARCHAR(20) NOT NULL DEFAULT 'scheduled'
        CHECK (delivery_status IN ('scheduled', 'delivered', 'dismissed', 'failed')),
    payload_preview VARCHAR(160) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_notifications_user_sched ON notifications(user_id, scheduled_for);

CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NULL REFERENCES users(id) ON DELETE SET NULL,
    actor_role VARCHAR(20) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id UUID NULL,
    action VARCHAR(60) NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_audit_user_time ON audit_logs(user_id, created_at DESC);

CREATE TABLE conversation_states (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    active_intent VARCHAR(80) NULL,
    context_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    pending_action JSONB NULL,
    confirmation_token UUID NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_conv_user_exp ON conversation_states(user_id, expires_at);
```

---

## 3. Mobile Offline SQLite Schema (`expo-sqlite`)

On Android, the mobile client maintains a compact offline mirror (default sync window: **last 30 days + next 14 days** of dose events, plus all active `personal_medicines` and `schedule_versions`) alongside an append-only `sync_outbox`:

```sql
CREATE TABLE IF NOT EXISTS local_medicines (
    id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    dosage_form TEXT NOT NULL,
    dose_per_intake REAL NOT NULL,
    dose_unit TEXT NOT NULL,
    stock_unit TEXT NOT NULL,
    units_per_pack REAL,
    confirmed_stock REAL NOT NULL,
    instructions TEXT,
    status TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS local_dose_events (
    id TEXT PRIMARY KEY,
    personal_med_id TEXT NOT NULL,
    schedule_version_id TEXT NOT NULL,
    scheduled_at TEXT NOT NULL,
    expected_qty REAL NOT NULL,
    confirmed_qty REAL NOT NULL DEFAULT 0,
    status TEXT NOT NULL,
    snoozed_until TEXT,
    actioned_at TEXT,
    client_event_id TEXT,
    sync_status TEXT NOT NULL DEFAULT 'synced'
);

CREATE TABLE IF NOT EXISTS sync_outbox (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_event_id TEXT NOT NULL UNIQUE,
    event_type TEXT NOT NULL, -- 'DOSE_ACTION' | 'STOCK_TX' | 'DOSE_CORRECTION'
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    last_error TEXT,
    synced_at TEXT
);
```

---

## 4. Key Validation & Migration Strategy
- **Migrations:** Managed via **Alembic** (`alembic upgrade head`) inside the FastAPI repository.
- **Data Integrity Check:** Application services wrap dose confirmation + stock deduction inside a single PostgreSQL `SERIALIZABLE` or row-locked (`SELECT ... FOR UPDATE` on `personal_medicines`) transaction to prevent race conditions.
