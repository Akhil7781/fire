"""
Chunked, memory-safe preprocessing pipeline orchestrating Stages 0 through 6.
"""

from __future__ import annotations

import gc
import json
import time
import tracemalloc
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from src.data.schema import (
    RAW_FIRMS_COLUMNS,
    generate_detection_id,
    MASTER_PARQUET_SCHEMA,
)
from src.data.invariants import (
    verify_raw_dataframe,
    verify_id_uniqueness,
    verify_temporal_monotonicity,
    verify_causal_history,
    PreprocessingInvariantError,
)
from src.data.instantaneous import compute_instantaneous_features
from src.data.spatial_index import assign_h3_res8, LocalSpatialIndex
from src.data.causal_context import compute_causal_and_snapshot_features
from src.data.partitions import assign_spatiotemporal_partitions, PartitionAwareScaler


class PreprocessingPipeline:
    """
    Executes the modular preprocessing pipeline with memory tracking and strict invariant enforcement.
    """

    def __init__(self, output_dir: Path, chunk_size: int = 50000):
        self.output_dir = Path(output_dir)
        self.chunk_size = chunk_size
        self.metrics: Dict[str, any] = {}

    def run_on_dataframe(
        self,
        raw_2025_df: pd.DataFrame,
        context_burn_in_df: Optional[pd.DataFrame] = None,
        source_name_2025: str = "validation_slice_2025.csv",
        source_name_context: str = "burn_in_context_2024.csv",
    ) -> Dict[str, any]:
        """
        Executes all preprocessing stages on provided dataframes (used for validation slice
        or in-memory evaluation).
        """
        tracemalloc.start()
        start_time = time.perf_counter()
        stage_counts: Dict[str, int] = {}

        # ----------------------------------------------------------------------
        # STAGE 0: Raw Data Integrity & Schema Verification
        # ----------------------------------------------------------------------
        verify_raw_dataframe(raw_2025_df, source_name_2025, RAW_FIRMS_COLUMNS)
        n_2025_raw = len(raw_2025_df)
        stage_counts["stage0_2025_raw_records"] = n_2025_raw

        has_context = context_burn_in_df is not None and len(context_burn_in_df) > 0
        if has_context:
            verify_raw_dataframe(context_burn_in_df, source_name_context, RAW_FIRMS_COLUMNS)
            stage_counts["stage0_context_burn_in_records"] = len(context_burn_in_df)
        else:
            stage_counts["stage0_context_burn_in_records"] = 0

        # ----------------------------------------------------------------------
        # STAGE 1: Full SHA-256 ID Assignment & Canonical Datetime Ingestion
        # ----------------------------------------------------------------------
        records = []
        # Ingest 2024 Q4 context burn-in if present
        if has_context:
            df_ctx = context_burn_in_df.copy()
            df_ctx["is_burn_in_context"] = True
            df_ctx["source_file"] = source_name_context
            df_ctx["source_row_idx"] = np.arange(len(df_ctx), dtype=np.int32)
            records.append(df_ctx)

        # Ingest 2025 primary study dataset
        df_2025 = raw_2025_df.copy()
        df_2025["is_burn_in_context"] = False
        df_2025["source_file"] = source_name_2025
        df_2025["source_row_idx"] = np.arange(len(df_2025), dtype=np.int32)
        records.append(df_2025)

        combined = pd.concat(records, ignore_index=True)
        stage_counts["stage1_ingested_total"] = len(combined)

        # Compute full 64-character SHA-256 IDs
        detection_ids = [
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
        combined["detection_id"] = detection_ids

        # Uniqueness assertion on detection_id
        verify_id_uniqueness(combined, "detection_id")

        # Parse canonical UTC datetimes and Unix epoch timestamps
        # Handle acq_time zero-padding: e.g., '35' -> '0035'
        formatted_times = combined["acq_time"].astype(str).str.zfill(4)
        datetime_strs = combined["acq_date"].astype(str) + " " + formatted_times.str.slice(0, 2) + ":" + formatted_times.str.slice(2, 4) + ":00"
        combined["acq_datetime_utc"] = pd.to_datetime(datetime_strs, utc=True)
        combined["timestamp_utc"] = combined["acq_datetime_utc"].astype("int64") // 10**9

        # Sort deterministically by (timestamp_utc, latitude, longitude)
        combined.sort_values(by=["timestamp_utc", "latitude", "longitude"], inplace=True)
        combined.reset_index(drop=True, inplace=True)
        verify_temporal_monotonicity(combined["timestamp_utc"].to_numpy())

        # ----------------------------------------------------------------------
        # STAGE 2: Deterministic Instantaneous Feature Generation (Stateless)
        # ----------------------------------------------------------------------
        instantaneous_df = compute_instantaneous_features(combined)
        stage_counts["stage2_instantaneous_records"] = len(instantaneous_df)

        # ----------------------------------------------------------------------
        # STAGE 3: Uber H3 Resolution 8 Geographic Context Indexing
        # ----------------------------------------------------------------------
        h3_res8_cells = assign_h3_res8(
            combined["latitude"].to_numpy(),
            combined["longitude"].to_numpy(),
        )
        combined["h3_res8"] = h3_res8_cells
        stage_counts["stage3_h3_assigned"] = len(h3_res8_cells)

        # Build local spatial candidate index
        spatial_index = LocalSpatialIndex()
        spatial_index.build(h3_res8_cells)

        # ----------------------------------------------------------------------
        # STAGE 4 & 5: Causal 2-km (6h/24h) and Snapshot Contemporaneous Features
        # ----------------------------------------------------------------------
        causal_and_snapshot_df = compute_causal_and_snapshot_features(
            combined,
            spatial_index,
            radius_meters=2000.0,
            enforce_strict_causality=True,
        )
        stage_counts["stage4_5_causal_snapshot_records"] = len(causal_and_snapshot_df)

        # ----------------------------------------------------------------------
        # STAGE 6: Partitioning & State Isolation
        # ----------------------------------------------------------------------
        partitioned_combined = assign_spatiotemporal_partitions(combined)
        stage_counts["stage6_partitioned_records"] = len(partitioned_combined)

        # Merge all tabular feature sets into a master feature table
        final_table = pd.concat([partitioned_combined, instantaneous_df, causal_and_snapshot_df], axis=1)

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
            scaled_final_table = scaler.transform(final_table)
        else:
            scaled_final_table = final_table

        # Measure performance and memory
        elapsed_sec = time.perf_counter() - start_time
        current_ram, peak_ram = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # Save artifacts to interim/
        self.output_dir.mkdir(parents=True, exist_ok=True)
        out_parquet_path = self.output_dir / "validation_slice_features.parquet"
        scaled_final_table.to_parquet(out_parquet_path, index=False)

        metrics = {
            "runtime_seconds": round(elapsed_sec, 3),
            "peak_memory_mb": round(peak_ram / (1024 * 1024), 2),
            "stage_counts": stage_counts,
            "output_path": str(out_parquet_path),
            "total_columns": len(scaled_final_table.columns),
            "partition_distribution": scaled_final_table["partition"].value_counts().to_dict(),
        }
        self.metrics = metrics
        return metrics
