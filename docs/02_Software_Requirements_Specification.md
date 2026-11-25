# Software Requirements Specification (SRS): NityaMed

**Project:** NityaMed — Medicine Continuity Management System (MCMS)  
**Version:** 1.0 (MVP Baseline)

---

## 1. Introduction

### 1.1 Purpose
This Software Requirements Specification (SRS) defines the complete functional, non-functional, data, interface, safety, and security requirements for the **NityaMed (MCMS)** MVP. It serves as the binding contract between requirements analysis, system architecture, database design, implementation, and testing.

### 1.2 Document Conventions
- **FR-XX-NN:** Functional Requirement (by module code and number).
- **NFR-NN:** Non-Functional Requirement.
- **SAF-NN / SEC-NN:** Safety and Security Requirements.
- **Proposed Default:** Clearly marked engineering defaults subject to validation during implementation/UAT.

### 1.3 Scope
**NityaMed** is a patient-centric medication continuity platform delivered as a **React Native (Expo)** cross-platform Android mobile app (primary, offline-capable) and Web companion, backed by a **Python (FastAPI)** modular monolith hosted on **Render** and a persistent **PostgreSQL** database (Neon/Supabase).

**Explicit Scope Boundaries (MVP):**
- **Included:** Patient workflows across Modules 1–11, minimal System Administrator catalogue/platform management, English/Kannada/Hindi support, custom ML intent model + bounded hybrid voice assistant.
- **Excluded:** Doctor/provider portals or notifications, handwritten prescription OCR, Caregiver accounts/linking (deferred to Phase 2), and any clinical diagnosis or treatment recommendation.

---

## 2. Product Overview

### 2.1 System Context
NityaMed coordinates four core domains:
1. **Deterministic Continuity Engine:** Schedules, strict dose-state tracking, transaction-based stock ledger, and deterministic refill predictions.
2. **Offline-First Mobile Runtime:** Local SQLite persistence, exact local alarm scheduling, and idempotent event synchronization.
3. **Verified Education Layer:** Curated Indian brand/generic seed catalogue linked to verified non-diagnostic generic information, plus custom entry fallback.
4. **Hybrid Multilingual Assistant:** Speech/text pipeline combining deterministic rules, a custom-trained ML intent model, and a strictly bounded LLM behind backend authorization and user confirmation gates.

### 2.2 User Characteristics

| Role | Description | Technical Profile | Access Scope |
| :--- | :--- | :--- | :--- |
| **Patient (Primary)** | Elderly patients, chronic-care patients, multi-medicine users in India. | Low-to-moderate digital literacy; may prefer Kannada, Hindi, or code-switched speech; intermittent internet. | Own profile, medicines, schedules, doses, inventory, analytics, voice assistant. |
| **System Administrator** | Technical maintainer managing shared system operations. | High technical proficiency. | Shared medicine catalogue curation, anonymized system/job health metrics. **Zero access** to individual patient medication histories or PII unless explicit consent/support workflow applies. |

---

## 3. Assumptions and Constraints
- **A-01 (Platform Split):** Full offline dose confirmation, SQLite storage, and local alarms are supported on the **Android mobile app**. The **Web app** operates as an online-connected companion (due to browser limits on background alarms when tabs are closed).
- **A-02 (Voice Connectivity):** Cloud STT, TTS, and bounded LLM require active internet; when offline, voice/LLM queries gracefully notify the user while local tap UI remains fully functional.
- **A-03 (Indian Medicine Data):** No single free official Indian REST API provides complete brand-to-generic mappings and patient leaflets; MVP relies on a curated seed dataset + custom entry fallback.
- **C-01 (Solo Development & Hosting Constraints):** Zero/low-cost cloud tiers (Render Web Service + Static Site, Neon/Supabase PostgreSQL). Deployed ML models must fit within Render free-tier memory constraints (~512 MB RAM), and scheduled server tasks must account for free-tier container sleep behavior.
- **C-02 (Medical Non-Intervention):** NityaMed is a continuity and informational aid only—not a medical device, diagnostic engine, or prescribing tool.

---

## 4. Functional Requirements

### 4.1 Module 1: User Management (`FR-UM`)
- **FR-UM-01:** The system shall allow new patients to register using a unique email address and password meeting minimum complexity rules (at least 8 characters).
- **FR-UM-02:** The system shall authenticate users via Email + Password and issue short-lived access tokens paired with revocable refresh tokens.
- **FR-UM-03:** On mobile devices, the system shall allow an authenticated user to enable an optional local 4-digit PIN or device biometric unlock for daily app entry without re-entering their password.
- **FR-UM-04:** Users shall be able to view and update profile details (display name, age group/timezone, preferred language: `English`, `Kannada`, or `Hindi`, and notification privacy/snooze preferences).
- **FR-UM-05:** Users shall be able to export all personal medication, adherence, and stock transaction data in structured machine-readable format (JSON/CSV).
- **FR-UM-06:** Users shall be able to request permanent account deletion, cascading or anonymizing personal records per retention/safety policy.

### 4.2 Module 2: Medicine Management (`FR-MM`)
- **FR-MM-01:** Users shall be able to search the built-in medicine catalogue by brand name, generic name, or active ingredient.
- **FR-MM-02:** Users shall be able to add a custom medicine manually when a medicine is missing from the catalogue.
- **FR-MM-03:** Each personal medicine entry shall store separately:
  - Medicine name (brand and/or generic), strength (e.g., `500 mg`, `5 mg/5 ml`), dosage form (`Tablet`, `Capsule`, `Syrup`, `Injection`, `Inhaler`, `Drops`, `Other`), and optional manufacturer/active ingredients.
  - **Prescribed dose per administration** (numeric quantity + unit, e.g., `1 tablet`, `5 ml`, `2 puffs`).
  - **Available stock quantity** (numeric quantity + base unit, supporting full strips, partial strips, or loose units—e.g., `1 strip of 10 + 4 loose = 14 tablets`).
  - Start date, optional end date (or fixed duration), and special instructions (e.g., *"after food"*).
- **FR-MM-04:** Users shall be able to edit, pause, archive/complete, or soft-delete personal medicines while preserving historical dose and stock records.

### 4.3 Module 3: Medicine Information & Education (`FR-ME`)
- **FR-ME-01:** For catalogue-linked medicines, the system shall display verified educational fields: common uses, mechanism of action (how it works), medicine category, common side effects, and important precautions.
- **FR-ME-02:** Every educational entry shall visibly display its **source name** and **last verified/updated date**.
- **FR-ME-03:** For custom user-entered medicines without a verified link, the system shall clearly display *"Unverified custom entry — educational details unavailable"* rather than guessing or generating facts.
- **FR-ME-04:** Translated or simplified education text (via LLM or pre-translated verified content) shall include a non-clinical disclaimer and shall never infer the patient's diagnosis or recommend starting, stopping, or modifying doses.

### 4.4 Module 4: Medication Adherence Management (`FR-AD`)
- **FR-AD-01:** The system shall support creating immutable **Schedule Versions** (preserving past schedules when timings or doses change) for patterns: once daily, multiple times per day, alternate-day, weekly, selected weekdays, varying dose by time-of-day, fixed-course, and as-needed (PRN).
- **FR-AD-02:** The system shall generate a chronological **Daily Schedule** of dose events for any selected date.
- **FR-AD-03:** Each scheduled dose event shall strictly follow valid state transitions across: `Pending`, `Snoozed`, `Taken on time`, `Taken late`, `Explicitly skipped`, `Partially taken`, and `Expired unconfirmed`.
- **FR-AD-04 (Proposed Default Time Windows):** A scheduled dose confirmed within `±30 minutes` (configurable `15–60 min`) of scheduled time shall record as `Taken on time`; confirmed after that window and before the expiry cutoff (`4 hours` or next scheduled dose of the same medicine, whichever is earlier) shall record as `Taken late`; unanswered past the cutoff shall transition to `Expired unconfirmed`.
- **FR-AD-05:** For `Partially taken`, the user shall enter the actual quantity consumed (e.g., `1` instead of `2` tablets) before saving.
- **FR-AD-06:** The system shall never automatically mark an unanswered dose as `Taken` or `Missed`.
- **FR-AD-07:** The system shall prevent duplicate confirmations for the same dose event via unique event IDs (`idempotency_key`).
- **FR-AD-08:** Users shall be able to correct an accidental confirmation within an audit-logged correction flow, automatically reversing or adjusting the linked stock transaction.

### 4.5 Module 5: Medicine Inventory Management (`FR-IN`)
- **FR-IN-01:** Every stock change shall be recorded as an immutable **Stock Transaction** (`INITIAL`, `DOSE_CONFIRMED`, `PURCHASE`, `MANUAL_ADJUSTMENT`, `EXPIRED_DAMAGED_LOST`, `RECONCILIATION`, `CORRECTION_REVERSAL`).
- **FR-IN-02:** The system shall maintain and clearly distinguish:
  - **Confirmed Stock Balance:** Exact sum of recorded stock transactions.
  - **Projected Stock Balance:** Estimated remaining stock subtracting upcoming pending/scheduled doses over a forecast horizon, explicitly labeled **"Estimate"**.
- **FR-IN-03:** Confirming a dose as `Taken on time`, `Taken late`, or `Partially taken` shall deduct the exact confirmed quantity from Confirmed Stock Balance.
- **FR-IN-04:** Marking a dose `Explicitly skipped` or `Expired unconfirmed` shall **not** deduct stock.
- **FR-IN-05:** Users shall be able to record new purchases (in strips or loose units), log expired/damaged/lost units, and perform **Physical Stock Reconciliation** (entering actual counted stock, which logs the delta rather than overwriting history).
- **FR-IN-06:** If Confirmed Stock reaches `0` while a user confirms a dose, the system shall allow the confirmation (safety/reality first: the user may have bought a new strip they haven't logged yet) and prompt the user to update/reconcile stock rather than blocking adherence logging.

### 4.6 Module 6: Refill Prediction & Alerts (`FR-RF`)
- **FR-RF-01:** Using deterministic schedule rules and Confirmed Stock Balance, the system shall calculate: estimated remaining days, projected depletion date, refill threshold (default: `5 days` of supply or user-configured minimum units), and suggested refill alert date.
- **FR-RF-02:** Calculations shall accurately model varying-dose, alternate-day, selected-weekday, and fixed-course end dates.
- **FR-RF-03:** Completed/stopped courses shall not generate refill alerts.
- **FR-RF-04:** As-needed (PRN) medicines shall not assume fixed daily consumption; optional low-stock alerts may trigger only if the user sets a static minimum unit threshold.

### 4.7 Module 7: Notification Management (`FR-NF`)
- **FR-NF-01:** On Android, the app shall schedule **local notifications** as the primary reminder mechanism so alerts fire offline and independently of backend server sleep states.
- **FR-NF-02:** Notifications shall support direct actions (`Mark Taken`, `Snooze 15 min`, `Skip`) and privacy-safe lock-screen mode (hiding medicine names on lock screen by default).
- **FR-NF-03:** The system shall deduplicate reminders across app restarts, schedule edits, and server-push fallbacks using deterministic notification keys.
- **FR-NF-04:** The mobile app shall detect disabled notification permissions or restrictive Android battery optimization and guide the user with clear, simple instructions.
- **FR-NF-05:** The system shall log notification delivery/trigger history and generate low-stock/refill alerts when refill thresholds are crossed.

### 4.8 Module 8: Hybrid AI Voice Assistant (`FR-VA`)
- **FR-VA-01:** The assistant shall be accessible across core patient screens via both **Voice (mic)** and **Text** input in English, Kannada, and Hindi.
- **FR-VA-02:** Voice input shall execute the staged pipeline: `Audio -> Cloud STT -> Language Detection -> Text Normalization -> Rule-Based Match -> Custom ML Intent Classifier -> Entity Extraction -> Dialogue State Check -> Safety Guardrails -> Backend API / Verified Retrieval -> Bounded Response Generation -> Cloud TTS`.
- **FR-VA-03:** The assistant shall support read-only queries (remaining stock, today's medicines, next dose, adherence status, refill date, verified medicine usage) and stateful actions (dose confirmation, stock purchase update, schedule assistance).
- **FR-VA-04:** **Safety Gates:**
  - Any state-changing action (confirming a dose, updating stock, adding a medicine, changing a schedule) shall require **explicit user confirmation** summarizing exact medicine name, quantity, and action before committing to the database.
  - Ambiguous medicine matches or low-confidence intents shall trigger a clarification question rather than guessing.
- **FR-VA-05:** The assistant shall maintain short-term multi-turn dialogue context (e.g., *"What about the evening one?"* after asking about morning doses).

### 4.9 Module 9: Custom ML/NLP Intent Model (`FR-ML`)
- **FR-ML-01:** NityaMed shall train and deploy a self-developed multilingual intent classifier supporting English, Kannada, Hindi, romanized text (e.g., Kanglish/Hinglish), code-switching, spelling variations, and simulated ASR noise.
- **FR-ML-02:** Model development shall benchmark at least: TF-IDF (word + char n-grams) + Logistic Regression / Linear SVM against FastText and/or a multilingual transformer baseline, deploying a compact high-performing model compatible with Render memory constraints.
- **FR-ML-03:** Training/validation/test splits shall group utterances by underlying intent template/paraphrase family to guarantee zero data leakage, keeping the medicine catalogue strictly separate from training utterances.
- **FR-ML-04:** The model shall support **Out-of-Scope (OOS)** rejection via confidence thresholding or an explicit `out_of_scope` class, evaluated via accuracy, precision, recall, F1, macro-F1, confusion matrix, and per-language metrics.

### 4.10 Module 10: Medicine Catalogue & Data Sources (`FR-MC`)
- **FR-MC-01:** NityaMed shall include a curated seed catalogue of common Indian medicines (mapping brand names, generic molecules, strengths, dosage forms, and strip sizes) paired with verified generic patient-education entries.
- **FR-MC-02:** System Administrators shall be able to add, verify, update, and deprecate catalogue entries with mandatory source and verification-date metadata.

### 4.11 Module 11: Adherence Analytics & Reports (`FR-AN`)
- **FR-AN-01:** Reports shall display counts and percentages over user-selected windows (7 days, 30 days, custom) for: `Taken on time`, `Taken late`, `Explicitly skipped`, and `Expired unconfirmed`.
- **FR-AN-02:** Metrics shall clearly document and separate `Confirmed Adherence Rate = (Taken on time + Taken late) / Total Scheduled` from `Unconfirmed Rate`, never conflating `Expired unconfirmed` with `Explicitly skipped`.
- **FR-AN-03:** The system shall highlight non-diagnostic irregular patterns (e.g., *"Evening doses delayed >3 times this week"*), strictly avoiding clinical interpretation.

---

## 5. Non-Functional Requirements (`NFR`)

- **NFR-01 (Usability & Accessibility):** Minimum `16–18sp` base body text, high-contrast colors (WCAG AA contrast target), large tap targets (`>=48x48 dp`), max 2 taps to confirm a due dose from the dashboard.
- **NFR-02 (Performance):** Local mobile dashboard & daily schedule load `<500 ms`; standard warm REST API responses `<300 ms` (excluding Render cold wake-up and external STT/LLM/TTS); custom ML intent inference `<100 ms`.
- **NFR-03 (Offline Reliability):** Core daily schedule viewing, dose confirmation, and local stock view must operate with **0% internet connectivity** on mobile and synchronize automatically when online.
- **NFR-04 (Maintainability):** FastAPI organized into clean domain modules (`auth`, `medicines`, `schedules`, `adherence`, `inventory`, `refill`, `notifications`, `assistant`, `analytics`, `admin`) with clear service/repository separation.
- **NFR-05 (Scalability & Portability):** Stateless REST APIs behind PostgreSQL allowing future extraction of the NLP or notification worker if scale grows.
- **NFR-06 (Reliability & Idempotency):** Zero duplicate stock deductions or duplicate dose records under network retries or concurrent offline sync replays.

---

## 6. Key Use Cases

| ID | Use Case | Primary Actor | Summary Flow |
| :--- | :--- | :--- | :--- |
| **UC-01** | Add Medicine & Schedule | Patient | Search catalogue (or custom entry) -> enter dose/intake, initial stock (strips/loose), schedule pattern -> save -> generate upcoming schedule & local alarms. |
| **UC-02** | Confirm Dose Offline | Patient | Local alarm fires (privacy-safe) -> patient taps `Taken` offline -> SQLite records event + UUID + deducts local confirmed stock -> syncs idempotently to PostgreSQL when online. |
| **UC-03** | Correct Accidental Confirmation | Patient | Patient opens today's history -> taps `Edit/Correct` -> changes `Taken` to `Skipped` -> audit log updated & stock deduction reversed. |
| **UC-04** | Physical Stock Reconciliation | Patient | Patient counts 8 tablets physically while app shows 10 -> enters `8` -> system creates `-2 RECONCILIATION` ledger transaction & recalculates refill date. |
| **UC-05** | Voice Purchase Update | Patient | User says *"I bought one more strip of Dolo"* (or Kannada/Hindi equivalent) -> STT -> ML intent `update_stock_purchase` + entity `Dolo, 1 strip` -> system asks *"Add 15 tablets to Dolo 650?"* -> user confirms -> stock updated. |
| **UC-06** | View Adherence Report | Patient | Selects 30-day view -> sees on-time, late, skipped, unconfirmed breakdown + medicine-wise chart and plain pattern notes. |

---

## 7. External Interface Requirements
1. **User Interface:** React Native (Expo) mobile UI (Android primary) + responsive Web UI (`react-native-web`) with language switcher (`EN / KN / HI`).
2. **Backend API Interface:** RESTful JSON over HTTPS (OpenAPI/Swagger documented via FastAPI), JWT Bearer auth, consistent error schema, and `X-Idempotency-Key` support on mutating sync/confirmation endpoints.
3. **External Speech & LLM Services:** HTTPS adapters for STT, TTS, and bounded LLM (swappable via provider interface).
4. **Device Hardware/OS Interfaces (Android):** Local Notification / Exact Alarm APIs, Microphone audio capture, Speaker TTS playback, Local biometric/PIN prompt, SQLite filesystem.

---

## 8. Data & System Constraints
- **Relational Integrity:** All core server entities (`users`, `patient_profiles`, `medicine_catalogue`, `medicine_education`, `personal_medicines`, `schedule_versions`, `dose_events`, `stock_transactions`, `notifications`, `audit_logs`, `conversation_states`) stored in PostgreSQL with strict foreign keys and soft-delete/archiving for historical integrity.
- **Append-Only Ledgers:** `stock_transactions` and `audit_logs` are append-only; corrections append compensating entries rather than deleting history.
- **Dataset Isolation:** NLP training/testing datasets remain strictly isolated from live patient records and the medicine catalogue schema.

---

## 9. Safety and Security Requirements (`SAF` & `SEC`)

- **SEC-01 (Password Security):** Passwords hashed using Argon2id (or bcrypt); never logged or returned in API responses.
- **SEC-02 (Authorization):** Every patient endpoint enforces strict `resource.user_id == current_user.id` ownership checks (preventing IDOR attacks).
- **SEC-03 (Transport & Storage Security):** Mandatory TLS/HTTPS in transit; encrypted database backups; secure token storage on device (`expo-secure-store`).
- **SEC-04 (Abuse Protection):** Rate limiting on auth, sync, and voice/LLM endpoints; strict Pydantic input validation.
- **SEC-05 (Privacy-Safe Notifications):** Lock-screen alerts display generic text (e.g., *"NityaMed reminder — tap to open"*) unless explicitly disabled by user.
- **SEC-06 (DPDP Act 2023 Alignment Notes):** Data minimization, explicit consent notice during registration, export/delete controls; formal legal compliance marked as requiring legal review prior to commercial/clinical deployment.
- **SAF-01 (LLM Containment):** The LLM has **zero direct DB access** and cannot execute raw queries or alter schedules/stock without structured backend validation + explicit user confirmation.
- **SAF-02 (No Medical Hallucination/Diagnosis):** Out-of-scope clinical queries (e.g., *"Should I stop taking my BP tablet?"*) are rejected with a safe message advising consultation with a qualified doctor/pharmacist.
- **SAF-03 (No Silent Stock/Dose Mutation):** No background job may mark doses `Taken` or silently overwrite `Confirmed Stock`.

---

## 10. Acceptance Criteria (MVP Release Gate)
1. **End-to-End Continuity:** Patient can register, add 3+ medicines (including strip + syrup + PRN), receive offline Android alarms, confirm/skip/partially take doses offline, and sync cleanly to PostgreSQL with zero duplicate deductions.
2. **Stock & Refill Accuracy:** 100% unit-test pass rate on schedule generation, confirmed vs. projected stock math, correction reversals, and deterministic refill depletion dates across all schedule types.
3. **ML Benchmark:** Custom intent classifier achieves documented evaluation metrics across English, Kannada, Hindi, romanized, and code-switched test sets with verified zero data leakage and working OOS rejection.
4. **Assistant Safety:** Automated test suite verifies all state-changing voice/text commands pause for confirmation and clinical advice prompts are safely refused.
5. **Security & Privacy:** Automated API tests confirm ownership isolation (no cross-user data leaks), password hashing, and lock-screen privacy masking.
