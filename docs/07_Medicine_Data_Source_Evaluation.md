# Medicine Catalogue & Data Source Evaluation (Module 10): NityaMed

**Project:** NityaMed — Medicine Continuity Management System (MCMS)  
**Purpose:** Evaluate real-world Indian and international medicine information sources honestly before designing the NityaMed seed catalogue and fallback strategy.

---

## 1. Key Reality Check for India
Unlike some countries with unified consumer-facing open drug APIs, **India currently has no single free, official, public REST API** that simultaneously provides:
1. All Indian retail brand names + strip/pack sizes, **and**
2. Verified active ingredients, **and**
3. Plain-language, patient-friendly educational descriptions (uses, mechanism, side effects, precautions).

Therefore, NityaMed must **never assume** a single API covers everything out of the box. Instead, we evaluate each source category realistically and combine strengths responsibly.

---

## 2. Comparative Evaluation of Medicine Data Sources

| Source Category | Examples | Indian Brand & Strip Coverage | Patient Education Quality | API Availability | Licensing / Usage Notes | Suitability for NityaMed MVP |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Indian Government & Official Registries** | **CDSCO** (Central Drugs Standard Control Organization), **IPC** (Indian Pharmacopoeia), **PMBJP / Jan Aushadhi** product lists, **NFI** (National Formulary of India) | High for approved generics & Jan Aushadhi generics; partial for private retail brands/strip sizes. | Clinical/formulary style (NFI) rather than plain elderly-friendly patient prose; Jan Aushadhi lists focus on generic name, pack size, and MRP. | **No standard consumer REST API.** Data is published mainly as PDFs, spreadsheets, or web tables. | Publicly published government regulatory/formulary references; must attribute source and publication/revision date. | **High for Indian generic & pack-size reference** when manually curated into a seed JSON/CSV. |
| **International Open Government Databases** | **U.S. NLM RxNorm / DailyMed**, **OpenFDA Drug Labeling**, **MedlinePlus** | **None** for Indian brand names (e.g., *Dolo 650*, *Glycomet*) or Indian strip counts. | **High.** Structured FDA labels (DailyMed/OpenFDA) and plain-language patient guides (MedlinePlus) organized by generic molecule. | **Yes — documented public REST APIs & bulk XML/JSON** (OpenFDA, RxNorm, DailyMed). | Open U.S. government public-domain data (check individual source terms and attribution guidelines). | **High for generic-molecule educational metadata** (uses, mechanism, side effects, precautions) mapped to Indian generics. |
| **International Terminology / Classification** | **WHO ATC Classification**, **WHO Model List of Essential Medicines** | Generic INN names & therapeutic categories only. | Category & essential medicine classification only (no patient leaflets). | Downloadable classification tables / web lookup. | WHO attribution requirements apply for public/academic reuse. | **Medium** — useful for standardized `category` taxonomy. |
| **Commercial Indian Pharmacy Websites / Unofficial Datasets** | Online retail pharmacy portals or unverified scraped Kaggle/GitHub CSVs | Very high Indian brand coverage. | Often marketing-mixed or inconsistent; scraped files frequently lack verification dates and provenance. | **No official public API** for academic free use; scraping violates Terms of Service. | High copyright/ToS risk; unverified scraped data fails healthcare safety standards (`Module 3`). | **Rejected as primary source.** Must not scrape proprietary portals or trust unverified crowdsourced dumps. |

---

## 3. Recommended NityaMed Catalogue Architecture (Two-Tier Verified Model)

To satisfy **Module 2** (Indian brands, strengths, dosage forms, strips/loose tablets), **Module 3** (verified, source-attributed patient education), and **Module 10** (reliable sources + custom fallback), NityaMed uses a **Curated Two-Tier Seed Catalogue + Custom Entry Fallback**:

### Tier 1: Curated Indian Brand-to-Generic Mapping (`medicine_catalogue`)
- **Initial MVP Scope:** Curate a verified seed dataset of **~200–500 high-frequency Indian chronic and acute medications** (e.g., antihypertensives, antidiabetics, lipid-lowering drugs, thyroid, asthma inhalers, common analgesics/antacids/syrups/drops).
- **Verified Fields:** Brand name, generic INN name(s), strength, dosage form (`tablet`, `capsule`, `syrup`, `inhaler`, `drops`, `injection`), standard Indian pack size (e.g., `10` or `15` tablets/strip), and manufacturer where verified.
- **Sourcing:** Cross-checked against official Indian generic/formulary references (Jan Aushadhi / NFI / CDSCO approved lists) and physical/official manufacturer pack standards.

### Tier 2: Generic-Level Verified Patient Education (`medicine_education`)
- Linked by `catalogue_id` (and shared across equivalent brands of the same generic molecule/form).
- **Content Standard:** Plain-language summaries of:
  1. Common uses
  2. Mechanism of action (how it works)
  3. Medicine category
  4. Common side effects
  5. Important precautions
- **Provenance Requirement (Mandatory):** Every record stores `source_name`, `source_url`, and `verified_at` date, rendered visibly in the UI.
- **Multilingual Handling:** Pre-verified translations or bounded LLM simplification/translation of the verified English record—**never** generating new medical claims.

### Tier 3: Custom Medicine Fallback (`is_custom = true`)
- If a patient's prescribed medicine is not in the curated seed catalogue:
  1. The user can add it manually with full scheduling, adherence, inventory, and refill support.
  2. The Medicine Details screen displays: *"Custom medicine entry — verified educational reference unavailable. Please consult your prescription or pharmacist."*
  3. An Admin review queue (optional enhancement) allows System Administrators to add verified catalogue entries over time.

---

## 4. Safety & Separation Rules
1. **Strict Separation from NLP Training Data:** The medicine catalogue (`medicine_catalogue`) is used at runtime for entity resolution/lookup, **never** baked as memorized text templates into the custom ML intent classifier's train/test splits (`FR-ML-03`).
2. **No Runtime Scraping or Unverified Fallback:** If a medicine is missing from the verified catalogue, NityaMed never queries arbitrary web search results or asks an LLM to invent side effects/uses.
3. **Update Governance:** Every seed catalogue update passes a validation script verifying non-empty `source_name`, valid `verified_at` date, valid `dosage_form`, and zero duplicate brand+strength+form rows before seeding PostgreSQL.
