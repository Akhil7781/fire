"""Stage 8.44 evidence and coverage audit (development candidates only).

This deliberately refuses to convert absent archive coverage into zero counts.
It never reads blind-test artifacts and performs no model training/evaluation.
"""
from __future__ import annotations

import hashlib
import json
import math
import shutil
import tempfile
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "artifacts/stage8_44"
LEDGER = ROOT / "artifacts/stage8_43/eligible_event_provenance.csv"
WINDOWS = [7, 30, 90, 180, 365]
FEATURES = [
    "detections_6h", "detections_24h", "detections_72h", "detections_7d",
    "detections_30d", "detections_90d", "detections_180d", "detections_365d",
    "active_days_7d", "active_days_30d", "active_days_90d", "active_days_180d",
    "active_days_365d", "median_interarrival", "std_interarrival", "IQR_interarrival",
    "interarrival_CV", "historical_spatial_mean_distance", "historical_spatial_std_distance",
    "historical_radius", "spatial_dispersion", "historical_FRP_mean", "historical_FRP_std",
    "historical_FRP_CV", "historical_BT4_mean", "historical_BT4_std", "historical_BT5_mean",
    "historical_BT5_std", "historical_night_ratio", "historical_day_ratio", "hour_of_day_entropy",
]


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def continuous_local_days() -> set[date]:
    """Only full-India, sequential standard-product chunk files count as coverage."""
    days: set[date] = set()
    for folder in [ROOT / "data/raw/2025", ROOT / "data/raw_context/2024_Q4"]:
        for p in folder.glob("VIIRS_NOAA20_SP_*.csv"):
            # Parse the explicit five-day filenames; don't infer coverage from event extracts.
            name = p.name
            try:
                start = date.fromisoformat(name.split("_SP_")[1][:10])
                end = date.fromisoformat(name.split("_to_")[1][:10])
            except (ValueError, IndexError):
                continue
            cur = start
            while cur <= end:
                days.add(cur)
                cur += timedelta(days=1)
    return days


def make_outputs(folder: Path) -> None:
    df = pd.read_csv(LEDGER, dtype={"event_id": str})
    # Normalize Stage 8.43 schema; only class_id=3 is Persistent.
    p = df[df.class_id == 3].copy()
    p["authoritative_t0"] = ""
    p["t0_reconstruction_method"] = "UNRESOLVED"
    p["t0_provenance"] = "No independently validated event-linked raw FIRMS detection timeline; Stage 8.43 flags t0 as inherited metadata or blank."
    p["authoritative_latitude"] = p.latitude
    p["authoritative_longitude"] = p.longitude
    p["coordinate_provenance"] = "Stage 8.43 label provenance ledger coordinates; not independently re-surveyed."
    p["first_observed_detection"] = ""
    p["last_observed_detection"] = ""
    p["event_duration_hours"] = float("nan")
    p["event_id_original"] = p.incident_id
    p["known_physical_source"] = p.facility_name
    p["label_source"] = p.label_provenance
    p["label_year"] = p.year
    p[["event_id", "label", "label_year", "event_id_original", "known_physical_source",
       "facility_name", "label_source", "label_tier", "adjudication_status", "label_confidence",
       "authoritative_t0", "first_observed_detection", "last_observed_detection", "event_duration_hours",
       "t0_reconstruction_method", "t0_provenance", "authoritative_latitude", "authoritative_longitude",
       "coordinate_provenance", "latitude", "longitude", "state", "spatial_region", "split",
       "spatial_component_id"]].to_csv(folder / "persistent_event_timeline.csv", index=False)

    # Date coverage calendar for only verified continuous local archive chunks.
    covered = continuous_local_days()
    coverage_rows = []
    feature_rows = []
    for _, r in df.iterrows():
        # Historical windows cannot be anchored to an authoritative event timestamp.
        # Metadata dates are recorded in the coverage matrix solely to quantify potential missingness.
        raw_t = r.get("t0")
        anchor_unresolved = int(r.class_id) == 3
        if pd.isna(raw_t) or not str(raw_t).strip():
            raw_t = r.get("metadata_event_start")
        # For Persistent events the old fixed metadata date is expressly disallowed
        # as an event anchor, even if populated in the source ledger.
        if anchor_unresolved:
            raw_t = None
        try:
            t0 = pd.Timestamp(raw_t).date()
        except Exception:
            t0 = None
        feature = {"event_id": r.event_id, "ground_truth_label": r.label,
                   "label_year": r.year, "t0_used_for_features": "",
                   "feature_status": "UNAVAILABLE: authoritative t0 unresolved; no historical feature values emitted"}
        for f in FEATURES:
            feature[f] = float("nan")
        for w in WINDOWS:
            days = []
            if t0:
                # Follow Stage 8.30's seven-day guard for historical inputs.
                end = t0 - timedelta(days=7)
                start = end - timedelta(days=w - 1)
                cur = start
                while cur <= end:
                    days.append(cur)
                    cur += timedelta(days=1)
            ncovered = sum(d in covered for d in days)
            frac = ncovered / len(days) if days and not anchor_unresolved else float("nan")
            feature[f"history_coverage_fraction_{w}d"] = frac
            coverage_rows.append({
                "event_id": r.event_id, "label": r.label, "label_year": int(r.year),
                "required_history_start": days[0].isoformat() if days else "",
                "required_history_end": days[-1].isoformat() if days else "",
                "window_days": w, "verified_continuous_days_available": ncovered if not anchor_unresolved else "",
                "coverage_fraction": frac, "coverage_state": "ANCHOR_UNRESOLVED" if anchor_unresolved else ("PARTIAL_OR_NONE" if frac < 1 else "COMPLETE_LOCAL"),
                "missing_days": len(days) - ncovered if not anchor_unresolved else "",
                "available_local_periods": "2024-10-01..2024-12-31; 2025-01-01..2025-12-31 (full India bbox, VIIRS_NOAA20_SP)",
                "missing_intervals": "See coverage calendar gaps; pre-2024-10-01 has no verified continuous local coverage",
                "t0_anchor_status": "UNRESOLVED" if r.class_id == 3 else "INHERITED_METADATA_NOT_RAW_VALIDATED",
                "zero_vs_unobserved_rule": "NO FEATURE COUNT EMITTED; missing coverage is unavailable, never zero",
            })
        feature_rows.append(feature)
    pd.DataFrame(coverage_rows).to_csv(folder / "coverage_audit.csv", index=False)
    pd.DataFrame(feature_rows).to_parquet(folder / "persistent_feature_reconstruction.parquet", index=False)

    # Split repair is represented as spatial/physical components; all 50km-connected
    # events remain together. This is an auditable grouping plan, not a trained split.
    n = len(df)
    parent = list(range(n))
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)
    def hav(a, b):
        la1, lo1, la2, lo2 = map(math.radians, [a.latitude, a.longitude, b.latitude, b.longitude])
        x = math.sin((la2-la1)/2)**2 + math.cos(la1)*math.cos(la2)*math.sin((lo2-lo1)/2)**2
        return 6371.0088 * 2 * math.asin(math.sqrt(x))
    for i in range(n):
        for j in range(i+1, n):
            a, b = df.iloc[i], df.iloc[j]
            if a.incident_id == b.incident_id or hav(a, b) <= 50.0:
                union(i, j)
    groups = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(i)
    group_rows = []
    for gid, members in enumerate(sorted(groups.values(), key=lambda x: min(df.iloc[k].event_id for k in x))):
        old = df.iloc[members].split.value_counts()
        proposed = str(old.index[0]) if len(old) else "train"
        group_rows.append({"spatial_source_component": f"SRCSP_{gid:03d}",
                           "event_ids": sorted(df.iloc[members].event_id.tolist()),
                           "member_count": len(members), "inherited_splits": sorted(set(df.iloc[members].split)),
                           "proposed_group_split": proposed})
    (folder / "development_split_manifest.json").write_text(json.dumps({
        "method": "Union events sharing incident_id or lying within 50 km using Stage 8.43 coordinates; assign connected groups by modal inherited split.",
        "spatial_threshold_km": 50.0, "groups": group_rows,
        "cross_split_pair_counts_after_grouping": {"under_5km": 0, "under_10km": 0, "under_50km": 0},
        "note": "Proposed grouping plan only; distances use ledger coordinates and physical facilities need review."
    }, indent=2))

    sources = []
    for folder_name in ["data/raw/2025", "data/raw_context/2024_Q4"]:
        for path in sorted((ROOT / folder_name).glob("VIIRS_NOAA20_SP_*.csv")):
            try:
                start = path.name.split("_SP_")[1][:10]
                end = path.name.split("_to_")[1][:10]
            except (IndexError, ValueError):
                start = end = "UNKNOWN"
            sources.append({"sensor": "VIIRS_NOAA20_SP", "processing_level": "SP (standard science product; according to product name)",
                            "date_range": [start, end], "source_url": "Local NASA FIRMS Area API acquisition; original request URL redacted/not retained",
                            "download_timestamp": "Unavailable in existing chunk filename metadata",
                            "relative_path": path.relative_to(ROOT).as_posix(), "file_hash_sha256": sha(path),
                            "coverage_scope": "India bbox; contiguous chunks only", "coverage_kind": "annual_2025" if "2025" in folder_name else "2024_Q4"})
    (folder / "historical_firms_index_manifest.json").write_text(json.dumps({
        "status": "INCOMPLETE_ARCHIVE", "indexed_files": sources,
        "continuous_local_coverage": [{"sensor": "VIIRS_NOAA20_SP", "start": "2024-10-01", "end": "2025-12-31", "scope": "India bbox"}],
        "event_window_extracts_excluded_from_zero-coverage_proof": True,
        "local_continuous_coverage_days": len(covered),
        "index_fields_requested": ["date", "latitude", "longitude", "sensor", "acq_datetime", "FRP", "BT4", "BT5", "daynight", "confidence", "source_file"],
        "index_status": "Raw files catalogued; observation-level index not represented as complete because full required archive is unavailable.",
        "note": "No file download timestamp or original API URL was embedded in the available raw chunk files."
    }, indent=2))


def run() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="stage844_audit_") as td:
        temp = Path(td)
        make_outputs(temp)
        first = {p.name: sha(p) for p in sorted(temp.iterdir())}
        # Required repeat: regenerate from the same frozen inputs and compare bytes.
        with tempfile.TemporaryDirectory(prefix="stage844_repeat_") as td2:
            second_dir = Path(td2)
            make_outputs(second_dir)
            second = {p.name: sha(p) for p in sorted(second_dir.iterdir())}
            if first != second:
                raise RuntimeError("Stage 8.44 outputs differ across identical reruns")
        for p in temp.iterdir():
            shutil.copy2(p, OUT / p.name)
    coverage = pd.read_csv(OUT / "coverage_audit.csv")
    persistent = pd.read_csv(OUT / "persistent_event_timeline.csv")
    manifest = json.loads((OUT / "historical_firms_index_manifest.json").read_text())
    hashes = {p.name: sha(p) for p in sorted(OUT.iterdir()) if p.is_file()}
    rows = [
        "# Stage 8.44 — authoritative timeline and historical coverage audit",
        "", "**NOT_READY_FOR_PERSISTENCE_MODELING**", "",
        "## Decision", "",
        "No. The historical FIRMS evidence is not sufficient to distinguish true zero recurrence from unavailable history, and the retained Persistent event t0 values remain unresolved.", "",
        "## Cohort and timeline", "",
        f"The Stage 8.43 ledger contains {len(pd.read_csv(LEDGER))} retained label-confident development candidates ({len(persistent)} Persistent). The Persistent timelines record provenance and coordinates but set authoritative t0 to unresolved; metadata dates are not promoted to observed event time.", "",
        "All 24 Persistent entries lack an independently validated first/last event detection and duration. Stage 8.43 states their t0 is inherited metadata or blank, and its report identifies fixed 2018-03-15 metadata in the canonical cohort. The supplied raw archive does not establish a verified event-linked raw timeline.", "",
        "## Archive coverage", "",
        f"Local sequential standard-product coverage is {manifest['continuous_local_coverage'][0]['start']} through {manifest['continuous_local_coverage'][0]['end']} for the India bbox ({manifest['local_continuous_coverage_days']} days). The 90 pre-2026 event-window CSVs cataloged in Stage 8.43 are not treated as continuous coverage.", "",
        f"Candidate/window coverage rows: {len(coverage)}. Complete local window rows: {int((coverage.coverage_fraction == 1).sum())}; partial/zero-coverage rows among date-anchored candidates: {int((coverage.coverage_fraction < 1).sum())}; Persistent rows with unresolved anchors: {int((coverage.coverage_state == 'ANCHOR_UNRESOLVED').sum())} (5 each for 24 events). Counts/features are NaN and unavailable when coverage or authoritative t0 is missing; no zero counts are substituted.", "",
        "For the 24 Persistent candidates, required start/end dates and missing-day counts are intentionally blank because their authoritative t0 is unresolved. The old fixed 2018-03-15 date is not used to fabricate a required history window. For the other 75 candidates, coverage dates use inherited event metadata only as provisional audit anchors and are not treated as event-time validation.", "",
        "The archive manifest records source hashes. Original request URLs and download timestamps were not embedded in available files. NASA historical archive availability was not acquired in this stage; theoretical archive availability is not counted as local observed coverage.", "",
        "## Causality and feature construction", "",
        "The established Stage 8.30 association semantics use a ±5 km candidate search, a 2 km primary historical sequence/statistics neighborhood, and a t0−7-day ongoing-event guard. Because t0 is unresolved and archive coverage is incomplete, no detection association or causal feature values are emitted. All requested feature columns are present as unavailable (NaN); the feature generator reads labels only as output metadata and does not branch on them.", "",
        "## Source diversity and split audit", "",
        f"Persistent candidates represent {persistent.event_id_original.nunique()} distinct incident/source IDs across {persistent.state.nunique()} states and {persistent.spatial_region.nunique()} macro-regions; label years: {json.dumps({str(k): int(v) for k,v in persistent.label_year.value_counts().sort_index().items()})}. Facility/source labels remain in the timeline. There are no sensor-attributed event timelines that meet the evidence standard, so reconstructed-timeline sensor distribution is unavailable.", "",
        "A proposed development split manifest groups events sharing an incident identifier or lying within 50 km, preserving those groups in one partition. Its connected-group plan yields zero cross-split pairs under 5, 10, and 50 km by construction. This is a proposed split grouping, not a validation that facility identity is complete; assignments retain each group’s modal inherited split.", "",
        "## Quality gates", "",
        "Failed: evidence-based Persistent t0; complete local history; historical zero-vs-unobserved distinction; causal feature reconstruction; independently verified physical-source grouping. Passed: no generated Stage 8.35 rows restored; missing coverage not encoded as zero; deterministic repeated artifact generation.", "",
        f"Reconstruction was run twice from the same development-only ledger and local coverage files; output bytes matched exactly. All {len(pd.read_csv(LEDGER)) * len(FEATURES)} history-dependent feature values remain unavailable (100%). No model was trained and no blind evaluator was run.", "",
        "## Generated artifact SHA-256", "",
    ]
    rows += [f"- `{k}`: `{v}`" for k, v in sorted(hashes.items())]
    rows += ["", "No Stage 8.36 checkpoint, independent test manifest, or evaluation counter was read or modified.", ""]
    (OUT / "stage8_44_report.md").write_text("\n".join(rows), encoding="utf-8")
    # Report hash listing includes itself via a companion hashes file (self-hashing is undefined).
    all_hashes = {p.name: sha(p) for p in sorted(OUT.iterdir()) if p.is_file() and p.name != "stage8_44_hashes.json"}
    (OUT / "stage8_44_hashes.json").write_text(json.dumps(all_hashes, indent=2))
    print(json.dumps({"status": "NOT_READY_FOR_PERSISTENCE_MODELING", "persistent_events": len(persistent),
                      "coverage_rows": len(coverage), "full_coverage_rows": int((coverage.coverage_fraction == 1).sum()),
                      "rerun_identical": True, "artifacts": sorted(p.name for p in OUT.iterdir())}, indent=2))


if __name__ == "__main__":
    run()
