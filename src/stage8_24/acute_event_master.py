"""
Stage 8.24 Phase A: Build Current Acute Event Master Table.

Combines authoritative predecessor event sources:
- DS03 forest events/matches
- DS04 agricultural events/matches
- DS05 industrial incidents/matches
- master_labels_2025
- Stage 8.23 label audit
- Stage 8.23 human adjudication

Produces:
- data/interim/ds08_stage8_24_current_acute_event_master.parquet
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Input paths
MASTER_LABELS_PATH = PROJECT_ROOT / "data" / "processed" / "labels" / "master_labels_2025.parquet"
DS03_MATCHES_PATH = PROJECT_ROOT / "data" / "labeling" / "ds03" / "forest_firms_matches.parquet"
DS04_MATCHES_PATH = PROJECT_ROOT / "data" / "labeling" / "ds04" / "agriculture_firms_matches.parquet"
DS05_MATCHES_PATH = PROJECT_ROOT / "data" / "labeling" / "ds05" / "ds05_firms_matches.parquet"

DS03_EVENTS_PATH = PROJECT_ROOT / "data" / "reference" / "ds03" / "forest_events.parquet"
DS04_EVENTS_PATH = PROJECT_ROOT / "data" / "reference" / "ds04" / "agriculture_events.parquet"
DS05_INCIDENTS_PATH = PROJECT_ROOT / "data" / "reference" / "ds05" / "industrial_incidents.parquet"
DS05_PERSISTENT_PATH = PROJECT_ROOT / "data" / "reference" / "ds05" / "persistent_sources.parquet"

STAGE8_23_AUDIT_PATH = PROJECT_ROOT / "data" / "interim" / "ds08_stage8_23_label_audit.parquet"
STAGE8_23_ADJUDICATION_PATH = PROJECT_ROOT / "data" / "interim" / "ds08_stage8_23_human_adjudication.parquet"

OUTPUT_MASTER_PARQUET = PROJECT_ROOT / "data" / "interim" / "ds08_stage8_24_current_acute_event_master.parquet"


def build_current_acute_event_master() -> Tuple[pd.DataFrame, Dict[str, Any]]:
    print("=" * 80)
    print("STAGE 8.24 PHASE A: BUILD CURRENT ACUTE EVENT MASTER TABLE")
    print("=" * 80)

    # 1. Load Predecessor Audit & Adjudication
    print("\n[Step 1/4] Loading Stage 8.23 audit and adjudication records...")
    df_audit = pd.read_parquet(STAGE8_23_AUDIT_PATH)
    df_adj = pd.read_parquet(STAGE8_23_ADJUDICATION_PATH)
    adj_decision_map = dict(zip(df_adj["event_id"], df_adj["reviewer_decision"]))
    adj_notes_map = dict(zip(df_adj["event_id"], df_adj["reviewer_notes"]))

    print(f"  Stage 8.23 audit records: {len(df_audit)}")
    print(f"  Stage 8.23 adjudication records: {len(df_adj)}")

    # 2. Build Master Records with Required Schema
    print("\n[Step 2/4] Constructing master schema records...")
    master_records: List[Dict[str, Any]] = []

    for _, row in df_audit.iterrows():
        ev_id = str(row["event_id"])
        inc_id = str(row["incident_id"])
        cls_name = str(row["source_class"])
        tax_id = int(row["taxonomy_class_id"])
        src_dataset = str(row["label_source"])
        evi_src = str(row["evidence_source"])
        evi_stat = str(row["evidence_status"])
        lbl_stat = str(row["label_status"])
        sup_elig = bool(row["supervised_eligibility"])

        # Detection IDs (ensure list/json consistency)
        det_ids_raw = row["detection_ids"]
        if isinstance(det_ids_raw, str):
            try:
                det_ids_list = json.loads(det_ids_raw)
            except Exception:
                det_ids_list = [det_ids_raw]
        elif isinstance(det_ids_raw, list):
            det_ids_list = det_ids_raw
        else:
            det_ids_list = []

        firms_det_str = json.dumps(det_ids_list)
        ev_start = str(row["temporal_extent_start"])
        ev_end = str(row["temporal_extent_end"])
        lat = float(row["latitude"])
        lon = float(row["longitude"])
        part = str(row["existing_partition"])

        # Reconcile adjudication status if uneligible
        if not sup_elig and ev_id in adj_decision_map:
            lbl_stat = f"ADJUDICATED_{adj_decision_map[ev_id]}"

        record = {
            "event_id": ev_id,
            "incident_id": inc_id,
            "class": cls_name,
            "class_id": tax_id,
            "source_dataset": src_dataset,
            "evidence_source": evi_src,
            "evidence_status": evi_stat,
            "label_status": lbl_stat,
            "supervised_eligibility": sup_elig,
            "firms_detection_ids": firms_det_str,
            "firms_detection_count": len(det_ids_list),
            "event_start": ev_start,
            "event_end": ev_end,
            "latitude": lat,
            "longitude": lon,
            "existing_partition": part,
        }
        master_records.append(record)

    df_master = pd.DataFrame(master_records)

    # 3. Save Master Parquet
    print("\n[Step 3/4] Persisting master table...")
    df_master.to_parquet(OUTPUT_MASTER_PARQUET, index=False)
    print(f"  Successfully wrote {len(df_master)} records to {OUTPUT_MASTER_PARQUET}")

    # 4. Compute and Print Exact Counts
    print("\n[Step 4/4] Computing exact audit counts...")
    print("-" * 60)
    print("A. COUNTS BY CLASS:")
    class_counts = df_master["class"].value_counts().to_dict()
    for c, cnt in class_counts.items():
        sup_cnt = len(df_master[(df_master["class"] == c) & (df_master["supervised_eligibility"] == True)])
        print(f"  - {c}: {cnt} total ({sup_cnt} supervised eligible)")

    print("\nB. COUNTS BY PHYSICAL EVENT (Supervised Eligible Acute Events):")
    df_acute_sup = df_master[
        (df_master["supervised_eligibility"] == True) &
        (df_master["class_id"].isin([0, 1, 2]))
    ]
    print(f"  Total Confirmed Acute Events: {len(df_acute_sup)}")
    for c in ["Industrial Fire", "Forest Fire", "Agricultural Fire"]:
        c_evs = df_acute_sup[df_acute_sup["class"] == c]
        print(f"  - {c}: {len(c_evs)} physical events (IDs: {c_evs['event_id'].tolist()})")

    print("\nC. COUNTS BY FIRMS DETECTION (Supervised Eligible Detections):")
    for c in ["Industrial Fire", "Forest Fire", "Agricultural Fire", "Other Thermal Source/Persistent Non-Biomass Thermal Source"]:
        sub = df_master[(df_master["class"] == c) & (df_master["supervised_eligibility"] == True)]
        tot_dets = sub["firms_detection_count"].sum()
        print(f"  - {c}: {tot_dets} associated detections")

    print("\nD. COUNTS BY EXISTING PARTITION (Supervised Eligible Acute Events):")
    part_counts = df_acute_sup["existing_partition"].value_counts().to_dict()
    for p, cnt in part_counts.items():
        print(f"  - {p}: {cnt} events")
    test_acute_cnt = len(df_acute_sup[df_acute_sup["existing_partition"].str.contains("test")])
    print(f"  >>> HELD-OUT INDEPENDENT TEST ACUTE EVENTS: {test_acute_cnt} <<<")

    print("\nE. COUNTS BY EVIDENCE STATUS:")
    evi_counts = df_master["evidence_status"].value_counts().to_dict()
    for e, cnt in evi_counts.items():
        print(f"  - {e}: {cnt} events")

    print("=" * 80)

    summary = {
        "total_records": len(df_master),
        "class_counts": class_counts,
        "acute_confirmed_events": len(df_acute_sup),
        "acute_test_events": test_acute_cnt,
        "evidence_status_counts": evi_counts,
    }
    return df_master, summary


if __name__ == "__main__":
    build_current_acute_event_master()
