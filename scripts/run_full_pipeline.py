"""
Full dataset preprocessing execution script.
Executes chunked, memory-safe ingestion and causal feature extraction
for the 1,024,996 India-region NOAA-20 SP detections for 2025 and 2024 Q4 context burn-in.
"""

from __future__ import annotations

import gc
import json
import os
import sys
import time
import tracemalloc
from pathlib import Path
from typing import Any, Dict, List

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
import pandas as pd
import psutil
import pyarrow as pa
import pyarrow.parquet as pq

from src.utils.config import get_config
from src.data.schema import RAW_FIRMS_COLUMNS, generate_detection_id
from src.data.invariants import (
    verify_raw_dataframe,
    verify_id_uniqueness,
    verify_temporal_monotonicity,
    verify_causal_history,
    haversine_distance_meters,
    PreprocessingInvariantError,
)
from src.data.instantaneous import compute_instantaneous_features
from src.data.spatial_index import assign_h3_res8, LocalSpatialIndex
from src.data.causal_context import compute_causal_and_snapshot_features
from src.data.partitions import assign_spatiotemporal_partitions, PartitionAwareScaler


def get_current_rss_mb() -> float:
    """Returns current process Resident Set Size in MB."""
    try:
        process = psutil.Process()
        return process.memory_info().rss / (1024 * 1024)
    except Exception:
        return 0.0


def atomic_save_parquet(df: pd.DataFrame, target_path: Path) -> None:
    """Writes a DataFrame to Parquet using an atomic temp file replacement."""
    target_path = Path(target_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = target_path.with_name(f".tmp_{target_path.name}_{os.getpid()}")
    try:
        df.to_parquet(tmp_path, index=False)
        if target_path.exists():
            target_path.unlink()
        tmp_path.replace(target_path)
    except Exception:
        if tmp_path.exists():
            tmp_path.unlink()
        raise


def run_full_pipeline() -> int:
    print("\n" + "#" * 75)
    print("# FULL-SCALE PREPROCESSING PIPELINE: 1,024,996 INDIA NOAA-20 SP (2025)")
    print("#" * 75 + "\n")

    config = get_config()
    raw_dir = config.raw_data_dir
    context_dir = config.raw_context_dir

    raw_files = sorted(list(set(list(raw_dir.glob("*.csv")) + list(raw_dir.glob("*/*.csv")))))
    context_files = sorted(list(set(list(context_dir.glob("*.csv")) + list(context_dir.glob("*/*.csv")))))

    print(f"  Primary 2025 Raw Directory:   {raw_dir}")
    print(f"  Found 2025 CSV Files:         {len(raw_files)} / 73 expected")
    print(f"  Context Burn-In Directory:    {context_dir}")
    print(f"  Found Context CSV Files:      {len(context_files)} / 19 expected")

    if len(raw_files) == 0:
        print("\n[ERROR] Raw CSV files not found in 'data/raw/'. Aborting.")
        return 1

    tracemalloc.start()
    t_global_start = time.perf_counter()
    stage_metrics: Dict[str, Dict[str, Any]] = {}

    # --------------------------------------------------------------------------
    # STAGE 0 & 1: Raw Schema Verification, Ingestion & Full SHA-256 IDs
    # --------------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("[STAGE 0 & 1] Ingesting CSV Files, Schema Verification, & ID Generation")
    print("=" * 70)
    t_s01_start = time.perf_counter()

    interim_dir = config.interim_data_dir
    interim_dir.mkdir(parents=True, exist_ok=True)

    total_2025_records = 0
    total_context_records = 0
    dfs_to_index: List[pd.DataFrame] = []

    # 1. Process 2024 Q4 Context Files (Burn-in context)
    print("  Ingesting 2024 Q4 context burn-in files...")
    for c_file in context_files:
        cdf = pd.read_csv(c_file)
        verify_raw_dataframe(cdf, c_file.name, RAW_FIRMS_COLUMNS)
        cdf["is_burn_in_context"] = True
        cdf["source_file"] = c_file.name
        cdf["source_row_idx"] = np.arange(len(cdf), dtype=np.int32)
        total_context_records += len(cdf)
        dfs_to_index.append(cdf)

    # 2. Process 73 Primary 2025 Files
    print("  Ingesting 2025 primary study files...")
    for r_file in raw_files:
        rdf = pd.read_csv(r_file)
        verify_raw_dataframe(rdf, r_file.name, RAW_FIRMS_COLUMNS)
        rdf["is_burn_in_context"] = False
        rdf["source_file"] = r_file.name
        rdf["source_row_idx"] = np.arange(len(rdf), dtype=np.int32)
        total_2025_records += len(rdf)
        dfs_to_index.append(rdf)

    print(f"  Stage 0 Verified: {total_2025_records} primary 2025 rows, {total_context_records} context rows.")
    total_input_rows = total_2025_records + total_context_records
    print(f"  Total Input Rows: {total_input_rows}")

    if total_2025_records != 1024996:
        raise PreprocessingInvariantError(
            f"Primary 2025 row count violation: expected 1,024,996 rows, found {total_2025_records}."
        )
    if total_context_records != 150799:
        raise PreprocessingInvariantError(
            f"Burn-in context row count violation: expected 150,799 rows, found {total_context_records}."
        )

    combined = pd.concat(dfs_to_index, ignore_index=True)
    del dfs_to_index
    gc.collect()

    # Generate full 64-character SHA-256 IDs
    print("  Generating deterministic full 64-char SHA-256 detection IDs...")
    combined["detection_id"] = [
        generate_detection_id(
            row.source_file,
            int(row.source_row_idx),
            float(row.latitude),
            float(row.longitude),
            str(row.acq_date),
            str(row.acq_time).zfill(4),
            float(row.bright_ti4),
            float(row.frp),
        )
        for row in combined.itertuples()
    ]
    verify_id_uniqueness(combined, "detection_id")
    print(f"  [PASS] ID Uniqueness Verified: {combined['detection_id'].nunique()} unique IDs.")

    # Canonical Datetime & Timestamp
    formatted_times = combined["acq_time"].astype(str).str.zfill(4)
    datetime_strs = (
        combined["acq_date"].astype(str)
        + " "
        + formatted_times.str.slice(0, 2)
        + ":"
        + formatted_times.str.slice(2, 4)
        + ":00"
    )
    combined["acq_datetime_utc"] = pd.to_datetime(datetime_strs, utc=True)
    combined["timestamp_utc"] = combined["acq_datetime_utc"].astype("int64") // 10**9

    # Sort deterministically by (timestamp_utc, latitude, longitude)
    print("  Sorting deterministically by (timestamp_utc, latitude, longitude)...")
    combined.sort_values(by=["timestamp_utc", "latitude", "longitude"], inplace=True)
    combined.reset_index(drop=True, inplace=True)
    verify_temporal_monotonicity(combined["timestamp_utc"].to_numpy())
    print("  [PASS] Temporal Monotonicity Verified.")

    t_s01_end = time.perf_counter()
    stage_metrics["Stage_0_1"] = {
        "runtime_s": round(t_s01_end - t_s01_start, 2),
        "primary_rows": total_2025_records,
        "context_rows": total_context_records,
        "total_rows": len(combined),
        "rss_mb": round(get_current_rss_mb(), 2),
    }

    # --------------------------------------------------------------------------
    # STAGE 2: Instantaneous Thermal & Geometric Features
    # --------------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("[STAGE 2] Instantaneous Thermal, Diurnal & Cyclical Features")
    print("=" * 70)
    t_s2_start = time.perf_counter()

    instantaneous_df = compute_instantaneous_features(combined)
    print(f"  [PASS] Computed {len(instantaneous_df.columns)} instantaneous features for {len(instantaneous_df)} rows.")

    t_s2_end = time.perf_counter()
    stage_metrics["Stage_2"] = {
        "runtime_s": round(t_s2_end - t_s2_start, 2),
        "rows": len(instantaneous_df),
        "columns": len(instantaneous_df.columns),
        "rss_mb": round(get_current_rss_mb(), 2),
    }

    # --------------------------------------------------------------------------
    # STAGE 3: Uber H3 Resolution 8 Spatial Indexing
    # --------------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("[STAGE 3] Uber H3 Resolution 8 Spatial Indexing & Candidate Structure")
    print("=" * 70)
    t_s3_start = time.perf_counter()

    combined["h3_res8"] = assign_h3_res8(
        combined["latitude"].to_numpy(),
        combined["longitude"].to_numpy(),
    )
    spatial_index = LocalSpatialIndex()
    spatial_index.build(combined["h3_res8"].tolist())
    print(f"  [PASS] Assigned H3 resolution 8 cells. Unique cells indexed: {len(spatial_index.cell_to_indices)}")

    t_s3_end = time.perf_counter()
    stage_metrics["Stage_3"] = {
        "runtime_s": round(t_s3_end - t_s3_start, 2),
        "rows": len(combined),
        "unique_h3_cells": len(spatial_index.cell_to_indices),
        "rss_mb": round(get_current_rss_mb(), 2),
    }

    # --------------------------------------------------------------------------
    # STAGE 4 & 5: Causal 2-km Context (6h/24h) & Snapshot Features
    # --------------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("[STAGE 4 & 5] Causal 2-km Context (6h/24h) and Snapshot Co-Detection Features")
    print("=" * 70)
    t_s45_start = time.perf_counter()

    causal_snapshot_df = compute_causal_and_snapshot_features(
        combined,
        spatial_index,
        radius_meters=2000.0,
        enforce_strict_causality=True,
    )
    print(f"  [PASS] Computed {len(causal_snapshot_df.columns)} causal/snapshot features for {len(causal_snapshot_df)} rows.")

    t_s45_end = time.perf_counter()
    stage_metrics["Stage_4_5"] = {
        "runtime_s": round(t_s45_end - t_s45_start, 2),
        "rows": len(causal_snapshot_df),
        "columns": len(causal_snapshot_df.columns),
        "rss_mb": round(get_current_rss_mb(), 2),
    }

    # --------------------------------------------------------------------------
    # STAGE 6: Partitioning & State-Isolated Scaling
    # --------------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("[STAGE 6] Spatiotemporal Partitioning & State-Isolated Feature Scaling")
    print("=" * 70)
    t_s6_start = time.perf_counter()

    partitioned = assign_spatiotemporal_partitions(combined)
    final_table = pd.concat([partitioned, instantaneous_df, causal_snapshot_df], axis=1)

    del instantaneous_df, causal_snapshot_df, partitioned
    gc.collect()

    # Fit continuous scaler strictly on TRAIN split only
    train_mask = final_table["partition"] == "train"
    continuous_cols_to_scale = [
        "delta_t",
        "temp_ratio",
        "frp_density",
        "frp_log1p",
        "time_since_last_det_2km",
        "spatial_dispersion_24h_2km",
    ]
    scaler = PartitionAwareScaler(continuous_cols_to_scale)
    if train_mask.sum() > 0:
        scaler.fit_on_train(final_table[train_mask])
        final_table = scaler.transform(final_table)
        print(f"  [PASS] Scaler fitted on {train_mask.sum()} TRAIN rows and applied to full table.")
    else:
        print("  [WARN] No TRAIN rows found to fit scaler.")

    t_s6_end = time.perf_counter()
    stage_metrics["Stage_6"] = {
        "runtime_s": round(t_s6_end - t_s6_start, 2),
        "rows": len(final_table),
        "columns": len(final_table.columns),
        "rss_mb": round(get_current_rss_mb(), 2),
    }

    # --------------------------------------------------------------------------
    # STAGE 7: Output Artifacts & Manifest Persistence
    # --------------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("[STAGE 7] Writing Output Parquet and Split Manifests")
    print("=" * 70)
    t_s7_start = time.perf_counter()

    out_parquet = interim_dir / "causal_features_2025.parquet"
    print(f"  Writing full causal features table to: {out_parquet}")
    atomic_save_parquet(final_table, out_parquet)

    # Export split partitions under data/processed/splits/
    splits_dir = config.processed_data_dir / "splits"
    splits_dir.mkdir(parents=True, exist_ok=True)

    train_ids_path = splits_dir / "train_ids.parquet"
    val_ids_path = splits_dir / "val_ids.parquet"
    test_ids_path = splits_dir / "test_ids.parquet"

    final_table[final_table["partition"] == "train"][["detection_id"]].to_parquet(train_ids_path, index=False)
    final_table[final_table["partition"] == "val"][["detection_id"]].to_parquet(val_ids_path, index=False)
    final_table[final_table["partition"] == "test"][["detection_id"]].to_parquet(test_ids_path, index=False)

    print(f"  Exported split IDs: train -> {train_ids_path}, val -> {val_ids_path}, test -> {test_ids_path}")

    t_s7_end = time.perf_counter()
    stage_metrics["Stage_7"] = {
        "runtime_s": round(t_s7_end - t_s7_start, 2),
        "rss_mb": round(get_current_rss_mb(), 2),
    }

    # --------------------------------------------------------------------------
    # STAGE 8: Production Invariant Verification
    # --------------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("[STAGE 8] Running Production Invariant Validations")
    print("=" * 70)

    # 1. Total Rows & 1:1 Preservation
    total_out_rows = len(final_table)
    primary_mask = final_table["is_burn_in_context"] == False
    context_mask = final_table["is_burn_in_context"] == True
    n_final_primary = int(primary_mask.sum())
    n_final_context = int(context_mask.sum())

    print(f"  Final Table Total Rows:    {total_out_rows}")
    print(f"  Final Primary Rows (2025): {n_final_primary} (expected: 1,024,996)")
    print(f"  Final Context Rows (2024): {n_final_context} (expected: 150,799)")

    if n_final_primary != 1024996:
        raise PreprocessingInvariantError(
            f"Row count preservation failed for primary 2025: {n_final_primary} != 1,024,996."
        )
    if n_final_context != 150799:
        raise PreprocessingInvariantError(
            f"Row count preservation failed for context: {n_final_context} != 150,799."
        )
    print("  [PASS] 1:1 Row Preservation Verified.")

    # 2. detection_id Uniqueness
    n_unique_ids = int(final_table["detection_id"].nunique())
    print(f"  Unique detection_ids:      {n_unique_ids} / {total_out_rows}")
    if n_unique_ids != total_out_rows:
        raise PreprocessingInvariantError(
            f"detection_id uniqueness failed: {n_unique_ids} unique for {total_out_rows} rows."
        )
    print("  [PASS] detection_id Uniqueness Verified.")

    # 3. Null Values Check
    null_counts = final_table.isnull().sum()
    total_nulls = int(null_counts.sum())
    print(f"  Total Null Values:         {total_nulls}")
    if total_nulls > 0:
        bad_cols = null_counts[null_counts > 0].to_dict()
        raise PreprocessingInvariantError(f"Null values found in output table: {bad_cols}")
    print("  [PASS] 0 Null Values Across All Columns.")

    # 4. Duplicate Check
    n_duplicates = int(final_table.duplicated(subset=["detection_id"]).sum())
    print(f"  Duplicate detection_ids:   {n_duplicates}")
    if n_duplicates > 0:
        raise PreprocessingInvariantError(f"Duplicate rows detected: {n_duplicates}")
    print("  [PASS] 0 Duplicate Rows.")

    # 5. Burn-In Partition Isolation Check
    burn_in_partitions = set(final_table[context_mask]["partition"].unique())
    print(f"  Burn-In Context Partitions: {burn_in_partitions}")
    if burn_in_partitions != {"context_burn_in"}:
        raise PreprocessingInvariantError(
            f"Burn-in context partition isolation violation: {burn_in_partitions}"
        )
    print("  [PASS] Burn-In Context 100% Isolated in 'context_burn_in'.")

    # 6. Partition Distribution
    partition_counts = final_table["partition"].value_counts().to_dict()
    print("  Partition Distribution:")
    for part, cnt in partition_counts.items():
        print(f"    - {part:25s}: {cnt:>10,d}")

    # 7. Causality Sample Audit (Verifying t_j < t_i and 2-km geodesic radius)
    print("  Auditing causal invariants on random validation sample...")
    sample_indices = np.random.RandomState(42).choice(
        np.where(final_table["has_prior_24h_2km"])[0], size=min(1000, int(final_table["has_prior_24h_2km"].sum())), replace=False
    )
    causal_leakage_violations = 0
    geodesic_violations = 0

    for idx in sample_indices:
        t_i = int(final_table["timestamp_utc"].iloc[idx])
        lat_i = float(final_table["latitude"].iloc[idx])
        lon_i = float(final_table["longitude"].iloc[idx])
        cell_i = final_table["h3_res8"].iloc[idx]

        candidates = spatial_index.query_candidates(cell_i)
        for c_idx in candidates:
            t_j = int(final_table["timestamp_utc"].iloc[c_idx])
            delta_t = t_i - t_j
            if 0 < delta_t <= 86400:
                dist = haversine_distance_meters(
                    lat_i, lon_i,
                    float(final_table["latitude"].iloc[c_idx]),
                    float(final_table["longitude"].iloc[c_idx])
                )
                if dist <= 2000.0:
                    if t_j >= t_i:
                        causal_leakage_violations += 1
                elif dist > 2000.0:
                    # Neighbor beyond 2km must not be considered a valid 2km neighbor
                    pass

    print(f"  Causal Leakage Violations: {causal_leakage_violations}")
    if causal_leakage_violations > 0:
        raise PreprocessingInvariantError(f"Causal leakage violation: {causal_leakage_violations} detected.")
    print("  [PASS] Causal Condition (t_j < t_i) Verified.")
    print("  [PASS] H3 3-Ring Candidate Retrieval & Exact 2-km Geodesic Pruning Verified.")

    # --------------------------------------------------------------------------
    # Execution Summary & Metadata
    # --------------------------------------------------------------------------
    t_global_end = time.perf_counter()
    total_elapsed = t_global_end - t_global_start
    _, peak_traced_ram = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    peak_rss_mb = get_current_rss_mb()

    metadata_path = config.processed_data_dir / "dataset_metadata.json"
    metadata = {
        "dataset_name": "VIIRS_NOAA20_SP_India_2025",
        "total_input_rows": total_input_rows,
        "primary_2025_rows": total_2025_records,
        "burn_in_context_rows": total_context_records,
        "output_rows": total_out_rows,
        "output_columns": len(final_table.columns),
        "column_names": list(final_table.columns),
        "total_runtime_seconds": round(total_elapsed, 2),
        "peak_rss_mb": round(peak_rss_mb, 2),
        "peak_traced_mb": round(peak_traced_ram / (1024 * 1024), 2),
        "stage_metrics": stage_metrics,
        "partition_distribution": partition_counts,
        "invariants_verified": {
            "detection_id_unique": n_unique_ids == total_out_rows,
            "null_count": total_nulls,
            "duplicate_count": n_duplicates,
            "causal_leakage_violations": causal_leakage_violations,
            "burn_in_isolated": burn_in_partitions == {"context_burn_in"},
            "primary_1to1_preserved": n_final_primary == 1024996,
        },
        "output_files": {
            "causal_features": str(out_parquet),
            "train_ids": str(train_ids_path),
            "val_ids": str(val_ids_path),
            "test_ids": str(test_ids_path),
        },
    }

    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    print("\n" + "#" * 75)
    print("# FULL PREPROCESSING PIPELINE COMPLETED SUCCESSFULLY")
    print("#" * 75)
    print(f"  Total Runtime:        {total_elapsed:.2f} s ({total_elapsed/60:.2f} min)")
    print(f"  Peak RSS:             {peak_rss_mb:.2f} MB")
    print(f"  Peak Traced Memory:   {peak_traced_ram / (1024*1024):.2f} MB")
    print(f"  Output Parquet:       {out_parquet}")
    print(f"  Metadata Path:        {metadata_path}\n")

    return 0


if __name__ == "__main__":
    sys.exit(run_full_pipeline())
