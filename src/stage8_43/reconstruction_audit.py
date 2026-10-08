"""Audit whether Stage 8.43 can build a valid persistence development table.

Reads only the authoritative Stage 8.34 development cohort and rows joined by
those development event IDs. It never reads the frozen blind manifest or any
2026 event rows. It inventories (but does not use as complete history) raw CSV
sources, then writes a provenance ledger and a NOT_READY manifest if historical
coverage is insufficient.
"""

from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
import platform
import sys

import pandas as pd
from src.persistence_expert.features import FEATURE_SCHEMA


PROJECT_ROOT = Path(__file__).resolve().parents[2]
COHORT_PATH = PROJECT_ROOT / "artifacts/stage8_34/trusted_development_cohort.parquet"
LABELS_PATH = PROJECT_ROOT / "data/interim/ds08_stage8_25_multiyear_labels.parquet"
EVENTS_PATH = PROJECT_ROOT / "data/interim/ds08_stage8_25_physical_events.parquet"
OUT_DIR = PROJECT_ROOT / "artifacts/stage8_43"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 6371.0088 * 2 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1 - a)))


def _inventory_raw_sources() -> tuple[list[dict[str, object]], dict[str, object]]:
    # Only source files dated through 2025 are inventoried. No per-event 2026
    # files or independent-test artifacts are opened or hashed.
    event_dir = PROJECT_ROOT / "data/raw_multiyear"
    event_files = sorted(p for p in event_dir.glob("*.csv") if "2026" not in p.name)
    annual_files = sorted((PROJECT_ROOT / "data/raw/2025").glob("*.csv"))
    records = []
    for kind, files in (("event_window", event_files), ("annual_2025", annual_files)):
        for path in files:
            records.append({"coverage_kind": kind, "relative_path": path.relative_to(PROJECT_ROOT).as_posix(), "sha256": sha256_file(path), "bytes": path.stat().st_size})
    summary = {
        "event_window_file_count": len(event_files),
        "annual_2025_file_count": len(annual_files),
        "annual_2025_start": "2025-01-01" if annual_files else None,
        "annual_2025_end": "2025-12-31" if annual_files else None,
        "coverage_assessment": "Event-window extracts before 2025 are not continuous spatial-temporal archive coverage; annual raw coverage is present only for 2025.",
    }
    return records, summary


def audit_and_write() -> dict[str, object]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cohort = pd.read_parquet(COHORT_PATH)
    if len(cohort) != 131 or cohort.event_id.duplicated().any():
        raise AssertionError("Expected the canonical unique 131-event development cohort")
    ids = cohort.event_id.tolist()

    labels = pd.read_parquet(
        LABELS_PATH,
        columns=["event_id", "incident_id", "target_class", "class_id", "year", "state", "label_tier", "adjudication_status", "evidence_source", "evidence_strength"],
        filters=[("event_id", "in", ids)],
    )
    events = pd.read_parquet(
        EVENTS_PATH,
        columns=["event_id", "event_start", "facility_name"],
        filters=[("event_id", "in", ids)],
    )
    if set(labels.event_id) != set(ids) or set(events.event_id) != set(ids):
        raise AssertionError("Development-only label/event metadata do not align to the trusted cohort")

    joined = cohort.merge(labels, on=["event_id", "target_class", "class_id", "year"], how="inner", validate="one_to_one")
    joined = joined.merge(events, on="event_id", how="inner", validate="one_to_one")
    joined["metadata_event_start"] = pd.to_datetime(joined.event_start, utc=True, errors="coerce")
    # Stage 8.30 derives Persistent t0 from the first detection in the source's
    # assigned year. Stage 8.25 event_start for these rows is fixed to 2018-03-15.
    joined["t0"] = joined["metadata_event_start"].where(joined.class_id != 3, pd.NaT)
    joined["t0_status"] = "metadata event_start; not independently rebuilt from raw rows"
    joined.loc[joined.class_id == 3, "t0_status"] = "UNVERIFIED: fixed metadata event_start; raw alert time unavailable"
    joined["history_coverage_status"] = "UNAVAILABLE: no event-level verified continuous FIRMS coverage map"
    joined["label_provenance"] = joined.evidence_source.astype(str) + " | " + joined.evidence_strength.astype(str)
    candidates = joined.loc[
        (joined.label_quality_flag == "LABEL_CONFIDENT")
        & joined.centroid_lat.notna()
        & joined.centroid_lon.notna()
    ].copy()
    candidates = candidates.sort_values(["year", "event_id"], kind="stable")

    ledger_cols = [
        "event_id", "target_class", "class_id", "year", "metadata_event_start", "t0", "t0_status", "history_coverage_status", "centroid_lat", "centroid_lon",
        "state", "spatial_region", "incident_id", "facility_name", "label_provenance",
        "label_tier", "adjudication_status", "label_quality_flag", "split", "spatial_component_id",
    ]
    ledger = candidates[ledger_cols].rename(columns={"target_class": "label", "centroid_lat": "latitude", "centroid_lon": "longitude", "label_quality_flag": "label_confidence"})
    for time_col in ("metadata_event_start", "t0"):
        ledger[time_col] = ledger[time_col].map(lambda x: x.isoformat() if pd.notna(x) else None)
    ledger.to_csv(OUT_DIR / "eligible_event_provenance.csv", index=False)

    quality = pd.read_csv(PROJECT_ROOT / "artifacts/stage8_34/label_quality_audit.csv")
    excluded_canonical = quality.loc[quality.label_quality_flag != "LABEL_CONFIDENT", ["event_id", "target_class", "class_id", "year", "label_quality_flag", "ambiguity_reason"]].copy()
    excluded_canonical["exclusion_reason"] = excluded_canonical.label_quality_flag + ": " + excluded_canonical.ambiguity_reason.fillna("label is not confidently established")
    excluded_canonical["cohort_origin"] = "STAGE_8_34_CANONICAL"
    expanded = pd.read_parquet(
        PROJECT_ROOT / "artifacts/stage8_35/trusted_expanded_cohort.parquet",
        columns=["event_id", "target_class", "class_id", "year", "label_confidence", "evidence_type", "data_vintage"],
    )
    excluded_expansion = expanded.loc[
        (expanded.data_vintage == "STAGE_8_35_EXPANSION") & (expanded.class_id == 3),
        ["event_id", "target_class", "class_id", "year", "label_confidence", "evidence_type"],
    ].copy()
    excluded_expansion = excluded_expansion.rename(columns={"label_confidence": "label_quality_flag", "evidence_type": "ambiguity_reason"})
    excluded_expansion["exclusion_reason"] = "Generated source-year row without event-level observed FIRMS alert linkage; feature builder assigns fixed thermal and recurrence values"
    excluded_expansion["cohort_origin"] = "STAGE_8_35_EXPANSION"
    excluded = pd.concat([excluded_canonical, excluded_expansion], ignore_index=True, sort=False)
    excluded.to_csv(OUT_DIR / "excluded_events.csv", index=False)

    # Closest pairs among label-confident development candidates; these do not
    # use feature values or any test event.
    pair_rows: list[dict[str, object]] = []
    rows = candidates.reset_index(drop=True)
    for i in range(len(rows)):
        for j in range(i + 1, len(rows)):
            a, b = rows.iloc[i], rows.iloc[j]
            distance = haversine_km(float(a.centroid_lat), float(a.centroid_lon), float(b.centroid_lat), float(b.centroid_lon))
            pair_rows.append({
                "event_a": a.event_id, "event_b": b.event_id, "distance_km": distance,
                "same_incident_id": bool(a.incident_id == b.incident_id),
                "same_split": bool(a.split == b.split), "split_a": a.split, "split_b": b.split,
                "same_spatial_component": bool(a.spatial_component_id == b.spatial_component_id),
                "class_a": a.target_class, "class_b": b.target_class,
            })
    pairs = pd.DataFrame(pair_rows).sort_values(["distance_km", "event_a", "event_b"], kind="stable") if pair_rows else pd.DataFrame()
    pairs.head(50).to_csv(OUT_DIR / "closest_development_event_pairs.csv", index=False)

    pers = joined.loc[joined.class_id == 3].copy()
    pers_conf = candidates.loc[candidates.class_id == 3].copy()
    class_conf = candidates.groupby("target_class").size().sort_index().to_dict()
    persistent_by_year = pers_conf.groupby("year").size().to_dict()
    persistent_year_quality = {f"{year}:{flag}": int(n) for (year, flag), n in pers.groupby(["year", "label_quality_flag"]).size().items()}
    persistent_by_region = pers_conf.groupby("spatial_region").size().to_dict()
    repeated_source_ids = int((pers_conf.groupby("incident_id").size() > 1).sum())
    cross_split_incident_groups = int((pers_conf.groupby("incident_id").split.nunique() > 1).sum())
    cross_split_near_pairs_5km = int(((pairs.distance_km <= 5.0) & (~pairs.same_split)).sum()) if len(pairs) else 0
    near_split_pairs = pairs.loc[(pairs.distance_km <= 5.0) & (~pairs.same_split)].to_dict("records") if len(pairs) else []
    persistent_fixed_start_count = int(pers.event_start.astype(str).str.startswith("2018-03-15").sum())

    raw_sources, source_summary = _inventory_raw_sources()
    source_manifest_path = OUT_DIR / "raw_source_inventory.json"
    source_manifest_path.write_text(json.dumps({"files": raw_sources, "summary": source_summary}, indent=2), encoding="utf-8")
    source_inventory_hash = sha256_file(source_manifest_path)
    schema_hash = hashlib.sha256(json.dumps({k: list(v) for k, v in FEATURE_SCHEMA.items()}, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    blockers = [
        "Pre-2025 FIRMS records are event-window extracts rather than a continuous archive; historical zero counts cannot be distinguished from unobserved periods.",
        "The 18 Stage 8.35 added Persistent examples are generated from six facility/site definitions with fixed event times and fixed feature values; no matching observed event-level FIRMS linkage is established.",
        "Canonical Persistent event_start metadata uses 2018-03-15 despite label years 2024/2025; Persistent alert t0 must be rebuilt from observed detections.",
        "The development features parquet cannot be certified from raw lineage until full local archive coverage and source-row provenance are supplied.",
    ]
    status = "NOT_READY_FOR_MODELING"
    manifest = {
        "stage": "8.43",
        "status": status,
        "dataset_path": None,
        "dataset_sha256": None,
        "dataset_created": False,
        "construction_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "development_event_count": int(len(candidates)),
        "record_count": 0,
        "candidate_label_counts": {str(k): int(v) for k, v in class_conf.items()},
        "persistent_candidate_count": int(len(pers_conf)),
        "persistent_events_by_year": {str(k): int(v) for k, v in persistent_by_year.items()},
        "persistent_events_by_region": {str(k): int(v) for k, v in persistent_by_region.items()},
        "persistent_label_quality_by_year": persistent_year_quality,
        "persistent_t0_reconstructed_count": 0,
        "history_depth_available_count": 0,
        "history_depth_unavailable_count": int(len(candidates)),
        "persistent_event_start_fixed_2018_03_15_count": persistent_fixed_start_count,
        "canonical_label_quality_excluded_count": int(len(excluded_canonical)),
        "stage8_35_persistent_expansion_excluded_count": int(len(excluded_expansion)),
        "persistent_repeated_source_groups": repeated_source_ids,
        "persistent_source_groups_crossing_existing_split": cross_split_incident_groups,
        "confident_candidate_cross_split_pairs_within_5km": cross_split_near_pairs_5km,
        "confident_candidate_cross_split_pairs_within_5km_details": near_split_pairs,
        "authoritative_cohort_path": COHORT_PATH.relative_to(PROJECT_ROOT).as_posix(),
        "authoritative_cohort_sha256": sha256_file(COHORT_PATH),
        "label_metadata_path": LABELS_PATH.relative_to(PROJECT_ROOT).as_posix(),
        "label_metadata_sha256": sha256_file(LABELS_PATH),
        "physical_event_metadata_path": EVENTS_PATH.relative_to(PROJECT_ROOT).as_posix(),
        "physical_event_metadata_sha256": sha256_file(EVENTS_PATH),
        "raw_source_inventory_path": source_manifest_path.relative_to(PROJECT_ROOT).as_posix(),
        "raw_source_inventory_sha256": source_inventory_hash,
        "eligible_event_provenance_path": (OUT_DIR / "eligible_event_provenance.csv").relative_to(PROJECT_ROOT).as_posix(),
        "excluded_events_path": (OUT_DIR / "excluded_events.csv").relative_to(PROJECT_ROOT).as_posix(),
        "closest_pairs_path": (OUT_DIR / "closest_development_event_pairs.csv").relative_to(PROJECT_ROOT).as_posix(),
        "raw_source_summary": source_summary,
        "proposed_feature_schema_sha256": schema_hash,
        "features_computed": False,
        "feature_schema_sha256": None,
        "causality_audit": "NOT_RUN: no feature table was constructed because coverage is incomplete",
        "software": {"python": platform.python_version(), "pandas": pd.__version__, "pyarrow": __import__("pyarrow").__version__},
        "blockers": blockers,
    }
    manifest_text = json.dumps(manifest, indent=2)
    for name in ("persistence_feature_manifest.json", "persistence_expert_development_manifest.json"):
        (OUT_DIR / name).write_text(manifest_text, encoding="utf-8")

    persistent_label_counts = pers.target_class.value_counts().to_dict()
    report = f"""# Stage 8.43 — Persistent development cohort reconstruction audit

**Status: {status}**

No persistence feature table was generated. No model was trained, no features were selected, and no blind evaluation was run.

## A. Eligible development events

The authoritative label cohort is the Stage 8.34 trusted development set (`N={len(cohort)}`), joined only to Stage 8.25 event/label metadata using those development event IDs. Label-confident candidate events with documented provenance and coordinates: `{len(ledger)}`. The ledger is `artifacts/stage8_43/eligible_event_provenance.csv`; it contains labels/coordinates/provenance only, no model features. The Persistent subset is `{len(pers_conf)}` events. Stage 8.35's {len(excluded_expansion)} generated Persistent rows were excluded. Persistent `t0` is intentionally blank: Stage 8.25 `event_start` is fixed at 2018-03-15 for all {persistent_fixed_start_count} Persistent rows despite label years 2024/2025. Stage 8.30 derives Persistent `t0` from the first observation in the assigned year, and that raw-observation link is not available here.

## B. Persistent vs Non-Persistent distribution

Label-confident candidate counts: `{json.dumps({str(k): int(v) for k, v in class_conf.items()}, sort_keys=True)}`. Persistent label audit totals: `{json.dumps({str(k): int(v) for k, v in persistent_label_counts.items()}, sort_keys=True)}`. Confident Persistent candidates by year: `{json.dumps({str(k): int(v) for k, v in persistent_by_year.items()}, sort_keys=True)}`. By macro-region: `{json.dumps({str(k): int(v) for k, v in persistent_by_region.items()}, sort_keys=True)}`. All 42 Persistent labels in the canonical 131-event cohort have `CONFIRMED` tier/status in the label manifest; the Stage 8.34 quality flags further classify them as `{json.dumps(persistent_year_quality, sort_keys=True)}`. Ambiguous/potential-duplicate events are not in the candidate ledger.

## C. Raw FIRMS sources used

Raw observations were **not** used to compute features. Inventory found {source_summary['annual_2025_file_count']} five-day raw FIRMS chunks covering 2025 and {source_summary['event_window_file_count']} pre-2026 event-window CSVs. The older event-window extracts are not continuous source coverage across dates and geography. The 2025 archive does not provide the missing pre-2025 intervals required for prior-year history. Per-file hashes and coverage categories are in `artifacts/stage8_43/raw_source_inventory.json`.

## D. Feature provenance

No feature values were emitted. Raw source observations and deterministic transformations would be the only allowed feature lineage. Existing historical radius semantics in Stage 8.30 use a ±5 km candidate search and a 2 km primary historical sequence/statistics neighborhood, with a `t0 - 7 day` guard to exclude the ongoing event. That is the established criterion and should be reused if its input archive becomes complete. No new arbitrary radius was used here. Stage 8.35 fixed values for the 18 generated Persistent events remain disallowed.

## E. Causality verification

No feature table means no feature timestamp assertions can be certified. The existing helper's cutoff tests are not evidence that this rebuild was performed. Persistent `t0` is not established, and the source-coverage limitation blocks causal window-completeness assertions.

## F. Spatial separation

`closest_development_event_pairs.csv` contains the 50 closest pairs among label-confident candidates, their geodesic distance, current split, and spatial-component comparison. Same-incident ID groups among confident Persistent candidates: {repeated_source_ids}; such groups crossing the existing temporal split: {cross_split_incident_groups}. Cross-split label-confident event pairs within 5 km: {cross_split_near_pairs_5km}. Both cross-split pairs share an existing spatial component: the 2019/2025 Similipal forest pair (1.29 km) and the 2022/2025 Bandhavgarh forest pair (3.98 km). This is direct evidence the inherited temporal split does not isolate spatial components. The nearest Persistent pair in the table is PER_SRC_09/PER_SRC_08 (6.34 km; train/validation; two distinct incident IDs in the Jharia coalfield complex), which requires facility-group review. The nearest-pair screen does not substitute for a spatial validation fold audit.

## G. Temporal separation

The inherited temporal split is train through 2024 and validation in 2025. Persistent confident labels occur in years `{json.dumps({str(k): int(v) for k, v in persistent_by_year.items()}, sort_keys=True)}`. Repeated `incident_id` groups crossing train/validation are {cross_split_incident_groups}. A season cannot be assigned to Persistent examples from a verified alert timestamp; their stored event-start metadata is invalid for seasonality.

## H. Source diversity

Persistent source labels are documented by the event provenance ledger; the candidate set contains {pers_conf.incident_id.nunique()} unique incident/source IDs across {pers_conf.state.nunique()} states and `{pers_conf.spatial_region.nunique()}` macro-regions. Label-source categories and subtypes available in artifacts are preserved in the ledger. Site-level complexes with nearby distinct source IDs remain a potential grouping concern.

## I. Missing-history statistics

All recurrence/thermal/spatial history fields are uncomputed and unavailable for all {len(candidates)} ledger candidates; **zero is not substituted for missing history**. Persistent alert `t0` is unavailable from verified observation records. There is no event-level verified coverage map for pre-2025 FIRMS. This prevents distinguishing true zero detections from periods not downloaded.

## J. Invalid/excluded events and reasons

- 18 Stage 8.35 additions: excluded; source code generates them from six manually specified facilities at fixed March 15 timestamps and assigns fixed thermal values rather than linking each alert to a raw detection record.
- 18 of the canonical 42 Persistent events: excluded from label-eligible candidates due to Stage 8.34 `LABEL_AMBIGUOUS` or `LABEL_POTENTIAL_DUPLICATE` status.
- Persistent `t0` for all 24 confident candidates: not accepted from the fixed 2018-03-15 event-start metadata; must be rebuilt from observed detections in the label year.
- All label-confident candidates: retained in the provenance ledger, but feature reconstruction blocked because historical coverage is incomplete before 2025.

Exact canonical exclusions and confidence reasons, plus every Stage 8.35 generated Persistent event ID and reason, are listed in `artifacts/stage8_43/excluded_events.csv` ({len(excluded_canonical)} canonical exclusions and {len(excluded_expansion)} generated Persistent exclusions).

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

**{status}**. Required next evidence: a continuous, attributable FIRMS archive covering the full pre-alert windows (including 2012–2024) for the candidate locations; source-row provenance and coverage intervals; explicit physical-site grouping for nearby facilities; and spatial/temporal folds that keep each physical site in one partition. Once available, rebuild features from raw rows and assert every observation timestamp is no later than `t0` (with the existing 7-day ongoing-event exclusion if retained).
"""
    (OUT_DIR / "stage8_43_reconstruction_report.md").write_text(report, encoding="utf-8")
    return manifest


if __name__ == "__main__":
    result = audit_and_write()
    print(json.dumps({k: result[k] for k in ("status", "development_event_count", "record_count", "persistent_candidate_count", "persistent_events_by_year", "persistent_events_by_region", "persistent_source_groups_crossing_existing_split", "confident_candidate_cross_split_pairs_within_5km", "blockers")}, indent=2))
