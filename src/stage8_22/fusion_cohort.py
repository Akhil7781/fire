"""
Stage 8.22: Multimodal Fusion Cohort Construction Module.
Builds the unified, auditable fusion table combining:
1. FIRMS causal geospatial/thermal features (27D)
2. Frozen 1D Causal TCN temporal embeddings (64D)
3. Frozen Deep SAD anomaly latent representations (32D)
4. Frozen YOLOv8n-Infra embeddings (128D - mask gated)
5. Frozen YOLOv8n-Fire/Smoke embeddings (128D - mask gated)
6. Frozen Sentinel-2 L2A visual embeddings (128D - mask gated)
7. Modality presence mask (6D)
8. Independently authorized target labels and split keys.

All joins are strictly validated for 1:1 integrity with explicit logging
of pre/post counts, unmatched counts, and modality coverage percentages.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Paths to frozen source artifacts
ALIGNED_TCN_SAD_PATH = PROJECT_ROOT / "data" / "embeddings" / "fusion" / "india_2025_tcn_sad_aligned.parquet"
CAUSAL_FEATURES_PATH = PROJECT_ROOT / "data" / "interim" / "causal_features_2025.parquet"
MASTER_LABELS_PATH = PROJECT_ROOT / "data" / "processed" / "labels" / "master_labels_2025.parquet"
S2_EMBEDDINGS_PATH = PROJECT_ROOT / "data" / "interim" / "ds08_stage8_21_s2_embeddings.parquet"
S2_ANNOTATIONS_PATH = PROJECT_ROOT / "data" / "interim" / "ds08_stage8_21_review_annotations.parquet"

# Output paths
FUSION_COHORT_PATH = PROJECT_ROOT / "data" / "interim" / "ds08_stage8_22_fusion_cohort.parquet"
LABELED_SUBSET_PATH = PROJECT_ROOT / "data" / "interim" / "ds08_stage8_22_labeled_fusion_subset.parquet"
FUSION_SUMMARY_PATH = PROJECT_ROOT / "data" / "interim" / "ds08_stage8_22_fusion_cohort_summary.json"

# Target taxonomy definitions
TARGET_TAXONOMY: List[str] = [
    "Industrial Fire",
    "Forest Fire",
    "Agricultural Fire",
    "Other Thermal Source/Persistent Non-Biomass Thermal Source",
]

CLASS_NAME_TO_ID: Dict[str, int] = {name: idx for idx, name in enumerate(TARGET_TAXONOMY)}
ID_TO_CLASS_NAME: Dict[int, str] = {idx: name for idx, name in enumerate(TARGET_TAXONOMY)}

# Master label mapping (from 1-indexed master labels to 0-indexed taxonomy)
MASTER_LABEL_TO_TAXONOMY: Dict[int, int] = {
    1: 0,  # Industrial Fire
    2: 1,  # Forest Fire
    3: 2,  # Agricultural Fire
    4: 3,  # Other Thermal Source / Persistent
}

# Modality definitions & dimensions
MODALITY_NAMES: List[str] = ["tcn", "sad", "yolo_infra", "yolo_fire", "s2", "geo"]
MODALITY_DIMS: Dict[str, int] = {
    "tcn": 64,
    "sad": 32,
    "yolo_infra": 128,
    "yolo_fire": 128,
    "s2": 128,
    "geo": 27,
    "mask": 6,
}

# Strictly causal, past-only tabular features from FIRMS (zero future leakage)
CAUSAL_GEO_FEATURES: List[str] = [
    "bright_ti4",
    "bright_ti5",
    "frp",
    "scan",
    "track",
    "delta_t",
    "temp_ratio",
    "pixel_area",
    "frp_density",
    "frp_log1p",
    "sin_diurnal",
    "cos_diurnal",
    "sin_lst",
    "cos_lst",
    "sin_annual",
    "cos_annual",
    "hist_count_6h_2km",
    "hist_count_24h_2km",
    "time_since_last_det_2km",
    "has_prior_24h_2km",
    "mean_frp_6h_2km",
    "max_frp_6h_2km",
    "mean_frp_24h_2km",
    "max_frp_24h_2km",
    "day_ratio_24h_2km",
    "spatial_dispersion_24h_2km",
    "snapshot_co_detect_count_2km",
]


def haversine_km_vec(lat1: np.ndarray, lon1: np.ndarray, lat2: float, lon2: float) -> np.ndarray:
    """Vectorized great-circle distance in kilometers."""
    R = 6371.0
    phi1 = np.radians(lat1)
    phi2 = np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlam = np.radians(lon2 - lon1)
    a = np.sin(dphi / 2.0) ** 2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlam / 2.0) ** 2
    c = 2.0 * np.arctan2(np.sqrt(a), np.sqrt(np.maximum(1.0 - a, 0.0)))
    return R * c


def build_fusion_cohort(
    save_parquet: bool = True,
    output_dir: Optional[Path] = None,
) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
    """
    Builds the unified multimodal fusion cohort table with 1:1 join verification.
    Returns:
        (df_full_cohort, df_labeled_subset, summary_metrics)
    """
    print("=" * 80)
    print("STAGE 8.22: MULTIMODAL FUSION COHORT CONSTRUCTION")
    print("=" * 80)

    # 1. Base Aligned TCN + Deep SAD table
    print("\n[Step 1/5] Loading operational TCN + Deep SAD aligned representations...")
    tcn_cols = [f"z_tcn_{i}" for i in range(MODALITY_DIMS["tcn"])]
    sad_cols = [f"z_sad_{i}" for i in range(MODALITY_DIMS["sad"])]
    meta_cols = ["detection_id", "sequence_id", "acq_datetime_utc", "timestamp_utc", "partition", "active_timesteps"]
    
    df_aligned = pd.read_parquet(ALIGNED_TCN_SAD_PATH, columns=meta_cols + tcn_cols + sad_cols)
    rows_initial = len(df_aligned)
    print(f"  Loaded aligned base table: {rows_initial:,} rows, {len(df_aligned.columns)} columns.")
    assert df_aligned["detection_id"].is_unique, "Aligned table detection_id must be unique!"

    # 2. Join Causal FIRMS Features
    print("\n[Step 2/5] Joining causal FIRMS spatio-temporal features (27D past-only)...")
    causal_req_cols = ["detection_id", "latitude", "longitude", "acq_date", "acq_time"] + CAUSAL_GEO_FEATURES
    df_causal = pd.read_parquet(CAUSAL_FEATURES_PATH, columns=causal_req_cols)
    print(f"  Pre-join row counts: Aligned={len(df_aligned):,}, Causal={len(df_causal):,}")
    
    # Cast boolean feature to float32
    df_causal["has_prior_24h_2km"] = df_causal["has_prior_24h_2km"].astype(np.float32)
    for col in CAUSAL_GEO_FEATURES:
        df_causal[col] = df_causal[col].astype(np.float32)

    df_fusion = df_aligned.merge(df_causal, on="detection_id", how="left")
    rows_after_causal = len(df_fusion)
    unmatched_causal = df_fusion["latitude"].isna().sum()
    print(f"  Post-join row count: {rows_after_causal:,} (change: {rows_after_causal - rows_initial})")
    print(f"  Unmatched causal rows: {unmatched_causal} (0.00%)")
    assert unmatched_causal == 0, "All operational detections must have causal features!"
    assert rows_after_causal == rows_initial, "1:1 join invariant violated on causal features!"

    # 3. Join Master Labels
    print("\n[Step 3/5] Joining independently authorized master labels...")
    label_cols = [
        "detection_id", "label_class", "label_status", "confidence_tier",
        "is_supervised_target", "evidence_category", "primary_source"
    ]
    df_labels = pd.read_parquet(MASTER_LABELS_PATH, columns=label_cols)
    print(f"  Pre-join row counts: Fusion={len(df_fusion):,}, Labels={len(df_labels):,}")
    
    df_fusion = df_fusion.merge(df_labels, on="detection_id", how="left")
    rows_after_labels = len(df_fusion)
    unmatched_labels = df_fusion["label_class"].isna().sum()
    print(f"  Post-join row count: {rows_after_labels:,} (change: {rows_after_labels - rows_initial})")
    print(f"  Unmatched label rows: {unmatched_labels} (0.00%)")
    assert unmatched_labels == 0, "All operational detections must have master label records!"
    assert rows_after_labels == rows_initial, "1:1 join invariant violated on master labels!"

    # Initialize unified target label columns
    df_fusion["target_class_id"] = -1
    df_fusion["target_class_name"] = "UNLABELED"
    df_fusion["human_observed_class"] = None
    df_fusion["expected_target_class"] = None

    # Map authorized labels
    for ml_id, tax_id in MASTER_LABEL_TO_TAXONOMY.items():
        mask = (df_fusion["label_class"] == ml_id) & (
            (df_fusion["is_supervised_target"] == True) | (ml_id == 4)  # Class 4 are persistent confounders
        )
        df_fusion.loc[mask, "target_class_id"] = tax_id
        df_fusion.loc[mask, "target_class_name"] = ID_TO_CLASS_NAME[tax_id]
        df_fusion.loc[mask, "human_observed_class"] = ID_TO_CLASS_NAME[tax_id]

    # 4. Modality Association: Sentinel-2 & YOLO
    print("\n[Step 4/5] Evaluating documented acquisition links for Sentinel-2 & YOLO...")
    
    # Initialize modality presence flags
    df_fusion["has_tcn"] = True
    df_fusion["has_sad"] = True
    df_fusion["has_geo"] = True
    df_fusion["has_yolo_infra"] = False
    df_fusion["has_yolo_fire"] = False
    df_fusion["has_s2"] = False
    
    # Allocate zero matrices for optional embeddings via single concatenated DataFrame
    s2_cols = [f"z_s2_{i}" for i in range(MODALITY_DIMS["s2"])]
    infra_cols = [f"z_infra_{i}" for i in range(MODALITY_DIMS["yolo_infra"])]
    fire_cols = [f"z_fire_smoke_{i}" for i in range(MODALITY_DIMS["yolo_fire"])]

    zeros_df = pd.DataFrame(
        np.zeros((len(df_fusion), len(s2_cols) + len(infra_cols) + len(fire_cols)), dtype=np.float32),
        columns=s2_cols + infra_cols + fire_cols,
        index=df_fusion.index,
    )
    df_fusion = pd.concat([df_fusion, zeros_df], axis=1)

    # Load Sentinel-2 chips and embeddings
    df_s2_emb = pd.read_parquet(S2_EMBEDDINGS_PATH)
    df_s2_ann = pd.read_parquet(S2_ANNOTATIONS_PATH)
    df_s2 = df_s2_ann.merge(df_s2_emb[["sample_id"] + [f"dim_{i:03d}" for i in range(128)]], on="sample_id")

    # Documented spatial/temporal matching to FIRMS
    s2_matched_det_ids = set()
    s2_optical_only_records = []

    for _, s2_row in df_s2.iterrows():
        sid = s2_row["sample_id"]
        c_lat, c_lon = s2_row["latitude"], s2_row["longitude"]
        s2_date = None
        for part in s2_row["source_product"].split("_"):
            if len(part) == 15 and part[8] == "T":
                s2_date = f"{part[:4]}-{part[4:6]}-{part[6:8]}"
                break

        # Spatial-temporal intersection (footprint <= 2.56 km radius, same sensing date)
        dist = haversine_km_vec(df_fusion["latitude"].values, df_fusion["longitude"].values, c_lat, c_lon)
        cand_mask = (dist <= 2.56) & (df_fusion["acq_date"] == s2_date)
        match_indices = df_fusion.index[cand_mask].tolist()

        if len(match_indices) > 0:
            print(f"  Sentinel-2 chip {sid} matched {len(match_indices)} coincident FIRMS detections on {s2_date}.")
            for midx in match_indices:
                det_id = df_fusion.at[midx, "detection_id"]
                s2_matched_det_ids.add(det_id)
                df_fusion.at[midx, "has_s2"] = True
                for i in range(128):
                    df_fusion.at[midx, f"z_s2_{i}"] = np.float32(s2_row[f"dim_{i:03d}"])
                df_fusion.at[midx, "expected_target_class"] = s2_row["expected_target_class"]
                df_fusion.at[midx, "human_observed_class"] = s2_row["human_observed_class"]
                df_fusion.at[midx, "evidence_category"] = "OPTICAL_SENTINEL2_VERIFIED"
                df_fusion.at[midx, "primary_source"] = f"SENTINEL2_SAFE_{sid}"
                df_fusion.at[midx, "label_status"] = "CONFIRMED_HUMAN_LABEL"
                df_fusion.at[midx, "confidence_tier"] = "Tier A"
                if s2_row["human_observed_class"] in CLASS_NAME_TO_ID:
                    df_fusion.at[midx, "target_class_id"] = CLASS_NAME_TO_ID[s2_row["human_observed_class"]]
                    df_fusion.at[midx, "target_class_name"] = s2_row["human_observed_class"]
                    df_fusion.at[midx, "is_supervised_target"] = s2_row["is_valid_supervised_sample"]
        else:
            # Standalone optical observation
            print(f"  Sentinel-2 chip {sid} has no coincident FIRMS detection (retained as standalone optical sample).")
            opt_dict = {
                "detection_id": f"S2_{sid}",
                "sequence_id": f"SEQ_S2_{sid}",
                "acq_datetime_utc": pd.to_datetime(s2_row["acquisition_timestamp"] or f"{s2_date}T05:30:00Z", utc=True),
                "timestamp_utc": int(pd.to_datetime(s2_row["acquisition_timestamp"] or f"{s2_date}T05:30:00Z", utc=True).timestamp()),
                "partition": "val" if sid in ["DS08_EXP_S4_001", "S8_002"] else "train",
                "active_timesteps": 1,
                "latitude": float(c_lat),
                "longitude": float(c_lon),
                "acq_date": s2_date or "2025-01-01",
                "acq_time": 530,
                "label_class": 1 if s2_row["human_observed_class"] == "Industrial Fire" else (2 if s2_row["human_observed_class"] == "Forest Fire" else (3 if s2_row["human_observed_class"] == "Agricultural Fire" else (4 if s2_row["human_observed_class"] == "Other Thermal Source/Persistent Non-Biomass Thermal Source" else 0))),
                "label_status": "CONFIRMED_HUMAN_LABEL",
                "confidence_tier": "Tier A",
                "is_supervised_target": bool(s2_row["is_valid_supervised_sample"]),
                "evidence_category": "OPTICAL_SENTINEL2_VERIFIED",
                "primary_source": f"SENTINEL2_SAFE_{sid}",
                "target_class_id": CLASS_NAME_TO_ID.get(s2_row["human_observed_class"], -1),
                "target_class_name": s2_row["human_observed_class"] if s2_row["human_observed_class"] in CLASS_NAME_TO_ID else "UNLABELED",
                "human_observed_class": s2_row["human_observed_class"],
                "expected_target_class": s2_row["expected_target_class"],
                "has_tcn": False,
                "has_sad": False,
                "has_geo": False,
                "has_yolo_infra": False,
                "has_yolo_fire": False,
                "has_s2": True,
            }
            # Fill zero columns
            for col in tcn_cols + sad_cols + infra_cols + fire_cols + CAUSAL_GEO_FEATURES:
                opt_dict[col] = np.float32(0.0)
            for i in range(128):
                opt_dict[f"z_s2_{i}"] = np.float32(s2_row[f"dim_{i:03d}"])
            s2_optical_only_records.append(opt_dict)

    if s2_optical_only_records:
        df_opt = pd.DataFrame(s2_optical_only_records)
        df_fusion = pd.concat([df_fusion, df_opt], ignore_index=True)
        print(f"  Appended {len(s2_optical_only_records)} standalone optical observations.")

    # 5. Build explicit modality masks
    print("\n[Step 5/5] Building explicit modality masks and summary statistics...")
    mask_df = pd.DataFrame({
        f"mask_{name}": df_fusion[f"has_{name}"].astype(np.float32)
        for name in MODALITY_NAMES
    }, index=df_fusion.index)
    df_fusion = pd.concat([df_fusion, mask_df], axis=1)

    total_rows = len(df_fusion)
    tcn_cov = float(df_fusion["has_tcn"].mean() * 100)
    sad_cov = float(df_fusion["has_sad"].mean() * 100)
    geo_cov = float(df_fusion["has_geo"].mean() * 100)
    s2_cov = float(df_fusion["has_s2"].mean() * 100)
    infra_cov = float(df_fusion["has_yolo_infra"].mean() * 100)
    fire_cov = float(df_fusion["has_yolo_fire"].mean() * 100)

    print("\nModality Coverage Across Operational Population:")
    print(f"  TCN Temporal (64D):       {df_fusion['has_tcn'].sum():,}/{total_rows:,} ({tcn_cov:.4f}%)")
    print(f"  Deep SAD Anomaly (32D):   {df_fusion['has_sad'].sum():,}/{total_rows:,} ({sad_cov:.4f}%)")
    print(f"  FIRMS Geospatial (27D):   {df_fusion['has_geo'].sum():,}/{total_rows:,} ({geo_cov:.4f}%)")
    print(f"  Sentinel-2 Visual (128D): {df_fusion['has_s2'].sum():,}/{total_rows:,} ({s2_cov:.4f}%)")
    print(f"  YOLO Infrastructure:      0/{total_rows:,} ({infra_cov:.4f}% - unjoined external benchmark)")
    print(f"  YOLO Fire/Smoke:          0/{total_rows:,} ({fire_cov:.4f}% - unjoined external benchmark)")

    # Extract labeled modeling subset
    labeled_mask = (df_fusion["target_class_id"] >= 0) | (df_fusion["human_observed_class"] == "Uncertain")
    df_labeled = df_fusion[labeled_mask].copy().reset_index(drop=True)
    
    print("\nLabeled Modeling/Evaluation Cohort Class Distribution:")
    for cid, cname in ID_TO_CLASS_NAME.items():
        cnt = (df_labeled["target_class_id"] == cid).sum()
        print(f"  Class {cid} [{cname}]: {cnt} samples")
    uncertain_cnt = (df_labeled["human_observed_class"] == "Uncertain").sum()
    print(f"  Negative Controls [Uncertain]: {uncertain_cnt} samples")
    print(f"  Total Labeled Modeling Cohort: {len(df_labeled)} samples")

    summary_metrics = {
        "stage": "Stage 8.22: Multimodal Fusion Cohort",
        "total_observations": total_rows,
        "rows_initial_aligned": rows_initial,
        "rows_post_causal": rows_after_causal,
        "rows_post_labels": rows_after_labels,
        "unmatched_causal_count": int(unmatched_causal),
        "unmatched_labels_count": int(unmatched_labels),
        "duplicate_detection_id_count": int(df_fusion["detection_id"].duplicated().sum()),
        "modality_coverage_pct": {
            "tcn": round(tcn_cov, 4),
            "sad": round(sad_cov, 4),
            "geo": round(geo_cov, 4),
            "s2": round(s2_cov, 4),
            "yolo_infra": round(infra_cov, 4),
            "yolo_fire": round(fire_cov, 4),
        },
        "labeled_cohort_size": len(df_labeled),
        "labeled_class_counts": {
            cname: int((df_labeled["target_class_id"] == cid).sum())
            for cid, cname in ID_TO_CLASS_NAME.items()
        },
        "negative_controls_uncertain_count": int(uncertain_cnt),
        "partition_counts_full": df_fusion["partition"].value_counts().to_dict(),
        "partition_counts_labeled": df_labeled["partition"].value_counts().to_dict(),
    }

    if save_parquet:
        out_base = output_dir or PROJECT_ROOT / "data" / "interim"
        out_base.mkdir(parents=True, exist_ok=True)
        cohort_out = out_base / "ds08_stage8_22_fusion_cohort.parquet"
        labeled_out = out_base / "ds08_stage8_22_labeled_fusion_subset.parquet"
        summary_out = out_base / "ds08_stage8_22_fusion_cohort_summary.json"

        print(f"\nSaving full fusion cohort to {cohort_out}...")
        df_fusion.to_parquet(cohort_out, index=False, compression="snappy")
        print(f"Saving labeled modeling subset to {labeled_out}...")
        df_labeled.to_parquet(labeled_out, index=False, compression="snappy")
        with open(summary_out, "w", encoding="utf-8") as f:
            json.dump(summary_metrics, f, indent=2)
        print(f"Saved summary metrics to {summary_out}.")

    return df_fusion, df_labeled, summary_metrics


if __name__ == "__main__":
    build_fusion_cohort(save_parquet=True)
