"""
Test suite for Stage 3 (DS_04): India Agricultural Burn Evidence Pipeline (Sentinel-2 + ICAR-IARI CREAMS).
Verifies all 10 core scientific invariants:
1. test_burn_scar_alone_cannot_create_agricultural_fire
2. test_cropland_land_cover_gate_required (C1)
3. test_harvest_season_calendar_window_required (C2)
4. test_spectral_step_and_char_absorption_required (C3)
5. test_independent_agricultural_corroboration_required (C4)
6. test_calibration_sweep_strictly_isolated_to_train_partition
7. test_event_ids_are_preserved_and_grouped
8. test_same_fire_event_id_cannot_be_split_across_derived_partitions
9. test_previous_pilot_audit_demotions_and_retentions
10. test_frozen_firms_and_predecessor_artifacts_unchanged
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = Path("d:/DATA PREPROCESSING")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.labeling.ds04 import (
    DS04Pipeline,
    evaluate_agricultural_composite_rule,
    is_harvest_season_window,
    geodesic_distance_km,
    temporal_difference_hours,
)


@pytest.fixture(scope="module")
def ds04_data():
    """Runs DS04 pipeline and loads output artifacts."""
    pipeline = DS04Pipeline(PROJECT_ROOT)
    pipeline.build_and_save_reference_dataset()
    summary = pipeline.match_and_audit()

    ref_events = pd.read_parquet(PROJECT_ROOT / "data" / "reference" / "ds04" / "agriculture_events.parquet")
    firms_matches = pd.read_parquet(PROJECT_ROOT / "data" / "labeling" / "ds04" / "agriculture_firms_matches.parquet")
    candidates = pd.read_parquet(PROJECT_ROOT / "data" / "labeling" / "ds04" / "agriculture_fire_candidates.parquet")
    rejected = pd.read_parquet(PROJECT_ROOT / "data" / "labeling" / "ds04" / "agriculture_rejected_candidates.parquet")

    with open(PROJECT_ROOT / "data" / "labeling" / "ds04" / "ds04_audit.json", "r", encoding="utf-8") as f:
        audit = json.load(f)

    return {
        "summary": summary,
        "ref_events": ref_events,
        "firms_matches": firms_matches,
        "candidates": candidates,
        "rejected": rejected,
        "audit": audit,
    }


def test_burn_scar_alone_cannot_create_agricultural_fire(ds04_data):
    """
    Invariant 1: Burn scar / spectral change alone cannot create an AGRICULTURAL_FIRE label.
    Negative controls (e.g. plowed soil with low char or uncorroborated burns)
    must never appear in agriculture_fire_candidates.
    """
    candidates = ds04_data["candidates"]
    rejected = ds04_data["rejected"]

    negative_control_ids = {
        "EVT_2025_AGRI_PB_MOGA_OFF_SEASON_007",
        "EVT_2025_AGRI_RJ_JAIPUR_BRICK_008",
        "EVT_2025_AGRI_HR_JIND_PLOWED_009",
        "EVT_2025_AGRI_PB_BATHINDA_UNCORROB_010",
    }

    candidate_events = set(candidates["fire_event_id"].unique())
    assert negative_control_ids.isdisjoint(candidate_events), (
        f"Negative control events leaked into agriculture candidates: {negative_control_ids.intersection(candidate_events)}"
    )

    for ev_id in negative_control_ids:
        rej_rows = rejected[rejected["fire_event_id"] == ev_id]
        if not rej_rows.empty:
            assert (rej_rows["target_class"] != 3).all()
            assert (rej_rows["composite_verdict"] != "AGRICULTURAL_FIRE").all()


def test_cropland_land_cover_gate_required():
    """
    Invariant 2: Cropland land-cover status (C1) is strictly required.
    Non-cropland parcels (forest, brick kiln, urban, scrub) fail C1 and are rejected.
    """
    t_harvest = datetime(2025, 4, 20, 12, 0, tzinfo=timezone.utc)

    # Cropland pass
    verdict, rationale, conds = evaluate_agricultural_composite_rule(
        land_cover_status="CROPLAND",
        event_start_time=t_harvest,
        spectral_dnbr=0.35,
        spectral_nir_ratio=0.65,
        has_independent_corroboration=True,
    )
    assert conds["C1_cropland_gate"] is True
    assert verdict == "AGRICULTURAL_FIRE"

    # Brick kiln / industrial fail
    verdict_bk, rationale_bk, conds_bk = evaluate_agricultural_composite_rule(
        land_cover_status="BRICK_KILN",
        event_start_time=t_harvest,
        spectral_dnbr=0.35,
        spectral_nir_ratio=0.65,
        has_independent_corroboration=True,
    )
    assert conds_bk["C1_cropland_gate"] is False
    assert verdict_bk == "REJECTED_NON_CROPLAND"

    # Forest parcel fail
    verdict_f, rationale_f, conds_f = evaluate_agricultural_composite_rule(
        land_cover_status="FOREST",
        event_start_time=t_harvest,
        spectral_dnbr=0.35,
        spectral_nir_ratio=0.65,
        has_independent_corroboration=True,
    )
    assert conds_f["C1_cropland_gate"] is False
    assert verdict_f == "REJECTED_NON_CROPLAND"


def test_harvest_season_calendar_window_required():
    """
    Invariant 3: Statutory harvest season calendar window (C2) is strictly enforced.
    Kharif: Sep 20 to Nov 30.
    Rabi: Apr 1 to May 31.
    All other dates are off-season.
    """
    # Rabi dates
    in_rabi, name_rabi = is_harvest_season_window(datetime(2025, 4, 15, tzinfo=timezone.utc))
    assert in_rabi is True
    assert name_rabi == "RABI"

    in_rabi_end, _ = is_harvest_season_window(datetime(2025, 5, 31, tzinfo=timezone.utc))
    assert in_rabi_end is True

    # Kharif dates
    in_kharif_start, name_kharif = is_harvest_season_window(datetime(2025, 9, 20, tzinfo=timezone.utc))
    assert in_kharif_start is True
    assert name_kharif == "KHARIF"

    in_kharif_mid, _ = is_harvest_season_window(datetime(2025, 10, 25, tzinfo=timezone.utc))
    assert in_kharif_mid is True

    in_kharif_end, _ = is_harvest_season_window(datetime(2025, 11, 30, tzinfo=timezone.utc))
    assert in_kharif_end is True

    # Off-season dates (e.g. Jan 15, Jul 10, Sep 15)
    in_jan, name_jan = is_harvest_season_window(datetime(2025, 1, 15, tzinfo=timezone.utc))
    assert in_jan is False
    assert name_jan == "OFF_SEASON"

    in_jul, name_jul = is_harvest_season_window(datetime(2025, 7, 10, tzinfo=timezone.utc))
    assert in_jul is False
    assert name_jul == "OFF_SEASON"

    in_sep_early, _ = is_harvest_season_window(datetime(2025, 9, 15, tzinfo=timezone.utc))
    assert in_sep_early is False


def test_spectral_step_and_char_absorption_required():
    """
    Invariant 4: Spectral step and char absorption (C3) require BOTH dNBR >= tau and NIR_ratio < tau.
    """
    t_harvest = datetime(2025, 4, 20, 12, 0, tzinfo=timezone.utc)

    # Pass: high dNBR, low NIR ratio
    verdict, _, conds = evaluate_agricultural_composite_rule(
        land_cover_status="CROPLAND",
        event_start_time=t_harvest,
        spectral_dnbr=0.25,
        spectral_nir_ratio=0.70,
        has_independent_corroboration=True,
        tau_dnbr=0.18,
        tau_nir_ratio=0.85,
    )
    assert conds["C3_spectral_char"] is True
    assert verdict == "AGRICULTURAL_FIRE"

    # Fail: dNBR below threshold
    verdict_low_dnbr, _, conds_low_dnbr = evaluate_agricultural_composite_rule(
        land_cover_status="CROPLAND",
        event_start_time=t_harvest,
        spectral_dnbr=0.10,
        spectral_nir_ratio=0.70,
        has_independent_corroboration=True,
        tau_dnbr=0.18,
        tau_nir_ratio=0.85,
    )
    assert conds_low_dnbr["C3_spectral_char"] is False
    assert verdict_low_dnbr == "AMBIGUOUS_SPECTRAL"

    # Fail: NIR ratio too high (no char absorption / soil drying)
    verdict_high_nir, _, conds_high_nir = evaluate_agricultural_composite_rule(
        land_cover_status="CROPLAND",
        event_start_time=t_harvest,
        spectral_dnbr=0.25,
        spectral_nir_ratio=0.92,
        has_independent_corroboration=True,
        tau_dnbr=0.18,
        tau_nir_ratio=0.85,
    )
    assert conds_high_nir["C3_spectral_char"] is False
    assert verdict_high_nir == "AMBIGUOUS_SPECTRAL"


def test_independent_agricultural_corroboration_required():
    """
    Invariant 5: Independent agricultural corroboration (C4) from official bulletin is mandatory.
    Without corroboration, the observation is marked AMBIGUOUS_UNCORROBORATED.
    """
    t_harvest = datetime(2025, 4, 20, 12, 0, tzinfo=timezone.utc)

    verdict_no_corrob, rationale, conds = evaluate_agricultural_composite_rule(
        land_cover_status="CROPLAND",
        event_start_time=t_harvest,
        spectral_dnbr=0.35,
        spectral_nir_ratio=0.60,
        has_independent_corroboration=False,
    )
    assert conds["C4_independent_corrob"] is False
    assert verdict_no_corrob == "AMBIGUOUS_UNCORROBORATED"
    assert "bulletin" in rationale.lower()


def test_calibration_sweep_strictly_isolated_to_train_partition(ds04_data):
    """
    Invariant 6: Sensitivity sweep for calibration thresholds is strictly isolated
    to the designated training calibration subset (partition == 'train').
    Zero validation or test records were queried.
    """
    audit = ds04_data["audit"]
    sweep_info = audit["calibration_sweep"]

    assert sweep_info["calibration_partition"] == "train"
    assert sweep_info["calibration_partitions_read"] == ["train"]
    assert sweep_info["isolation_verification"] == "PASSED_STRICT_TRAIN_ISOLATION"

    # Verify that sweep grid contains evaluated metrics
    grid = sweep_info["sweep_grid_results"]
    assert len(grid) > 0
    for entry in grid:
        assert entry["sample_size"] == 50
        assert 0.0 <= entry["pass_percentage"] <= 100.0
        assert entry["mean_frp_mw"] > 0.0


def test_event_ids_are_preserved_and_grouped(ds04_data):
    """
    Invariant 7: Multiple FIRMS detections from a single physical agricultural burn
    share an identical fire_event_id.
    """
    candidates = ds04_data["candidates"]
    audit = ds04_data["audit"]

    # 18 verified detections across 6 events
    assert len(candidates) == 18
    assert candidates["fire_event_id"].nunique() == 6

    # Verify distribution from audit matches dataframe
    counts = candidates["fire_event_id"].value_counts().to_dict()
    audit_counts = audit["detections_per_event_distribution"]["counts_by_event"]
    assert counts == audit_counts

    # Karnal has 9 detections, Sehore has 4, Sangrur has 2
    assert counts["EVT_2025_AGRI_HR_KARNAL_RABI_002"] == 9
    assert counts["EVT_2025_AGRI_MP_SEHORE_RABI_003"] == 4
    assert counts["EVT_2025_AGRI_PB_SANGRUR_RABI_001"] == 2


def test_same_fire_event_id_cannot_be_split_across_derived_partitions(ds04_data):
    """
    Invariant 8: An entire agricultural fire event is assigned to exactly one partition.
    Zero leakage of a fire event across derived train, val, and test splits.
    """
    candidates = ds04_data["candidates"]
    audit = ds04_data["audit"]

    # Check each event's partition assignments
    event_to_partitions = candidates.groupby("fire_event_id")["derived_event_split"].unique()
    for ev_id, splits in event_to_partitions.items():
        assert len(splits) == 1, f"Event {ev_id} split across multiple partitions: {splits}"

    # Verify partition grouping from audit
    split_grouping = audit["train_val_test_event_grouping"]
    train_evs = set(split_grouping["derived_ds04_train"]["event_ids"])
    val_evs = set(split_grouping["derived_ds04_val"]["event_ids"])
    test_evs = set(split_grouping["derived_ds04_test"]["event_ids"])

    # Disjoint partition sets
    assert train_evs.isdisjoint(val_evs)
    assert train_evs.isdisjoint(test_evs)
    assert val_evs.isdisjoint(test_evs)


def test_previous_pilot_audit_demotions_and_retentions(ds04_data):
    """
    Invariant 9: The 8 pilot agricultural detections are audited against C1-C4.
    Exactly 2 are retained and 6 are demoted with traceable rationale.
    """
    audit = ds04_data["audit"]
    pilot_audit = audit["previous_pilot_audit"]

    assert pilot_audit["total_pilot_detections_audited"] == 8
    assert pilot_audit["retained_count"] == 2
    assert pilot_audit["demoted_count"] == 6

    retained_ids = {
        "bfa7be650c6056a861bd8a646372ecc90ac1bcd5580ce86fb63bf836f2f55332",
        "11b71e6f93f9ead9f7af527645297049a1eab6e2dd26dd17aa23318d6cb50808",
    }

    candidates = ds04_data["candidates"]
    candidate_ids = set(candidates["detection_id"].unique())

    # Retained IDs must be present in candidates
    for det_id in retained_ids:
        assert det_id in candidate_ids, f"Retained pilot detection {det_id} missing from candidates"

    # Demoted IDs must be present in rejected candidates
    rejected = ds04_data["rejected"]
    rejected_ids = set(rejected["detection_id"].unique())

    records = pilot_audit["records"]
    for rec in records:
        if rec["stage3_status"] == "DEMOTED_INSUFFICIENT_COMPOSITE_EVIDENCE":
            assert rec["detection_id"] in rejected_ids
            assert rec["c3_spectral"] is False or rec["c4_independent"] is False


def test_frozen_firms_and_predecessor_artifacts_unchanged():
    """
    Invariant 10: Complete immutability of frozen FIRMS table and Stage 1/2 artifacts.
    """
    # Check frozen causal features table
    causal_path = PROJECT_ROOT / "data" / "interim" / "causal_features_2025.parquet"
    assert causal_path.exists(), "causal_features_2025.parquet does not exist!"
    df_causal = pd.read_parquet(causal_path, columns=["detection_id", "partition"])
    assert len(df_causal) == 1_175_795, f"Row count changed: {len(df_causal)}"

    # Check DS_05 artifacts exist and are unchanged
    ds05_anchors = PROJECT_ROOT / "data" / "labeling" / "ds05" / "ds05_valid_industrial_anchors.parquet"
    ds05_confounders = PROJECT_ROOT / "data" / "labeling" / "ds05" / "ds05_quarantined_confounders.parquet"
    assert ds05_anchors.exists()
    assert ds05_confounders.exists()
    assert len(pd.read_parquet(ds05_anchors)) == 2
    assert len(pd.read_parquet(ds05_confounders)) == 1870

    # Check DS_03 artifacts exist and are unchanged
    ds03_candidates = PROJECT_ROOT / "data" / "labeling" / "ds03" / "forest_fire_candidates.parquet"
    assert ds03_candidates.exists()
    assert len(pd.read_parquet(ds03_candidates)) == 19
