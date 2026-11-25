# Project Synopsis: NityaMed (Medicine Continuity Management System)

**Project Name:** NityaMed — Medicine Continuity Management System (MCMS)  
**Target Users:** Patients (Elderly, Chronic-Care, Multi-Medicine, Regional-Language Users in India)  
**Development Mode:** Solo Academic Engineering Project  

---

## 1. Project Title
**NityaMed: A Multilingual, Offline-Resilient Medicine Continuity Management System with Inventory Tracking and Hybrid AI Voice Assistance**

---

## 2. Introduction
Long-term and multi-medicine therapies require consistent daily execution, accurate timing, and uninterrupted medicine availability. However, many patients—particularly elderly individuals, people managing chronic conditions, and users comfortable in regional Indian languages—struggle with complex schedules, fragmented tracking, and unexpected medicine stock-outs. Conventional reminder applications typically act as simple alarms: they do not track confirmed versus unconfirmed doses, separate prescribed doses from available inventory, handle partial strips or loose tablets, or provide accessible multilingual voice interaction.

**NityaMed (MCMS)** is an intelligent, patient-centric healthcare-support application designed to help individuals maintain continuity in their prescribed medication routines. It integrates deterministic medication scheduling, strict adherence state tracking, dual-balance inventory and refill prediction, verified non-diagnostic medicine education, offline-capable local notifications, and a safety-guarded multilingual hybrid AI voice assistant supporting **English, Kannada, and Hindi**.

---

## 3. Problem Statement
Patients managing regular or multi-drug regimens commonly face seven interrelated challenges:
1. **Missed or Forgotten Doses:** Busy routines, memory decline, or complex timings lead to skipped doses.
2. **Incorrect Administration Timing:** Taking medicines outside intended intervals reduces routine consistency.
3. **Lack of Consumption Tracking:** Patients cannot reliably verify whether an earlier dose was actually taken, taken late, or skipped.
4. **Unexpected Medicine Shortages:** Without linking confirmed consumption to remaining stock, patients run out of essential medicines unexpectedly.
5. **Limited Understanding of Prescribed Medicines:** Patients often lack plain-language, trustworthy information about what a medicine is commonly used for, how it works, common side effects, and precautions.
6. **Multi-Regimen Complexity:** Managing multiple medicines with differing schedules (daily, alternate-day, weekly, varying-dose, fixed-course, and as-needed) is error-prone.
7. **Accessibility and Language Barriers:** English-only, cluttered interfaces and unreliable internet connectivity exclude elderly and regional-language users.

---

## 4. Objectives

### Primary Objective
To design, implement, and rigorously test **NityaMed**, a reliable, secure, offline-resilient, and multilingual Medicine Continuity Management System that helps patients follow their medication routines, monitor adherence accurately, manage inventory, and prevent unexpected shortages.

### Specific Objectives
1. Build an accessible, large-text cross-platform client (Android mobile app + Web companion) tailored for elderly and non-technical users.
2. Implement deterministic scheduling and strict dose-confirmation workflows that never falsely assume an unconfirmed dose was taken or missed.
3. Develop a transaction-based inventory ledger separating **Confirmed Stock Balance** from **Projected Stock Balance**, supporting full strips, partial strips, loose tablets, and physical reconciliation.
4. Implement deterministic refill prediction calculations across varied schedule patterns while avoiding false alerts for completed or as-needed courses.
5. Provide source-attributed, non-diagnostic medicine education backed by a curated medicine catalogue and custom-entry fallback.
6. Build and benchmark a custom multilingual ML/NLP intent classification model (English, Kannada, Hindi, including romanized and code-switched inputs) without train-test data leakage.
7. Integrate the custom intent model into a safety-guarded hybrid voice assistant (`STT -> Rules/ML -> Bounded LLM -> Validated Backend API -> TTS`) with explicit confirmation for state-changing actions.
8. Ensure offline resilience, idempotent synchronization, privacy-safe lock-screen notifications, and security aligned with sound data-minimization principles.

---

## 5. Existing System and Limitations

| Limitation in Existing Tools | Impact on Patients |
| :--- | :--- |
| **Simple Alarm Apps Only** | Fire notifications without tracking confirmed vs. late vs. unconfirmed doses or preserving schedule version history. |
| **No Stock-to-Consumption Linkage** | Do not maintain separate confirmed and projected stock balances or account for Indian strip/loose-tablet purchasing patterns. |
| **Auto-Assumption Errors** | Some trackers automatically mark unanswered reminders as "missed" or deduct stock automatically, corrupting adherence and inventory records. |
| **Poor Offline & OEM Reliability** | Cloud-only web/mobile apps fail when internet is intermittent or when Android battery optimization kills background tasks. |
| **English-Centric & Complex UIs** | High cognitive load for elderly users and lack of Kannada/Hindi voice support with romanized/code-switched understanding. |
| **Unbounded AI Risks** | Generic chatbots may hallucinate dosages, infer diagnoses, or recommend medication changes without safety boundaries. |

---

## 6. Proposed System
NityaMed addresses these gaps through a **safety-first, deterministic-core + bounded-AI** architecture:
- **Deterministic Core:** Scheduling, dose state transitions, stock ledger accounting, and refill depletion math are strictly rule-based and transactional—never left to probabilistic AI.
- **Dual Stock & Strict Dose Integrity:** Stock is deducted only upon explicit dose confirmation (or manual adjustment/expiry logging). Unanswered doses transition to `Expired unconfirmed` rather than falsely becoming `Taken` or automatically `Missed`.
- **Hybrid Multilingual Voice Assistant:** Combines rule-based matching, a custom-trained ML/NLP intent classifier, and a strictly bounded LLM (used only for disambiguation and simplifying/translating verified text) behind backend validation and explicit user confirmation.
- **Verified Non-Diagnostic Education:** Displays medicine purpose, mechanism, category, side effects, and precautions with source attribution and update dates. It never diagnoses conditions or advises starting, stopping, or altering prescriptions.
- **Explicit System Boundaries:** No doctor/healthcare-provider dashboards or portals, no handwritten prescription OCR in MVP, and Caregiver functionality deferred to Phase 2.

---

## 7. Proposed Methodology
The project follows an iterative, modular software engineering and ML development lifecycle:
1. **Requirements & Architecture Phase:** Finalize SRS, initial architecture, relational database schema, API contracts, and system diagrams.
2. **Backend & Data Foundation:** Implement the FastAPI modular monolith, PostgreSQL schema, authentication, and ownership-based authorization.
3. **Core Continuity Modules:** Build Medicine Catalogue + Custom Entry, Schedule Versioning, Dose State Engine, Transaction-Led Inventory, and Deterministic Refill Prediction.
4. **Offline & Notification Layer:** Implement SQLite local persistence, idempotent sync endpoints, and Android local scheduled notifications with privacy-safe lock-screen summaries.
5. **ML/NLP Dataset & Model Pipeline:** Construct a leak-free multilingual dataset (English, Kannada, Hindi, romanized, code-switched, noisy ASR variants), train and benchmark baseline-to-advanced intent classifiers, and implement out-of-scope rejection.
6. **Hybrid Voice Integration:** Connect STT/TTS services, dialogue state management, safety checks, and backend APIs.
7. **Analytics, Testing & Hardening:** Build adherence analytics, execute unit/integration/offline-sync/security/multilingual/UAT tests, and deploy on Render + managed PostgreSQL.

---

## 8. Main Modules
1. **User Management:** Email + Password authentication, optional local 4-digit PIN/biometric unlock, language (`en`/`kn`/`hi`) & notification preferences, data export, and account deletion.
2. **Medicine Management:** Catalogue search and custom medicine entry; brand/generic names, strength, dosage form (tablets, capsules, syrups, inhalers, drops, injections), strip/loose quantities, separating prescribed dose from stock balance.
3. **Medicine Information & Education:** Source-attributed, non-diagnostic reference information with verification/update dates.
4. **Medication Adherence Management:** Multi-pattern schedules, daily agenda, dose confirmations (`Pending`, `Snoozed`, `Taken on time`, `Taken late`, `Explicitly skipped`, `Expired unconfirmed`, `Partially taken`), accidental confirmation correction, and history preservation.
5. **Medicine Inventory Management:** Initial stock, confirmed-dose deductions, purchases, manual adjustments, expired/damaged logs, physical reconciliation, and separate confirmed vs. projected balances.
6. **Refill Prediction & Alerts:** Deterministic remaining-days and depletion-date calculation, configurable thresholds, and exclusion of completed/as-needed courses.
7. **Notification Management:** Primary local scheduled alarms on Android, push fallback, snoozing, duplicate prevention, reboot/battery-optimization guidance, and privacy-safe lock-screen text.
8. **Hybrid AI Voice Assistant:** Multilingual voice/text pipeline with dialogue state, safety guardrails, and mandatory confirmation for mutations.
9. **Custom ML/NLP Intent Model:** Independently trained and evaluated intent classifier covering accuracy, precision, recall, F1, macro-F1, confusion matrix, per-language breakdown, and out-of-scope rejection.
10. **Medicine Catalogue & Data Sources:** Curated seed catalogue derived from verified reference sources mapped to generic patient education, plus custom fallback.
11. **Adherence Analytics & Reports:** Transparent formulas for on-time, late, skipped, and unconfirmed metrics, per-medicine history, and irregular-pattern detection without clinical diagnosis.

---

## 9. Technologies Proposed

| Layer | Proposed Technology | Justification |
| :--- | :--- | :--- |
| **Mobile & Web Frontend** | **React Native (Expo)** + TypeScript + `react-native-web` | Single React codebase delivering a real native Android app (for alarms, SQLite, mic) and a responsive Web companion. |
| **Local Offline Storage** | **SQLite (`expo-sqlite`)** | Reliable structured offline storage and queued sync events on mobile devices. |
| **Backend API & Logic** | **Python (FastAPI)** — Modular Monolith | High performance, strict Pydantic validation, and unified Python runtime shared with the ML/NLP module. |
| **Primary Database** | **PostgreSQL** (Neon / Supabase) | ACID transactions, foreign-key integrity, and persistent managed hosting for stock ledgers and schedule versions. |
| **Authentication** | **Email + Password** (Argon2/bcrypt + JWT) + Local PIN | Zero SMS cost, reliable academic deployment, and low daily friction for elderly users. |
| **ML/NLP Modeling** | **Python (`scikit-learn`, FastText / Multilingual Transformers)** | Enables offline benchmarking of baselines vs. transformers while deploying a compact, fast model suitable for Render container limits. |
| **Voice & Language AI** | Existing Cloud **STT / TTS** + **Bounded LLM API** | Avoids training speech models from scratch; enforces strict backend-validated action boundaries. |
| **Hosting** | **Render** (Backend Web Service + Web Static Site) & **Expo EAS** (Android APK) | Cost-effective academic deployment with HTTPS and automated builds. |

---

## 10. Scope

### In Scope (MVP)
- **User Roles:** Patient (primary) and System Administrator (technical/catalogue management only).
- **Platforms:** Android mobile app (full offline + local alarms + voice) and Web companion (connected access).
- **Languages:** English, Kannada, and Hindi (native script + romanized/code-switched NLU support).
- **Features:** All 11 core modules implemented with deterministic continuity logic, curated medicine seed dataset + custom entry, custom ML intent model, and adherence reporting.

### Out of Scope / Future Enhancements (Phase 2)
- **Caregiver Module:** Family-member linking, consent permissions, and escalation alerts.
- **Handwritten Prescription OCR / Barcode Scanning.**
- **Additional Indian Regional Languages** beyond English, Kannada, and Hindi.
- **ML-Based Adherence Forecasting** (deferred until sufficient real longitudinal data exists).
- **Doctor / Healthcare-Provider Portals or Clinical Decision Support** (permanently excluded by design).

---

## 11. Expected Outcomes
1. A functional, installable Android application (**NityaMed**) and Web companion usable by elderly and multilingual patients.
2. Accurate, audit-logged adherence and dual-balance stock tracking free from duplicate-deduction or auto-assumption bugs.
3. A documented, reproducible multilingual NLP intent classification benchmark report free of data leakage.
4. Comprehensive engineering documentation (SRS, Architecture, DB Schema, Testing Strategy) suitable for academic evaluation and real-world demonstration.

---

## 12. Conclusion
**NityaMed (MCMS)** bridges the gap between simple reminder alarms and genuine medication continuity support. By combining deterministic scheduling and ledger-based inventory accounting with accessible mobile UX, offline resilience, and a safety-bounded multilingual voice assistant, NityaMed offers a practical, ethical, and technically rigorous solution to everyday medication management challenges.

---

## 13. References
1. Government of India, *The Digital Personal Data Protection Act, 2023* (Ministry of Law and Justice).
2. World Health Organization (WHO), *Adherence to Long-Term Therapies: Evidence for Action* (conceptual framework on medication adherence).
3. Official Technical Documentation: FastAPI (Python), PostgreSQL, Expo / React Native, SQLite, scikit-learn, and Render Platform Docs.
4. Public Medical Reference Frameworks evaluated for Module 10 (e.g., Central Drugs Standard Control Organization [CDSCO] / Indian Pharmacopoeia references, MedlinePlus / DailyMed / OpenFDA — to be formally benchmarked during the Medicine Data Source Evaluation).
