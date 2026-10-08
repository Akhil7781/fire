"""
Stage 8.2: TCN + Deep SAD Multimodal Representation Alignment Pipeline.

Aligns frozen 64-dimensional temporal convolutional representations (z_TCN)
with frozen 32-dimensional Deep SAD combustion anomaly representations (z_SAD)
strictly across the 1,024,996 operational FIRMS detections in India (2025).

Invariants:
  1. Operates ONLY on the 5 operational partitions:
     - train (578,465)
     - train_heldout_spatial (277,395)
     - test_seen_spatial (91,846)
     - test (47,881)
     - val (29,409)
     Total = 1,024,996 detections.
  2. context_burn_in (150,799 detections) is explicitly excluded.
  3. Relational join is keyed strictly on canonical `detection_id`.
  4. Final artifact structure:
     - 6 metadata columns: detection_id, sequence_id, acq_datetime_utc,
       timestamp_utc, partition, active_timesteps
     - 64 z_TCN columns: z_tcn_0 ... z_tcn_63
     - 32 z_SAD columns: z_sad_0 ... z_sad_31
     Total columns = 102.
  5. Bit-level value preservation: All z_TCN and z_SAD values are preserved
     without numerical drift or imputation.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


OPERATIONAL_PARTITIONS = (
    "train",
    "train_heldout_spatial",
    "val",
    "test",
    "test_seen_spatial",
)

METADATA_COLUMNS = [
    "detection_id",
    "sequence_id",
    "acq_datetime_utc",
    "timestamp_utc",
    "partition",
    "active_timesteps",
]

Z_TCN_COLUMNS = [f"z_tcn_{i}" for i in range(64)]
Z_SAD_COLUMNS = [f"z_sad_{i}" for i in range(32)]
ALL_ALIGNED_COLUMNS = METADATA_COLUMNS + Z_TCN_COLUMNS + Z_SAD_COLUMNS

EXPECTED_OPERATIONAL_ROWS = 1_024_996
EXPECTED_COLUMNS_COUNT = 102


class RepresentationAlignmentPipeline:
    """
    Executes relational alignment of TCN (64-D) and Deep SAD (32-D) representations.
    """

    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = Path(project_root) if project_root else Path("d:/DATA PREPROCESSING")
        self.tcn_parquet_path = (
            self.project_root / "data" / "embeddings" / "tcn" / "india_2025_embeddings.parquet"
        )
        self.causal_features_path = (
            self.project_root / "data" / "interim" / "causal_features_2025.parquet"
        )
        self.deep_sad_dir = self.project_root / "data" / "embeddings" / "deep_sad"
        self.output_dir = self.project_root / "data" / "embeddings" / "fusion"
        self.output_parquet_path = self.output_dir / "india_2025_tcn_sad_aligned.parquet"
        self.summary_json_path = self.output_dir / "india_2025_tcn_sad_aligned_summary.json"

    def load_operational_tcn_embeddings(self) -> pd.DataFrame:
        """
        Loads TCN embeddings for the 1,024,996 operational detections,
        filtering out the context_burn_in partition.
        """
        logger.info(f"Loading TCN embeddings from {self.tcn_parquet_path}...")
        tcn_df = pd.read_parquet(self.tcn_parquet_path)
        logger.info(f"Full TCN embeddings shape: {tcn_df.shape}")

        # Verify initial invariants
        assert len(tcn_df) == 1_175_795, f"Expected 1,175,795 TCN rows, got {len(tcn_df)}"
        assert tcn_df["detection_id"].nunique() == 1_175_795, "Duplicate detection_id in TCN!"

        # Filter strictly to operational partitions
        op_mask = tcn_df["partition"].isin(OPERATIONAL_PARTITIONS)
        op_tcn_df = tcn_df[op_mask].copy().reset_index(drop=True)
        logger.info(
            f"Filtered TCN to operational partitions: {len(op_tcn_df):,} rows "
            f"(excluded {len(tcn_df) - len(op_tcn_df):,} context_burn_in rows)"
        )

        assert len(op_tcn_df) == EXPECTED_OPERATIONAL_ROWS, (
            f"Expected {EXPECTED_OPERATIONAL_ROWS:,} operational TCN rows, got {len(op_tcn_df):,}"
        )
        return op_tcn_df

    def load_operational_deep_sad_embeddings(self) -> pd.DataFrame:
        """
        Loads Deep SAD embeddings from partition .npy files and associates
        each array row with its canonical detection_id from causal_features_2025.parquet.
        """
        logger.info(f"Loading causal features index from {self.causal_features_path}...")
        cf_df = pd.read_parquet(
            self.causal_features_path, columns=["detection_id", "partition"]
        )

        sad_partition_map = [
            ("train", "train", "train_embeddings.npy"),
            ("val", "val", "val_embeddings.npy"),
            ("heldout_spatial", "train_heldout_spatial", "heldout_spatial_embeddings.npy"),
            ("test", "test", "test_embeddings.npy"),
            ("test_seen_spatial", "test_seen_spatial", "test_seen_spatial_embeddings.npy"),
        ]

        part_dfs: List[pd.DataFrame] = []
        total_loaded = 0

        for sad_part_name, cf_partition_val, npy_filename in sad_partition_map:
            npy_path = self.deep_sad_dir / npy_filename
            if not npy_path.exists():
                raise FileNotFoundError(f"Deep SAD embedding file not found: {npy_path}")

            emb_arr = np.load(npy_path)
            part_mask = cf_df["partition"] == cf_partition_val
            part_ids = cf_df.loc[part_mask, "detection_id"].values

            if len(part_ids) != len(emb_arr):
                raise ValueError(
                    f"Partition size mismatch in {sad_part_name}: "
                    f"{len(part_ids)} causal_features IDs vs {len(emb_arr)} Deep SAD embeddings"
                )

            part_df = pd.DataFrame(emb_arr, columns=Z_SAD_COLUMNS)
            part_df["detection_id"] = part_ids
            part_df["sad_partition"] = cf_partition_val

            part_dfs.append(part_df)
            total_loaded += len(emb_arr)
            logger.info(f"  Loaded {sad_part_name} ({cf_partition_val}): {len(emb_arr):,} rows")

        assert total_loaded == EXPECTED_OPERATIONAL_ROWS, (
            f"Expected {EXPECTED_OPERATIONAL_ROWS:,} Deep SAD rows, got {total_loaded:,}"
        )

        sad_df = pd.concat(part_dfs, ignore_index=True)
        assert sad_df["detection_id"].nunique() == EXPECTED_OPERATIONAL_ROWS, (
            "Duplicate detection_id in constructed Deep SAD table!"
        )
        logger.info(f"Total operational Deep SAD embeddings loaded: {len(sad_df):,} rows")
        return sad_df

    def align_representations(
        self, tcn_df: pd.DataFrame, sad_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Performs inner join on canonical detection_id and validates all invariants.
        """
        logger.info("Executing relational inner join on `detection_id`...")
        merged_df = pd.merge(
            tcn_df,
            sad_df,
            on="detection_id",
            how="inner",
            validate="one_to_one",
        )
        logger.info(f"Joined dataframe shape: {merged_df.shape}")

        # 1. Row count validation
        if len(merged_df) != EXPECTED_OPERATIONAL_ROWS:
            raise ValueError(
                f"Row count mismatch: expected {EXPECTED_OPERATIONAL_ROWS:,}, got {len(merged_df):,}"
            )

        # 2. Partition consistency check
        partition_mismatches = (merged_df["partition"] != merged_df["sad_partition"]).sum()
        if partition_mismatches > 0:
            raise ValueError(f"Found {partition_mismatches} partition mismatches between TCN and Deep SAD!")
        logger.info("Partition consistency check passed (0 mismatches).")

        # 3. Drop auxiliary partition column and reorder to canonical schema
        merged_df = merged_df.drop(columns=["sad_partition"])
        aligned_df = merged_df[ALL_ALIGNED_COLUMNS].copy()

        # 4. Invariant Validations
        self._validate_invariants(aligned_df, tcn_df, sad_df)
        return aligned_df

    def _validate_invariants(
        self,
        aligned_df: pd.DataFrame,
        orig_tcn_df: pd.DataFrame,
        orig_sad_df: pd.DataFrame,
    ) -> None:
        """
        Performs exhaustive mathematical, relational, and schema invariant checks.
        """
        logger.info("Validating exhaustive Stage 8.2 invariants...")

        # Invariant 1: Exactly 1,024,996 rows
        assert len(aligned_df) == EXPECTED_OPERATIONAL_ROWS, (
            f"Expected {EXPECTED_OPERATIONAL_ROWS:,} rows, got {len(aligned_df):,}"
        )

        # Invariant 2: detection_id unique
        assert aligned_df["detection_id"].nunique() == EXPECTED_OPERATIONAL_ROWS, (
            "detection_id is not unique in aligned artifact!"
        )

        # Invariant 3: Operational partitions only (zero context_burn_in)
        assert set(aligned_df["partition"].unique()) == set(OPERATIONAL_PARTITIONS), (
            f"Unexpected partitions: {aligned_df['partition'].unique()}"
        )
        assert "context_burn_in" not in aligned_df["partition"].values, (
            "context_burn_in leaked into aligned artifact!"
        )

        # Invariant 4 & 5: Exact column counts
        assert len(aligned_df.columns) == EXPECTED_COLUMNS_COUNT, (
            f"Expected {EXPECTED_COLUMNS_COUNT} columns, got {len(aligned_df.columns)}"
        )
        assert list(aligned_df.columns) == ALL_ALIGNED_COLUMNS, "Column schema/ordering mismatch!"

        # Invariant 6 & 7: Zero NaN / Inf
        z_tcn_vals = aligned_df[Z_TCN_COLUMNS].to_numpy(dtype=np.float32)
        z_sad_vals = aligned_df[Z_SAD_COLUMNS].to_numpy(dtype=np.float32)

        nan_tcn = int(np.isnan(z_tcn_vals).sum())
        nan_sad = int(np.isnan(z_sad_vals).sum())
        inf_tcn = int(np.isinf(z_tcn_vals).sum())
        inf_sad = int(np.isinf(z_sad_vals).sum())

        assert nan_tcn == 0, f"Found {nan_tcn} NaNs in z_TCN!"
        assert nan_sad == 0, f"Found {nan_sad} NaNs in z_SAD!"
        assert inf_tcn == 0, f"Found {inf_tcn} Infs in z_TCN!"
        assert inf_sad == 0, f"Found {inf_sad} Infs in z_SAD!"

        # Invariant 8: Zero duplicate IDs
        dup_count = int(aligned_df["detection_id"].duplicated().sum())
        assert dup_count == 0, f"Found {dup_count} duplicate detection_ids!"

        # Invariant 9: Zero partition mismatches (already verified during join)

        # Invariant 10: All original operational detection IDs represented exactly once
        orig_ids_set = set(orig_tcn_df["detection_id"])
        aligned_ids_set = set(aligned_df["detection_id"])
        assert orig_ids_set == aligned_ids_set, "Set difference between original and aligned IDs!"

        # Invariant 11: TCN values unchanged after join
        # Re-index original by detection_id to compare values directly
        orig_tcn_indexed = orig_tcn_df.set_index("detection_id")[Z_TCN_COLUMNS]
        aligned_tcn_indexed = aligned_df.set_index("detection_id")[Z_TCN_COLUMNS]
        aligned_tcn_indexed = aligned_tcn_indexed.loc[orig_tcn_indexed.index]
        tcn_max_diff = float(np.max(np.abs(orig_tcn_indexed.values - aligned_tcn_indexed.values)))
        assert tcn_max_diff == 0.0, f"TCN values changed after join! Max diff = {tcn_max_diff}"
        logger.info(f"TCN values bit-level preservation verified: max absolute difference = {tcn_max_diff}")

        # Invariant 12: Deep SAD values unchanged after join
        orig_sad_indexed = orig_sad_df.set_index("detection_id")[Z_SAD_COLUMNS]
        aligned_sad_indexed = aligned_df.set_index("detection_id")[Z_SAD_COLUMNS]
        aligned_sad_indexed = aligned_sad_indexed.loc[orig_sad_indexed.index]
        sad_max_diff = float(np.max(np.abs(orig_sad_indexed.values - aligned_sad_indexed.values)))
        assert sad_max_diff == 0.0, f"Deep SAD values changed after join! Max diff = {sad_max_diff}"
        logger.info(f"Deep SAD values bit-level preservation verified: max absolute difference = {sad_max_diff}")

        logger.info("All 12 invariant validations PASSED.")

    def run_alignment(self) -> Dict:
        """
        Executes full alignment pipeline, saves parquet and metadata summary.
        """
        self.output_dir.mkdir(parents=True, exist_ok=True)

        tcn_df = self.load_operational_tcn_embeddings()
        sad_df = self.load_operational_deep_sad_embeddings()
        aligned_df = self.align_representations(tcn_df, sad_df)

        logger.info(f"Writing aligned representations to {self.output_parquet_path}...")
        # Write to parquet with zstd compression
        table = pa.Table.from_pandas(aligned_df, preserve_index=False)
        pq.write_table(
            table,
            self.output_parquet_path,
            compression="zstd",
            compression_level=7,
        )
        file_size_mb = self.output_parquet_path.stat().st_size / (1024 * 1024)
        logger.info(f"Successfully written {self.output_parquet_path} ({file_size_mb:.2f} MB)")

        # Prepare summary dictionary
        partition_counts = aligned_df["partition"].value_counts().to_dict()
        summary = {
            "status": "COMPLETED",
            "artifact_path": str(self.output_parquet_path),
            "file_size_mb": round(file_size_mb, 2),
            "total_rows": len(aligned_df),
            "total_columns": len(aligned_df.columns),
            "metadata_columns": len(METADATA_COLUMNS),
            "z_tcn_dimensions": len(Z_TCN_COLUMNS),
            "z_sad_dimensions": len(Z_SAD_COLUMNS),
            "partition_counts": partition_counts,
            "nan_inf_count": 0,
            "duplicate_detection_ids": 0,
            "partition_mismatches": 0,
            "tcn_value_drift_max": 0.0,
            "sad_value_drift_max": 0.0,
            "operational_cohort_only": True,
            "context_burn_in_excluded": True,
        }

        with open(self.summary_json_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)
        logger.info(f"Saved summary to {self.summary_json_path}")

        return summary
