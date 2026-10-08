# Stage 8.45 — Persistent event timeline recovery and FIRMS feasibility pilot

**NOT_READY_FOR_PERSISTENCE_RECONSTRUCTION**

## Executive finding

The full 2024 standard-product candidate AOIs and existing full 2025 archive yielded at least one observation within 2 km in the label year for 17/24 candidates. A candidate-year first detection is established as PROBABLE for 10/24; 14/24 remain unresolved because no in-year point association was found. Coordinates are numerically available from the provenance ledger for 24/24 but are not independently verified against authoritative facility surveys.

## Candidate event evidence

The Stage 8.25 physical-event rows are source-level aggregates: each Persistent row lists detections in 2018, 2020, 2022, 2024, 2025, and 2026, while event_start/event_end span 2018-03-15 through 2026-03-15. That multi-year span is not a valid single event timeline. This audit read only each retained development candidate's label-year linked detection; it did not load 2026 linked detections. The legacy 2018-03-15 timestamp was not used as t0. A t0 here means the earliest relevant NOAA-20 SP detection in the candidate's assigned calendar year, under the project's <=2 km association rule.

## Archive and acquisition

NASA live data availability confirmed VIIRS_NOAA20_SP coverage from 2018-04-01 to 2026-06-30 and VIIRS_SNPP_SP from 2012-01-20 to 2026-06-30. The endpoint rejected VIIRS_NOAA21_SP as an invalid source. The Area API supports date-scoped 1–5 day AOI queries; 21 tight India candidate AOIs were queried across all 366 days in 2024. Existing 2025 full-India SP archive was searched for the 2025 cohort. Acquisition request details, bytes, latencies, response counts and file hashes are in acquisition_manifest.json.

The full-year pull generated 1495 network requests and 59 cached chunks; downloaded 973661 bytes in 1001.3s of processing (689.7s summed response latency). A separate 21-request event-day pilot is preserved in eventday_verification_manifest.json. Continuous local India-wide coverage remains 2024-10-01 through 2025-12-31 (457 days), augmented by candidate-specific 2024 AOIs. Dates before 2024-01-01 remain unobserved locally for those sites; 365-day pre-event coverage therefore depends on t0 and often requires additional targeted 2023 acquisition.

## Window feasibility

Using each probable first-in-year t0 and the seven-day guard, complete local date coverage windows are: 7d=11, 30d=10, 90d=4, 180d=0, 365d=0 of 24. No feature counts or recurrence statistics were computed. Where t0 is unresolved, all historical windows are unavailable.

The longest verified continuous span is 366 days for each acquired 2024 candidate AOI and 457 days in the India-wide local archive; these spans do not automatically overlap the required pre-t0 interval. The feasibility matrix gives exact per-candidate window start/end, coverage fraction, and missing intervals. The maximum causal history length is candidate-specific; candidates with early-year first detections can have no complete short windows, while later candidates may support 7–180 days if their start date falls after 2024-01-01 or 2024-10-01 respectively. No candidate can claim complete 365-day pre-event history from current data.

## Source diversity and split feasibility

There are 24 candidate incident IDs and 24 normalized facility names across 10 states and 3 regions. Candidate years: {"2024": 21, "2025": 3}. Sensor evidence among target-year nearby detections is recorded in each timeline row. Distinct incident IDs do not prove physical independence; nearby-source groups require expert facility review.

Inherited Persistent splits contain train/validation groups. Closest cross-split distance is 6.343 km; cross-split pairs under 5/10/50 km: 0/1/3. This is a feasibility audit only; no model split is finalized.

## Decision

The Persistent Expert is not feasible yet. A candidate-day satellite observation is not a trustworthy event onset, and complete causal histories cannot be inferred from the current partial archive. The next data foundation step is first to resolve event semantics/t0 for each physical source, then retrieve date-continuous standard-product AOIs only for candidates with defensible t0 values. No model features were created, no model was trained, and no blind-test artifact was accessed.

## Reproducibility and frozen artifacts

The analysis outputs are deterministically regenerated from the local archive and saved acquisition files; hashes are in stage8_45_hashes.json. The acquisition manifest preserves request timestamps and latency, which are intentionally outside deterministic analysis hashes. Frozen Stage 8.36 model and independent test manifest were not opened or modified; evaluation counter was not accessed in this stage.
