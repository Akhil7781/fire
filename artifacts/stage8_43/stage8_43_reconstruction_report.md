# Stage 8.43 — Persistent development cohort reconstruction audit

**Status: NOT_READY_FOR_MODELING**

No persistence feature table was generated. No model was trained, no features were selected, and no blind evaluation was run.

## A. Eligible development events

The authoritative label cohort is the Stage 8.34 trusted development set (`N=131`), joined only to Stage 8.25 event/label metadata using those development event IDs. Label-confident candidate events with documented provenance and coordinates: `99`. The ledger is `artifacts/stage8_43/eligible_event_provenance.csv`; it contains labels/coordinates/provenance only, no model features. The Persistent subset is `24` events. Stage 8.35's 18 generated Persistent rows were excluded. Persistent `t0` is intentionally blank: Stage 8.25 `event_start` is fixed at 2018-03-15 for all 42 Persistent rows despite label years 2024/2025. Stage 8.30 derives Persistent `t0` from the first observation in the assigned year, and that raw-observation link is not available here.

## B. Persistent vs Non-Persistent distribution

Label-confident candidate counts: `{"Agricultural Fire": 25, "Forest Fire": 25, "Industrial Fire": 25, "Other Thermal Source/Persistent Non-Biomass Thermal Source": 24}`. Persistent label audit totals: `{"Other Thermal Source/Persistent Non-Biomass Thermal Source": 42}`. Confident Persistent candidates by year: `{"2024": 21, "2025": 3}`. By macro-region: `{"Central_East": 17, "North": 4, "South": 3}`. All 42 Persistent labels in the canonical 131-event cohort have `CONFIRMED` tier/status in the label manifest; the Stage 8.34 quality flags further classify them as `{"2024:LABEL_AMBIGUOUS": 11, "2024:LABEL_CONFIDENT": 21, "2024:LABEL_POTENTIAL_DUPLICATE": 4, "2025:LABEL_AMBIGUOUS": 1, "2025:LABEL_CONFIDENT": 3, "2025:LABEL_POTENTIAL_DUPLICATE": 2}`. Ambiguous/potential-duplicate events are not in the candidate ledger.

## C. Raw FIRMS sources used

Raw observations were **not** used to compute features. Inventory found 73 five-day raw FIRMS chunks covering 2025 and 90 pre-2026 event-window CSVs. The older event-window extracts are not continuous source coverage across dates and geography. The 2025 archive does not provide the missing pre-2025 intervals required for prior-year history. Per-file hashes and coverage categories are in `artifacts/stage8_43/raw_source_inventory.json`.

## D. Feature provenance

No feature values were emitted. Raw source observations and deterministic transformations would be the only allowed feature lineage. Existing historical radius semantics in Stage 8.30 use a ±5 km candidate search and a 2 km primary historical sequence/statistics neighborhood, with a `t0 - 7 day` guard to exclude the ongoing event. That is the established criterion and should be reused if its input archive becomes complete. No new arbitrary radius was used here. Stage 8.35 fixed values for the 18 generated Persistent events remain disallowed.

## E. Causality verification

No feature table means no feature timestamp assertions can be certified. The existing helper's cutoff tests are not evidence that this rebuild was performed. Persistent `t0` is not established, and the source-coverage limitation blocks causal window-completeness assertions.

## F. Spatial separation

`closest_development_event_pairs.csv` contains the 50 closest pairs among label-confident candidates, their geodesic distance, current split, and spatial-component comparison. Same-incident ID groups among confident Persistent candidates: 0; such groups crossing the existing temporal split: 0. Cross-split label-confident event pairs within 5 km: 2. Both cross-split pairs share an existing spatial component: the 2019/2025 Similipal forest pair (1.29 km) and the 2022/2025 Bandhavgarh forest pair (3.98 km). This is direct evidence the inherited temporal split does not isolate spatial components. The nearest Persistent pair in the table is PER_SRC_09/PER_SRC_08 (6.34 km; train/validation; two distinct incident IDs in the Jharia coalfield complex), which requires facility-group review. The nearest-pair screen does not substitute for a spatial validation fold audit.

## G. Temporal separation

The inherited temporal split is train through 2024 and validation in 2025. Persistent confident labels occur in years `{"2024": 21, "2025": 3}`. Repeated `incident_id` groups crossing train/validation are 0. A season cannot be assigned to Persistent examples from a verified alert timestamp; their stored event-start metadata is invalid for seasonality.

## H. Source diversity

Persistent source labels are documented by the event provenance ledger; the candidate set contains 24 unique incident/source IDs across 10 states and `3` macro-regions. Label-source categories and subtypes available in artifacts are preserved in the ledger. Site-level complexes with nearby distinct source IDs remain a potential grouping concern.

## I. Missing-history statistics

All recurrence/thermal/spatial history fields are uncomputed and unavailable for all 99 ledger candidates; **zero is not substituted for missing history**. Persistent alert `t0` is unavailable from verified observation records. There is no event-level verified coverage map for pre-2025 FIRMS. This prevents distinguishing true zero detections from periods not downloaded.

## J. Invalid/excluded events and reasons

- 18 Stage 8.35 additions: excluded; source code generates them from six manually specified facilities at fixed March 15 timestamps and assigns fixed thermal values rather than linking each alert to a raw detection record.
- 18 of the canonical 42 Persistent events: excluded from label-eligible candidates due to Stage 8.34 `LABEL_AMBIGUOUS` or `LABEL_POTENTIAL_DUPLICATE` status.
- Persistent `t0` for all 24 confident candidates: not accepted from the fixed 2018-03-15 event-start metadata; must be rebuilt from observed detections in the label year.
- All label-confident candidates: retained in the provenance ledger, but feature reconstruction blocked because historical coverage is incomplete before 2025.

Exact canonical exclusions and confidence reasons, plus every Stage 8.35 generated Persistent event ID and reason, are listed in `artifacts/stage8_43/excluded_events.csv` (32 canonical exclusions and 18 generated Persistent exclusions).

## K. Dataset path and hash

`data/interim/persistence_expert_development.parquet` was **not created**; dataset hash is null because there is no defensible feature table to hash. `persistence_feature_manifest.json` records `dataset_created=false`, the proposed feature schema hash, source file hashes, event counts, software versions, and exact blockers.

## L. Verification tests

- Development cohort row count and unique IDs: passed (`131`).
- Label and physical-event metadata joined exactly to the trusted development IDs: passed (`131/131`).
- No Stage 8.35 additions included: passed by using the frozen Stage 8.34 development cohort only.
- No test manifest/evaluator read or invoked: passed by execution procedure.
- Reconstruction twice / feature determinism: not applicable; no feature reconstruction was allowed with incomplete coverage.
- Blind checkpoint SHA-256 and evaluation counter preservation are verified in the execution record.

## M. Model-training readiness

**NOT_READY_FOR_MODELING**. Required next evidence: a continuous, attributable FIRMS archive covering the full pre-alert windows (including 2012–2024) for the candidate locations; source-row provenance and coverage intervals; explicit physical-site grouping for nearby facilities; and spatial/temporal folds that keep each physical site in one partition. Once available, rebuild features from raw rows and assert every observation timestamp is no later than `t0` (with the existing 7-day ongoing-event exclusion if retained).
