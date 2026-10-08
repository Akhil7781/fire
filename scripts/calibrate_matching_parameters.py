"""
Empirical Sensitivity Analysis & Calibration Script for Label Matching Parameters.
Evaluates spatial and temporal matching parameter sweeps strictly on the TRAIN partition.
Does NOT touch or leak test partition data.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List
import pandas as pd

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.labeling.config import get_label_config
from src.labeling.matching import match_evidence_to_firms
from src.labeling.sources import (
    AgriculturalFireAdapter,
    ForestFireAdapter,
    IndustrialFireAdapter,
    OtherThermalSourceAdapter,
)


def run_parameter_sensitivity_sweep() -> Dict[str, Any]:
    print("\n" + "=" * 75)
    print("EMPIRICAL PARAMETER SENSITIVITY SWEEP (TRAINING PARTITION ONLY)")
    print("=" * 75 + "\n")

    config = get_label_config()

    # Load ONLY train partition detections
    print("Loading TRAIN partition detections from frozen Parquet...")
    firms_df = pd.read_parquet(
        config.frozen_features_path,
        columns=["detection_id", "latitude", "longitude", "acq_datetime_utc", "partition"],
    )
    train_df = firms_df[firms_df["partition"] == "train"].copy()
    total_train = len(train_df)
    print(f"Loaded {total_train:,d} TRAIN detections (Zero test leakage).\n")

    # Ingest reference evidence
    all_evis = []
    for ad_cls in [IndustrialFireAdapter, ForestFireAdapter, AgriculturalFireAdapter, OtherThermalSourceAdapter]:
        ad = ad_cls(config.reference_dir)
        all_evis.extend(ad.normalize(ad.fetch_or_load()))
    print(f"Total reference evidence records: {len(all_evis)}\n")

    # 1. Spatial Tolerance Sweep across [0.25, 0.50, 1.00, 1.50, 2.00, 3.00, 5.00] km
    spatial_grid = [0.25, 0.50, 1.00, 1.50, 2.00, 3.00, 5.00]
    spatial_results = []

    print("-" * 75)
    print(f"{'Spatial Tol (km)':<18} | {'Total Matches':<14} | {'Class Distribution':<35}")
    print("-" * 75)

    for s_tol in spatial_grid:
        cfg = get_label_config()
        # Scale spatial tolerances uniformly for sensitivity testing
        cfg.spatial_tol_forest_cluster = s_tol
        cfg.spatial_tol_agri_field = s_tol
        cfg.spatial_tol_industrial_polygon = s_tol
        cfg.spatial_tol_industrial_exact = min(s_tol, 1.0)
        cfg.spatial_tol_power_plant = min(s_tol, 1.0)
        cfg.spatial_tol_flaring_stack = min(s_tol, 1.0)
        cfg.spatial_tol_brick_kiln = min(s_tol, 1.0)
        cfg.spatial_tol_coal_fire = s_tol

        matches = match_evidence_to_firms(train_df, all_evis, cfg)
        by_class = {}
        for m in matches:
            c = m.candidate_class.name
            by_class[c] = by_class.get(c, 0) + 1

        res_entry = {
            "spatial_tol_km": s_tol,
            "total_matches": len(matches),
            "class_distribution": by_class,
        }
        spatial_results.append(res_entry)
        cls_str = ", ".join(f"{k}:{v}" for k, v in by_class.items())
        print(f"{s_tol:<18.2f} | {len(matches):<14d} | {cls_str}")

    # 2. Temporal Tolerance Sweep across [12, 24, 48, 72, 96] hours
    temporal_grid = [12.0, 24.0, 48.0, 72.0, 96.0]
    temporal_results = []

    print("\n" + "-" * 75)
    print(f"{'Temporal Tol (h)':<18} | {'Total Matches':<14} | {'Class Distribution':<35}")
    print("-" * 75)

    for t_tol in temporal_grid:
        cfg = get_label_config()
        cfg.temporal_tol_news_incident = t_tol
        cfg.temporal_tol_sebi_disclosure = t_tol
        cfg.temporal_tol_spcb_order = t_tol
        cfg.temporal_tol_iari_bulletin = t_tol
        cfg.temporal_tol_mcd64a1 = t_tol

        matches = match_evidence_to_firms(train_df, all_evis, cfg)
        by_class = {}
        for m in matches:
            c = m.candidate_class.name
            by_class[c] = by_class.get(c, 0) + 1

        res_entry = {
            "temporal_tol_hours": t_tol,
            "total_matches": len(matches),
            "class_distribution": by_class,
        }
        temporal_results.append(res_entry)
        cls_str = ", ".join(f"{k}:{v}" for k, v in by_class.items())
        print(f"{t_tol:<18.1f} | {len(matches):<14d} | {cls_str}")

    # Save calibration report
    out_dir = config.audits_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    sweep_json = out_dir / "parameter_sensitivity_sweep.json"
    sweep_md = out_dir / "parameter_sensitivity_sweep.md"

    payload = {
        "dataset_partition": "train",
        "train_rows_evaluated": total_train,
        "spatial_sensitivity_sweep": spatial_results,
        "temporal_sensitivity_sweep": temporal_results,
    }

    with open(sweep_json, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    with open(sweep_md, "w", encoding="utf-8") as f:
        f.write("# Empirical Parameter Sensitivity & Calibration Report\n\n")
        f.write("**Evaluation Partition**: `train` (578,465 detections, strictly isolated from test)\n\n")
        f.write("## 1. Spatial Tolerance Sensitivity Sweep\n\n")
        f.write("| Spatial Tolerance (km) | Total Candidate Matches | Class Breakdown |\n")
        f.write("|---|---|---|\n")
        for r in spatial_results:
            cls_fmt = ", ".join(f"`{k}`: {v}" for k, v in r["class_distribution"].items()) or "None"
            f.write(f"| {r['spatial_tol_km']:.2f} km | {r['total_matches']:,d} | {cls_fmt} |\n")

        f.write("\n## 2. Temporal Tolerance Sensitivity Sweep\n\n")
        f.write("| Temporal Tolerance (hours) | Total Candidate Matches | Class Breakdown |\n")
        f.write("|---|---|---|\n")
        for r in temporal_results:
            cls_fmt = ", ".join(f"`{k}`: {v}" for k, v in r["class_distribution"].items()) or "None"
            f.write(f"| {r['temporal_tol_hours']:.1f} h | {r['total_matches']:,d} | {cls_fmt} |\n")

    print(f"\nCalibration sweep report saved to:\n  {sweep_json}\n  {sweep_md}\n")
    return payload


if __name__ == "__main__":
    run_parameter_sensitivity_sweep()
