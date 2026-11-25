# System Diagrams: NityaMed

**Project:** NityaMed — Medicine Continuity Management System (MCMS)  
**Baseline:** Consistent with SRS v1.0 & Initial Architecture v1.0 (Patient + System Admin only; Caregiver deferred to Phase 2; no doctor portal)

---

## 1. Use Case Diagram

**Explanation:** Shows every primary interaction boundary for the two MVP actors (**Patient** and **System Administrator**), plus supporting external services for speech/LLM and push fallback.

```mermaid
flowchart LR
    Patient(["Patient"])
    Admin(["System Administrator"])
    ExtAI(["External STT / TTS / Bounded LLM"])

    subgraph NityaMed["NityaMed Application Boundary"]
        UC1["UC-1: Register, Login & Manage PIN/Language"]
        UC2["UC-2: Search Catalogue or Add Custom Medicine"]
        UC3["UC-3: View Verified Non-Diagnostic Medicine Info"]
        UC4["UC-4: Create & Version Medication Schedules"]
        UC5["UC-5: Confirm / Skip / Partially Take / Correct Dose"]
        UC6["UC-6: Manage Stock, Purchases & Physical Reconciliation"]
        UC7["UC-7: View Refill Predictions & Alerts"]
        UC8["UC-8: Receive Privacy-Safe Local & Push Reminders"]
        UC9["UC-9: Use Multilingual Voice/Text Assistant"]
        UC10["UC-10: View Adherence Analytics & Pattern Summaries"]
        UC11["UC-11: Export Data or Delete Account"]
        UC12["UC-12: Curate & Verify Medicine Catalogue"]
        UC13["UC-13: Monitor Anonymized System Health"]
    end

    Patient --> UC1
    Patient --> UC2
    Patient --> UC3
    Patient --> UC4
    Patient --> UC5
    Patient --> UC6
    Patient --> UC7
    Patient --> UC8
    Patient --> UC9
    Patient --> UC10
    Patient --> UC11

    UC9 --> ExtAI

    Admin --> UC12
    Admin --> UC13
```

---

## 2. Context Diagram (DFD Level 0)

**Explanation:** Treats NityaMed as a single system boundary, illustrating all high-level data entering and leaving the platform.

```mermaid
flowchart LR
    Patient["Patient (Android App / Web)"]
    Admin["System Administrator"]
    SpeechLLM["Cloud STT / TTS / Bounded LLM"]
    PushSvc["Push Notification Service (FCM)"]

    NityaMed(("0.0 NityaMed MCMS"))

    Patient -->|"Auth, Medicines, Schedules, Dose Actions, Stock Updates, Voice/Text"| NityaMed
    NityaMed -->|"Daily Agenda, Verified Info, Refill Alerts, Analytics, TTS/Text Replies"| Patient

    Admin -->|"Verified Catalogue Entries, Source Metadata"| NityaMed
    NityaMed -->|"Catalogue Audit & System Health Metrics"| Admin

    NityaMed -->|"Audio Stream, Verified Text for Simplification/Translation"| SpeechLLM
    SpeechLLM -->|"Transcripts, Disambiguation / Translated Replies"| NityaMed

    NityaMed -->|"Fallback Alert Payloads (Privacy-Masked)"| PushSvc
    PushSvc -->|"Push Delivery Status"| NityaMed
```

---

## 3. Data Flow Diagram — Level 1 (DFD Level 1)

**Explanation:** Decomposes NityaMed into seven core functional processes (`1.0` to `7.0`) and six logical data stores (`D1` to `D6`), showing how schedules, dose events, stock transactions, and the hybrid assistant interact without bypassing validation.

```mermaid
flowchart TD
    Patient["Patient"]
    Admin["System Administrator"]
    ExtSpeech["External STT / TTS / LLM"]

    P1(("1.0 Auth & Profile Mgmt"))
    P2(("2.0 Medicine & Info Mgmt"))
    P3(("3.0 Schedule & Adherence Engine"))
    P4(("4.0 Inventory & Refill Engine"))
    P5(("5.0 Notification & Sync Coordinator"))
    P6(("6.0 Hybrid AI & ML Assistant"))
    P7(("7.0 Adherence Analytics"))

    D1[("D1: Users & Profiles")]
    D2[("D2: Medicine Catalogue & Education")]
    D3[("D3: Personal Meds & Schedule Versions")]
    D4[("D4: Dose Events")]
    D5[("D5: Stock Transactions Ledger")]
    D6[("D6: Notifications & Audit Logs")]

    Patient -->|"Credentials, Preferences"| P1
    P1 <--> D1

    Admin -->|"Catalogue Updates"| P2
    Patient -->|"Search / Custom Med"| P2
    P2 <--> D2
    P2 -->|"Save Personal Med"| D3

    Patient -->|"Schedule Rules, Dose Confirm/Correct"| P3
    P3 <--> D3
    P3 <--> D4
    P3 -->|"Confirmed Qty / Reversal"| P4

    Patient -->|"Purchase, Loss, Reconciliation"| P4
    P4 <--> D5
    P4 -->|"Depletion Dates & Refill Triggers"| P5

    P3 -->|"Upcoming Schedule Windows"| P5
    P5 <--> D6
    P5 -->|"Privacy-Safe Reminders & Refill Alerts"| Patient

    Patient -->|"Voice Audio / Text Query"| P6
    P6 <--> ExtSpeech
    P6 -->|"Verified Info Query"| P2
    P6 -->|"Confirmed Dose Action"| P3
    P6 -->|"Confirmed Stock Purchase"| P4
    P6 -->|"Assistant Reply + Confirmation Prompt"| Patient

    D4 --> P7
    D3 --> P7
    P7 -->|"Non-Clinical Adherence Reports"| Patient
```

---

## 4. Entity-Relationship (ER) Diagram

**Explanation:** Models the PostgreSQL relational schema. `MEDICINE_EDUCATION` is separated from `PERSONAL_MEDICINES` with source and date attribution; `SCHEDULE_VERSIONS` preserves historical regimens; and `DOSE_EVENTS` + `STOCK_TRANSACTIONS` enforce unique `client_event_id` keys for offline idempotency.

```mermaid
erDiagram
    USERS ||--|| PATIENT_PROFILES : has
    USERS ||--o{ PERSONAL_MEDICINES : owns
    USERS ||--o{ NOTIFICATIONS : receives
    USERS ||--o{ AUDIT_LOGS : triggers
    USERS ||--o{ CONVERSATION_STATES : maintains

    MEDICINE_CATALOGUE ||--o{ MEDICINE_EDUCATION : documents
    MEDICINE_CATALOGUE ||--o{ PERSONAL_MEDICINES : templates

    PERSONAL_MEDICINES ||--o{ SCHEDULE_VERSIONS : defines
    PERSONAL_MEDICINES ||--o{ DOSE_EVENTS : tracks
    PERSONAL_MEDICINES ||--o{ STOCK_TRANSACTIONS : logs

    SCHEDULE_VERSIONS ||--o{ DOSE_EVENTS : generates
    DOSE_EVENTS ||--o{ STOCK_TRANSACTIONS : deducts_or_reverses

    USERS {
        uuid id PK
        string email UK
        string password_hash
        string role
        boolean is_active
        timestamp created_at
    }

    PATIENT_PROFILES {
        uuid user_id PK,FK
        string display_name
        string preferred_lang
        string timezone
        boolean lockscreen_privacy
        int default_snooze_min
        int ontime_window_min
    }

    MEDICINE_CATALOGUE {
        uuid id PK
        string brand_name
        string generic_name
        string strength
        string dosage_form
        int standard_pack_size
        string manufacturer
        boolean is_verified
    }

    MEDICINE_EDUCATION {
        uuid id PK
        uuid catalogue_id FK
        string category
        text common_uses
        text mechanism
        text side_effects
        text precautions
        string source_name
        date verified_at
    }

    PERSONAL_MEDICINES {
        uuid id PK
        uuid user_id FK
        uuid catalogue_id FK
        boolean is_custom
        string display_name
        string generic_name
        string strength
        string dosage_form
        decimal dose_per_intake
        string dose_unit
        string stock_unit
        decimal confirmed_stock
        decimal low_stock_threshold
        string status
        text instructions
    }

    SCHEDULE_VERSIONS {
        uuid id PK
        uuid personal_med_id FK
        int version_number
        string frequency_type
        jsonb schedule_rules
        date start_date
        date end_date
        boolean is_prn
        timestamp effective_from
        timestamp effective_to
    }

    DOSE_EVENTS {
        uuid id PK
        uuid personal_med_id FK
        uuid schedule_version_id FK
        timestamp scheduled_at
        decimal expected_qty
        decimal confirmed_qty
        string status
        timestamp actioned_at
        uuid client_event_id UK
    }

    STOCK_TRANSACTIONS {
        uuid id PK
        uuid personal_med_id FK
        uuid dose_event_id FK
        string tx_type
        decimal qty_delta
        decimal balance_after
        string notes
        uuid client_event_id UK
        timestamp created_at
    }

    NOTIFICATIONS {
        uuid id PK
        uuid user_id FK
        uuid personal_med_id FK
        string notif_type
        string dedup_key UK
        timestamp scheduled_for
        string delivery_status
    }

    AUDIT_LOGS {
        uuid id PK
        uuid user_id FK
        string entity_type
        uuid entity_id
        string action
        jsonb metadata
        timestamp created_at
    }

    CONVERSATION_STATES {
        uuid id PK
        uuid user_id FK
        string active_intent
        jsonb pending_action
        timestamp expires_at
    }
```

---

## 5. Activity Diagram: Offline Dose Confirmation & Idempotent Sync

**Explanation:** Traces what happens when a patient acts on a scheduled dose while offline, ensuring local SQLite reflects reality immediately while PostgreSQL prevents duplicate deductions during synchronization.

```mermaid
flowchart TD
    Start(["Local Alarm Fires on Android"]) --> Action{"Patient Action?"}
    Action -->|"Snooze"| Snooze["Reschedule Local Alarm (+15 min) & Set Status = Snoozed"]
    Action -->|"Skip"| Skip["Generate client_event_id & Save Status = Explicitly skipped (0 Stock Change)"]
    Action -->|"Taken / Partial"| QtyCheck["Verify Actual Quantity Taken"]
    QtyCheck --> TimeCheck{"Within On-Time Window?"}
    TimeCheck -->|"Yes"| OnTime["Save Status = Taken on time"]
    TimeCheck -->|"No (Before Expiry)"| Late["Save Status = Taken late"]
    OnTime --> LocalDeduct["Deduct Qty in Local SQLite & Queue Sync Outbox"]
    Late --> LocalDeduct
    Skip --> QueueOnly["Queue Sync Outbox in SQLite"]

    LocalDeduct --> Online{"Internet Available?"}
    QueueOnly --> Online
    Online -->|"No"| WaitNet["Keep Queued Safely in SQLite"]
    WaitNet --> Online
    Online -->|"Yes"| SendAPI["POST /api/v1/sync/events with client_event_id"]

    SendAPI --> IdempCheck{"client_event_id Exists in PostgreSQL?"}
    IdempCheck -->|"Yes (Retry)"| ReturnAck["Return Prior Ack Without Mutating Stock"]
    IdempCheck -->|"No (New)"| CommitPG["Atomic DB Tx: Update DoseEvent + Append StockTransaction"]
    CommitPG --> UpdateRefill["Recompute Projected Depletion Date"]
    UpdateRefill --> ReturnAck
    ReturnAck --> ClearOutbox["Mark Outbox Item Synced in SQLite"]
    ClearOutbox --> EndNode(["Done"])
```

---

## 6. Sequence Diagram: Hybrid Voice Assistant Stock Update

**Explanation:** Demonstrates the safety-guarded pipeline (`STT -> Normalization -> Rules/ML Intent -> Confirmation Gate -> Validated Backend Transaction -> TTS`). No database write occurs until the user explicitly confirms.

```mermaid
sequenceDiagram
    actor P as Patient
    participant App as NityaMed Mobile (Expo)
    participant API as FastAPI Assistant Service
    participant STT as Cloud STT Adapter
    participant ML as Rules + Custom ML Intent
    participant LLM as Bounded LLM Adapter
    participant Inv as Inventory Service + PG
    participant TTS as Cloud TTS Adapter

    P->>App: Speaks "I bought one strip of Dolo" (EN/KN/HI)
    App->>API: POST /assistant/voice (audio + JWT)
    API->>STT: Transcribe audio
    STT-->>API: "I bought one strip of Dolo" + lang
    API->>ML: Normalize + classify intent + OOS check
    ML-->>API: intent=update_stock_purchase (conf=0.92)
    API->>LLM: Optional entity normalization if needed
    LLM-->>API: med="Dolo", qty=1, unit="strip"
    API->>Inv: Lookup user's personal medicine ("Dolo 650 mg")
    Inv-->>API: Found: 1 strip = 15 tablets
    API->>API: Save pending confirmation in conversation_states
    API->>TTS: Synthesize confirmation question in user's lang
    TTS-->>API: Audio prompt
    API-->>App: Display confirmation card + play audio ("Add 15 tablets to Dolo 650 mg?")

    P->>App: Taps "Confirm" (or says "Yes")
    App->>API: POST /assistant/confirm (confirmation_token)
    API->>Inv: Execute PURCHASE (+15 tablets) with idempotency_key
    Inv-->>API: New Confirmed Balance = 25 tablets
    API-->>App: Updated balance + confirmation message
```

---

## 7. Dose Event State Machine

**Explanation:** Enforces the SRS safety rule that unanswered doses become `Expired unconfirmed` (never automatically `Taken` or `Missed`) and accidental confirmations can be corrected through an audited flow.

```mermaid
stateDiagram-v2
    [*] --> Pending : Schedule materialized
    Pending --> Snoozed : User snoozes
    Snoozed --> Pending : Snooze timer fires

    Pending --> Taken_on_time : Confirmed within on-time window
    Snoozed --> Taken_on_time : Confirmed within on-time window

    Pending --> Taken_late : Confirmed after on-time window
    Snoozed --> Taken_late : Confirmed after on-time window

    Pending --> Partially_taken : Confirmed with partial qty
    Snoozed --> Partially_taken : Confirmed with partial qty

    Pending --> Explicitly_skipped : User skips dose
    Snoozed --> Explicitly_skipped : User skips dose

    Pending --> Expired_unconfirmed : Cutoff elapsed without action
    Snoozed --> Expired_unconfirmed : Cutoff elapsed without action

    Taken_on_time --> Explicitly_skipped : Audited accidental correction
    Taken_late --> Explicitly_skipped : Audited accidental correction
    Partially_taken --> Taken_late : Audited quantity correction
    Expired_unconfirmed --> Taken_late : Late manual logging allowed
```

---

## 8. Core Domain Class Diagram

**Explanation:** Shows the clean domain/service structure inside the FastAPI Modular Monolith, keeping deterministic logic cleanly separated from AI routing.

```mermaid
classDiagram
    class PersonalMedicine {
        +UUID id
        +UUID userId
        +string displayName
        +string dosageForm
        +decimal dosePerIntake
        +decimal confirmedStock
        +addStock(qty, txType, clientEventId)
    }

    class ScheduleVersion {
        +UUID id
        +int versionNumber
        +string frequencyType
        +dict scheduleRules
        +bool isPrn
        +generateEvents(fromDate, toDate)
    }

    class DoseEvent {
        +UUID id
        +datetime scheduledAt
        +string status
        +decimal confirmedQty
        +confirm(actualQty, actionedAt, clientEventId)
        +correct(newStatus, newQty, reason)
    }

    class InventoryLedgerService {
        +recordTransaction(medId, txType, delta, clientEventId)
        +reconcilePhysicalCount(medId, actualCount)
        +getProjectedBalance(medId, horizonDays)
    }

    class RefillPredictor {
        +estimateRemainingDays(med, activeSchedule)
        +computeDepletionDate(med, activeSchedule)
        +shouldAlert(med, activeSchedule)
    }

    class IntentRouter {
        +normalizeText(text, lang)
        +matchRules(text)
        +predictIntent(text)
        +isOutOfScope(confidence)
    }

    class AssistantOrchestrator {
        +handleVoiceOrText(userId, input)
        +requestConfirmation(userId, pendingAction)
        +commitConfirmedAction(userId, token)
    }

    PersonalMedicine "1" --> "*" ScheduleVersion
    PersonalMedicine "1" --> "*" DoseEvent
    ScheduleVersion "1" --> "*" DoseEvent
    InventoryLedgerService ..> PersonalMedicine
    InventoryLedgerService ..> DoseEvent
    RefillPredictor ..> PersonalMedicine
    RefillPredictor ..> ScheduleVersion
    AssistantOrchestrator --> IntentRouter
    AssistantOrchestrator --> InventoryLedgerService
    AssistantOrchestrator --> DoseEvent
```

---

## 9. Deployment Diagram

**Explanation:** Maps where every NityaMed runtime component executes using Render (Backend + Static Web) paired with persistent managed PostgreSQL (Neon/Supabase) and Expo Android APK builds.

```mermaid
flowchart TB
    subgraph Device["Patient Android Device"]
        RNApp["NityaMed Android APK (Expo)"]
        SQLite[("Expo SQLite")]
        OSAlarm["Android Exact Alarm / Notifications"]
        RNApp --> SQLite
        RNApp --> OSAlarm
    end

    subgraph WebBrowser["Desktop / Mobile Web Browser"]
        RNWeb["NityaMed Web App (Render Static Site)"]
    end

    subgraph RenderCloud["Render Cloud Hosting"]
        FastAPI["FastAPI Modular Monolith (Docker Web Service)"]
        CustomML["Lightweight Custom ML Intent Artifacts"]
        FastAPI --> CustomML
    end

    subgraph ManagedDB["Persistent Managed PostgreSQL (Neon / Supabase)"]
        PG[("PostgreSQL Primary DB")]
    end

    subgraph ExternalAPIs["External Cloud Services"]
        STT_TTS["STT / TTS Provider"]
        LLM_API["Bounded LLM API"]
        FCM["FCM Push Service"]
    end

    RNApp <-->|"HTTPS REST + Idempotent Sync"| FastAPI
    RNWeb <-->|"HTTPS REST"| FastAPI
    FastAPI <-->|"TLS / SQLAlchemy"| PG
    FastAPI <-->|"HTTPS"| STT_TTS
    FastAPI <-->|"HTTPS"| LLM_API
    FastAPI -->|"HTTPS"| FCM
    FCM -.->|"Fallback Push"| RNApp
```
