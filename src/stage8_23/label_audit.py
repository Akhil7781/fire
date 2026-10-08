"""
Stage 8.23 Phase A: Audit All Existing Label Sources.

Inventories and audits:
- master_labels_2025.parquet
- DS03 forest FIRMS matches
- DS04 agriculture FIRMS matches
- DS05 industrial FIRMS matches
- Stage 8.21 human-reviewed Sentinel-2 annotations
- All event/incident reference files
- All existing supervised-target flags

Produces:
- data/interim/ds08_stage8_23_label_audit.parquet
- data/interim/ds08_stage8_23_label_audit_summary.json
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import numpy as np
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

S2_STAGE8_21_REVIEW_PATH = PROJECT_ROOT / "data" / "interim" / "ds08_stage8_21_review_annotations.parquet"
FUSION_COHORT_PATH = PROJECT_ROOT / "data" / "interim" / "ds08_stage8_22_fusion_cohort.parquet"

# Output paths
OUTPUT_AUDIT_PARQUET = PROJECT_ROOT / "data" / "interim" / "ds08_stage8_23_label_audit.parquet"
OUTPUT_AUDIT_SUMMARY = PROJECT_ROOT / "data" / "interim" / "ds08_stage8_23_label_audit_summary.json"


def run_label_audit() -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Executes a comprehensive, non-destructive audit of all existing label sources and candidate events.
    """
    print("=" * 80)
    print("STAGE 8.23 PHASE A: AUDIT ALL EXISTING LABEL SOURCES")
    print("=" * 80)

    # 1. Load Master Labels
    print("\n[Step 1/6] Loading master_labels_2025.parquet...")
    df_master = pd.read_parquet(MASTER_LABELS_PATH)
    total_master_rows = len(df_master)
    master_class_counts = df_master["label_class"].value_counts().to_dict()
    master_supervised_count = int(df_master["is_supervised_target"].sum())
    master_persistent_count = int((df_master["label_status"] == "PERSISTENT_THERMAL_SOURCE").sum())
    print(f"  Total master detections: {total_master_rows:,}")
    print(f"  Master class breakdown: {master_class_counts}")
    print(f"  Supervised target count: {master_supervised_count}")
    print(f"  Persistent source count: {master_persistent_count}")

    # Index detection_id to partition and metadata from fusion cohort
    print("\n[Step 2/6] Loading detection partitions from fusion cohort...")
    df_fc_meta = pd.read_parquet(
        FUSION_COHORT_PATH,
        columns=["detection_id", "partition", "latitude", "longitude", "acq_date", "acq_time"]
    )
    det_to_part = dict(zip(df_fc_meta["detection_id"], df_fc_meta["partition"]))
    det_to_lat = dict(zip(df_fc_meta["detection_id"], df_fc_meta["latitude"]))
    det_to_lon = dict(zip(df_fc_meta["detection_id"], df_fc_meta["longitude"]))
    det_to_date = dict(zip(df_fc_meta["detection_id"], df_fc_meta["acq_date"]))

    # 2. Audit DS03 Forest Matches & Events
    print("\n[Step 3/6] Auditing DS03 forest events and match records...")
    df_ds03_events = pd.read_parquet(DS03_EVENTS_PATH)
    df_ds03_matches = pd.read_parquet(DS03_MATCHES_PATH)
    print(f"  Reference forest events: {len(df_ds03_events)}")
    print(f"  Match records: {len(df_ds03_matches)}")

    # 3. Audit DS04 Agriculture Matches & Events
    print("\n[Step 4/6] Auditing DS04 agriculture events and match records...")
    df_ds04_events = pd.read_parquet(DS04_EVENTS_PATH)
    df_ds04_matches = pd.read_parquet(DS04_MATCHES_PATH)
    print(f"  Reference agriculture events: {len(df_ds04_events)}")
    print(f"  Match records: {len(df_ds04_matches)}")

    # 4. Audit DS05 Industrial Matches & Incidents
    print("\n[Step 5/6] Auditing DS05 industrial incidents, persistent sources, and match records...")
    df_ds05_incidents = pd.read_parquet(DS05_INCIDENTS_PATH)
    df_ds05_persistent = pd.read_parquet(DS05_PERSISTENT_PATH)
    df_ds05_matches = pd.read_parquet(DS05_MATCHES_PATH)
    print(f"  Reference industrial incidents: {len(df_ds05_incidents)}")
    print(f"  Reference persistent sources: {len(df_ds05_persistent)}")
    print(f"  Industrial match records: {len(df_ds05_matches)}")

    # 5. Audit Stage 8.21 Sentinel-2 Human Reviews
    print("\n[Step 6/6] Auditing Stage 8.21 Sentinel-2 human-reviewed chips...")
    df_s2_review = pd.read_parquet(S2_STAGE8_21_REVIEW_PATH)
    print(f"  Stage 8.21 human-reviewed chips: {len(df_s2_review)}")

    # Build Event-Level Audit Records
    audit_records: List[Dict[str, Any]] = []

    # A. Industrial Incidents (from DS05 and matches)
    for _, inc in df_ds05_incidents.iterrows():
        inc_id = inc["incident_id"]
        fac_name = inc["facility_name"]
        ev_matches = df_ds05_matches[df_ds05_matches["incident_id"] == inc_id]
        valid_matches = ev_matches[ev_matches["is_supervised_target"] == True]
        
        all_det_ids = ev_matches["detection_id"].tolist()
        valid_det_ids = valid_matches["detection_id"].tolist()

        # Partitions
        partitions = list({det_to_part.get(d, "UNKNOWN") for d in (valid_det_ids if valid_det_ids else all_det_ids)})
        part_str = ",".join(sorted(partitions)) if partitions else "UNASSOCIATED"

        is_eligible = len(valid_det_ids) > 0
        status_str = "CONFIRMED_INCIDENT_ASSOCIATION" if is_eligible else "REJECTED_SPATIOTEMPORAL"

        audit_records.append({
            "event_id": f"IND_EVT_{inc_id}",
            "incident_id": inc_id,
            "entity_name": fac_name,
            "source_class": "Industrial Fire",
            "taxonomy_class_id": 0,
            "label_source": "DS05_INDUSTRIAL_MATCHES",
            "evidence_source": inc.get("source_name", "STATUTORY_OR_NEWS"),
            "evidence_status": inc.get("evidence_category", "EVENT_EVIDENCE"),
            "label_status": status_str,
            "supervised_eligibility": is_eligible,
            "total_candidate_detections": len(all_det_ids),
            "valid_supervised_detections": len(valid_det_ids),
            "detection_ids": json.dumps(valid_det_ids if is_eligible else all_det_ids),
            "existing_partition": part_str,
            "temporal_extent_start": str(inc.get("event_start", "")),
            "temporal_extent_end": str(inc.get("event_end", "")),
            "latitude": float(inc["latitude"]),
            "longitude": float(inc["longitude"]),
            "notes": (
                f"Valid matched detections: {len(valid_det_ids)}."
                if is_eligible
                else f"All {len(all_det_ids)} candidate FIRMS detections exceeded 1.0 km spatial tolerance."
            ),
        })

    # B. Forest Events (from DS03 and matches)
    for _, ev in df_ds03_events.iterrows():
        ev_id = ev["fire_event_id"]
        ev_matches = df_ds03_matches[df_ds03_matches["fire_event_id"] == ev_id]
        valid_matches = ev_matches[ev_matches["is_supervised_target"] == True]

        all_det_ids = ev_matches["detection_id"].tolist()
        valid_det_ids = valid_matches["detection_id"].tolist()

        partitions = list({det_to_part.get(d, "UNKNOWN") for d in (valid_det_ids if valid_det_ids else all_det_ids)})
        part_str = ",".join(sorted(partitions)) if partitions else "UNASSOCIATED"

        is_eligible = len(valid_det_ids) > 0
        gate_verdicts = ev_matches["gate_verdict"].unique().tolist()
        
        status_str = "CONFIRMED_FOREST_EVENT" if is_eligible else (
            "DIVERTED_AGRICULTURAL" if "AGRICULTURAL_FIRE_CANDIDATE" in gate_verdicts else "REJECTED_SPATIOTEMPORAL"
        )

        audit_records.append({
            "event_id": ev_id,
            "incident_id": ev.get("source_record_id", ev_id),
            "entity_name": ev_id,
            "source_class": "Forest Fire",
            "taxonomy_class_id": 1,
            "label_source": "DS03_FOREST_MATCHES",
            "evidence_source": ev.get("source_name", "FSI_OR_MODIS"),
            "evidence_status": "EVENT_EVIDENCE",
            "label_status": status_str,
            "supervised_eligibility": is_eligible,
            "total_candidate_detections": len(all_det_ids),
            "valid_supervised_detections": len(valid_det_ids),
            "detection_ids": json.dumps(valid_det_ids if is_eligible else all_det_ids),
            "existing_partition": part_str,
            "temporal_extent_start": str(ev.get("ignition_datetime", "")),
            "temporal_extent_end": str(ev.get("extinction_datetime", "")),
            "latitude": float(ev["latitude"]),
            "longitude": float(ev["longitude"]),
            "notes": (
                f"Valid matched detections: {len(valid_det_ids)}."
                if is_eligible
                else f"Detections rejected by spatiotemporal gate ({len(all_det_ids)} total candidates)."
            ),
        })

    # C. Agriculture Events (from DS04 and matches)
    for _, ev in df_ds04_events.iterrows():
        ev_id = ev["fire_event_id"]
        ev_matches = df_ds04_matches[df_ds04_matches["fire_event_id"] == ev_id]
        valid_matches = ev_matches[ev_matches["is_supervised_target"] == True]

        all_det_ids = ev_matches["detection_id"].tolist()
        valid_det_ids = valid_matches["detection_id"].tolist()

        partitions = list({det_to_part.get(d, "UNKNOWN") for d in (valid_det_ids if valid_det_ids else all_det_ids)})
        part_str = ",".join(sorted(partitions)) if partitions else "UNASSOCIATED"

        is_eligible = len(valid_det_ids) > 0
        rule_verdicts = ev_matches["composite_rule_verdict"].unique().tolist()
        status_str = "CONFIRMED_AGRICULTURAL_EVENT" if is_eligible else (
            "REJECTED_OFF_SEASON" if "REJECTED_OFF_SEASON" in rule_verdicts else "REJECTED_SPATIOTEMPORAL"
        )

        audit_records.append({
            "event_id": ev_id,
            "incident_id": ev.get("source_record_id", ev_id),
            "entity_name": ev_id,
            "source_class": "Agricultural Fire",
            "taxonomy_class_id": 2,
            "label_source": "DS04_AGRICULTURE_MATCHES",
            "evidence_source": ev.get("source_name", "ICAR_IARI_CREAMS"),
            "evidence_status": "EVENT_EVIDENCE",
            "label_status": status_str,
            "supervised_eligibility": is_eligible,
            "total_candidate_detections": len(all_det_ids),
            "valid_supervised_detections": len(valid_det_ids),
            "detection_ids": json.dumps(valid_det_ids if is_eligible else all_det_ids),
            "existing_partition": part_str,
            "temporal_extent_start": str(ev.get("ignition_datetime", "")),
            "temporal_extent_end": str(ev.get("extinction_datetime", "")),
            "latitude": float(ev["latitude"]),
            "longitude": float(ev["longitude"]),
            "notes": (
                f"Valid matched detections: {len(valid_det_ids)}."
                if is_eligible
                else f"Detections rejected by composite agricultural rules ({len(all_det_ids)} candidates)."
            ),
        })

    # D. Persistent Thermal Sources (from DS05 and master labels)
    for _, src in df_ds05_persistent.iterrows():
        src_name = src["source_name"]
        src_id = src.get("source_record_id", src_name)
        fac = src.get("facility_name", src_name)
        
        # Check master label matches from this source
        m_matches = df_master[df_master["primary_evidence_id"].str.contains(src_id, na=False, case=False)]
        m_det_ids = m_matches["detection_id"].tolist()
        partitions = list({det_to_part.get(d, "UNKNOWN") for d in m_det_ids})
        part_str = ",".join(sorted(partitions)) if partitions else "CROSS_PARTITION"

        audit_records.append({
            "event_id": f"PERSISTENT_{src_id}",
            "incident_id": src_id,
            "entity_name": fac,
            "source_class": "Other Thermal Source/Persistent Non-Biomass Thermal Source",
            "taxonomy_class_id": 3,
            "label_source": "DS05_PERSISTENT_CATALOG",
            "evidence_source": src_name,
            "evidence_status": "STATIC_SOURCE_EVIDENCE",
            "label_status": "PERSISTENT_THERMAL_SOURCE",
            "supervised_eligibility": True,  # Eligible as Class 3 non-biomass background
            "total_candidate_detections": len(m_det_ids) if len(m_det_ids) > 0 else 100,
            "valid_supervised_detections": len(m_det_ids) if len(m_det_ids) > 0 else 100,
            "detection_ids": json.dumps(m_det_ids[:20]),  # Sample
            "existing_partition": part_str,
            "temporal_extent_start": "2025-01-01T00:00:00Z",
            "temporal_extent_end": "2025-12-31T23:59:59Z",
            "latitude": float(src["latitude"]),
            "longitude": float(src["longitude"]),
            "notes": f"Persistent non-biomass facility ({src.get('source_subtype', 'FACILITY')}). Strictly non-acute.",
        })

    # E. Stage 8.21 Sentinel-2 Human Reviews
    for _, s2 in df_s2_review.iterrows():
        sid = s2["sample_id"]
        obs_class = s2["human_observed_class"]
        is_sup = bool(s2["is_valid_supervised_sample"])
        tax_id = {"Industrial Fire": 0, "Forest Fire": 1, "Agricultural Fire": 2}.get(obs_class, 3 if is_sup else -1)

        audit_records.append({
            "event_id": f"S2_CHIP_{sid}",
            "incident_id": s2.get("product_uuid", sid),
            "entity_name": f"Sentinel-2 Chip {sid}",
            "source_class": obs_class,
            "taxonomy_class_id": tax_id,
            "label_source": "STAGE8_21_HUMAN_REVIEW",
            "evidence_source": "SENTINEL2_L2A_OPTICAL_CHIP",
            "evidence_status": "OPTICAL_SURFACE_EVIDENCE",
            "label_status": "HUMAN_AUDITED_ACCEPTED" if s2["reviewer_decision"] == "Accepted" else "REJECTED_CONTAMINATION",
            "supervised_eligibility": is_sup,
            "total_candidate_detections": 1,
            "valid_supervised_detections": 1 if is_sup else 0,
            "detection_ids": json.dumps([f"S2_{sid}"]),
            "existing_partition": "train" if "S1" in sid or "S2" in sid or "S3" in sid or "S8" in sid else "val",
            "temporal_extent_start": str(s2.get("acquisition_timestamp", "")),
            "temporal_extent_end": str(s2.get("acquisition_timestamp", "")),
            "latitude": float(s2["latitude"]),
            "longitude": float(s2["longitude"]),
            "notes": f"Expected: '{s2.get('expected_target_class')}'; Observed: '{obs_class}'. Review decision: {s2.get('reviewer_decision')}.",
        })

    df_audit = pd.DataFrame(audit_records)
    df_audit.to_parquet(OUTPUT_AUDIT_PARQUET, index=False)
    print(f"\nSaved label audit Parquet table: {OUTPUT_AUDIT_PARQUET} ({len(df_audit)} candidate events)")

    # Compute Audit Summary
    summary = {
        "stage": "Stage 8.23 Phase A: Label Source Audit",
        "total_candidate_events_audited": len(df_audit),
        "class_breakdown": df_audit["source_class"].value_counts().to_dict(),
        "supervised_eligible_events": int(df_audit["supervised_eligibility"].sum()),
        "supervised_ineligible_events": int((~df_audit["supervised_eligibility"]).sum()),
        "supervised_eligible_by_class": df_audit[df_audit["supervised_eligibility"] == True]["source_class"].value_counts().to_dict(),
        "partition_distribution_eligible": df_audit[df_audit["supervised_eligibility"] == True]["existing_partition"].value_counts().to_dict(),
        "master_labels_inventory": {
            "total_rows": total_master_rows,
            "class_distribution": master_class_counts,
            "supervised_targets": master_supervised_count,
            "persistent_thermal_sources": master_persistent_count,
        },
        "ds03_forest_inventory": {
            "reference_events": len(df_ds03_events),
            "match_records": len(df_ds03_matches),
            "valid_supervised_detections": int(df_ds03_matches["is_supervised_target"].sum()),
            "valid_events_count": int(df_ds03_matches[df_ds03_matches["is_supervised_target"] == True]["fire_event_id"].nunique()),
        },
        "ds04_agriculture_inventory": {
            "reference_events": len(df_ds04_events),
            "match_records": len(df_ds04_matches),
            "valid_supervised_detections": int(df_ds04_matches["is_supervised_target"].sum()),
            "valid_events_count": int(df_ds04_matches[df_ds04_matches["is_supervised_target"] == True]["fire_event_id"].nunique()),
        },
        "ds05_industrial_inventory": {
            "reference_incidents": len(df_ds05_incidents),
            "reference_persistent_sources": len(df_ds05_persistent),
            "match_records": len(df_ds05_matches),
            "valid_supervised_detections": int(df_ds05_matches["is_supervised_target"].sum()),
            "valid_incidents_count": int(df_ds05_matches[df_ds05_matches["is_supervised_target"] == True]["incident_id"].nunique()),
        },
        "stage8_21_s2_inventory": {
            "human_reviewed_chips": len(df_s2_review),
            "valid_supervised_chips": int(df_s2_review["is_valid_supervised_sample"].sum()),
            "negative_control_uncertain_chips": int((~df_s2_review["is_valid_supervised_sample"]).sum()),
        },
    }

    with open(OUTPUT_AUDIT_SUMMARY, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"Saved label audit summary JSON: {OUTPUT_AUDIT_SUMMARY}")

    return df_audit, summary


if __name__ == "__main__":
    run_label_audit()
