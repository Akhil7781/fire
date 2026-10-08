# Stage 8.44 — authoritative timeline and historical coverage audit

**NOT_READY_FOR_PERSISTENCE_MODELING**

## Decision

No. The historical FIRMS evidence is not sufficient to distinguish true zero recurrence from unavailable history, and the retained Persistent event t0 values remain unresolved.

## Cohort and timeline

The Stage 8.43 ledger contains 99 retained label-confident development candidates (24 Persistent). The Persistent timelines record provenance and coordinates but set authoritative t0 to unresolved; metadata dates are not promoted to observed event time.

All 24 Persistent entries lack an independently validated first/last event detection and duration. Stage 8.43 states their t0 is inherited metadata or blank, and its report identifies fixed 2018-03-15 metadata in the canonical cohort. The supplied raw archive does not establish a verified event-linked raw timeline.

## Archive coverage

Local sequential standard-product coverage is 2024-10-01 through 2025-12-31 for the India bbox (457 days). The 90 pre-2026 event-window CSVs cataloged in Stage 8.43 are not treated as continuous coverage.

Candidate/window coverage rows: 495. Complete local window rows: 54; partial/zero-coverage rows among date-anchored candidates: 321; Persistent rows with unresolved anchors: 120 (5 each for 24 events). Counts/features are NaN and unavailable when coverage or authoritative t0 is missing; no zero counts are substituted.

For the 24 Persistent candidates, required start/end dates and missing-day counts are intentionally blank because their authoritative t0 is unresolved. The old fixed 2018-03-15 date is not used to fabricate a required history window. For the other 75 candidates, coverage dates use inherited event metadata only as provisional audit anchors and are not treated as event-time validation.

The archive manifest records source hashes. Original request URLs and download timestamps were not embedded in available files. NASA historical archive availability was not acquired in this stage; theoretical archive availability is not counted as local observed coverage.

## Causality and feature construction

The established Stage 8.30 association semantics use a ±5 km candidate search, a 2 km primary historical sequence/statistics neighborhood, and a t0−7-day ongoing-event guard. Because t0 is unresolved and archive coverage is incomplete, no detection association or causal feature values are emitted. All requested feature columns are present as unavailable (NaN); the feature generator reads labels only as output metadata and does not branch on them.

## Source diversity and split audit

Persistent candidates represent 24 distinct incident/source IDs across 10 states and 3 macro-regions; label years: {"2024": 21, "2025": 3}. Facility/source labels remain in the timeline. There are no sensor-attributed event timelines that meet the evidence standard, so reconstructed-timeline sensor distribution is unavailable.

A proposed development split manifest groups events sharing an incident identifier or lying within 50 km, preserving those groups in one partition. Its connected-group plan yields zero cross-split pairs under 5, 10, and 50 km by construction. This is a proposed split grouping, not a validation that facility identity is complete; assignments retain each group’s modal inherited split.

## Quality gates

Failed: evidence-based Persistent t0; complete local history; historical zero-vs-unobserved distinction; causal feature reconstruction; independently verified physical-source grouping. Passed: no generated Stage 8.35 rows restored; missing coverage not encoded as zero; deterministic repeated artifact generation.

Reconstruction was run twice from the same development-only ledger and local coverage files; output bytes matched exactly. All 3069 history-dependent feature values remain unavailable (100%). No model was trained and no blind evaluator was run.

## Generated artifact SHA-256

- `coverage_audit.csv`: `ee3be11a7f4b0c97be591fa3a0aa400fcdef339babf917b56569f49a3d247a67`
- `development_split_manifest.json`: `3c1d041b52fa0a2acf83dfa34ba3080cc420c994745b77d8641d3e7bdcac536c`
- `historical_firms_index_manifest.json`: `9a874ccf74e51cbcc10246cacf43f2987cdf7a1b7e5faba71c6dad654a94d741`
- `persistent_event_timeline.csv`: `286b63f4b073e0a44e3ae20aefc37baceb33546906f14e91d1827964af248f04`
- `persistent_feature_reconstruction.parquet`: `1bd733ac4ee952ea1f99533366fba2c80045ebb80b372264d64ad8f6af4f7057`
- `stage8_44_hashes.json`: `7d0f6e885373630e1a0977e0aea95f3e2e58e4d99a182febd78e638f8839a52f`
- `stage8_44_report.md`: `a80616cd95ca85ee2c411f21e0ea2a26f28ea7e9ccff81513393c63c7c46e517`

No Stage 8.36 checkpoint, independent test manifest, or evaluation counter was read or modified.
