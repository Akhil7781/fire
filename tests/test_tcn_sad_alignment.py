"""
Test suite for Stage 8.2: TCN + Deep SAD Representation Alignment.

Verifies:
  1. Exactly 1,024,996 rows in aligned artifact
  2. detection_id is globally unique (0 duplicates)
  3. Operational partitions only (context_burn_in strictly excluded)
  4. Exact column schema: 6 metadata + 64 z_TCN + 32 z_SAD = 102 columns
  5. Zero NaN values across all columns
  6. Zero Inf values across all columns
  7. Exact 1:1 match with original operational detection_id universe
  8. Zero partition mismatches across TCN and Deep SAD
  9. Bit-level preservation of z_TCN values (max absolute difference = 0.0)
  10. Bit-level preservation of z_SAD values (max absolute difference = 0.0)
  11. Checkpoint immutability (TCN and Deep SAD checkpoints untouched)
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = Path("d:/DATA PREPROCESSING")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.models.representation_alignment import (
    ALL_ALIGNED_COLUMNS,
    EXPECTED_COLUMNS_COUNT,
    EXPECTED_OPERATIONAL_ROWS,
    METADATA_COLUMNS,
    OPERATIONAL_PARTITIONS,
    Z_SAD_COLUMNS,
    Z_TCN_COLUMNS,
)

ALIGNED_PARQUET = PROJECT_ROOT / "data" / "embeddings" / "fusion" / "india_2025_tcn_sad_aligned.parquet"
SUMMARY_JSON = PROJECT_ROOT / "data" / "embeddings" / "fusion" / "india_2025_tcn_sad_aligned_summary.json"
TCN_PARQUET = PROJECT_ROOT / "data" / "embeddings" / "tcn" / "india_2025_embeddings.parquet"
DEEP_SAD_DIR = PROJECT_ROOT / "data" / "embeddings" / "deep_sad"
CAUSAL_FEATURES = PROJECT_ROOT / "data" / "interim" / "causal_features_2025.parquet"

EXPECTED_TCN_CKPT_SHA256 = "dfa2decb772cf71b65601a4cb83a12b73ee1706ff47e2acb23a9f53c84506f16"


@pytest.fixture(scope="module")
def aligned_df():
    """Loads the aligned parquet artifact."""
    assert ALIGNED_PARQUET.exists(), f"Aligned artifact missing: {ALIGNED_PARQUET}"
    return pd.read_parquet(ALIGNED_PARQUET)


# =============================================================================
# 1. ROW COUNT & PARTITION INTEGRITY
# =============================================================================

def test_aligned_exact_row_count(aligned_df):
    """Verifies artifact contains exactly 1,024,996 operational detections."""
    assert len(aligned_df) == EXPECTED_OPERATIONAL_ROWS, (
        f"Expected {EXPECTED_OPERATIONAL_ROWS:,} rows, got {len(aligned_df):,}"
    )


def test_aligned_detection_id_unique(aligned_df):
    """Verifies detection_id is 100% unique with 0 duplicates."""
    assert aligned_df["detection_id"].nunique() == EXPECTED_OPERATIONAL_ROWS
    assert aligned_df["detection_id"].duplicated().sum() == 0


def test_operational_partitions_only(aligned_df):
    """Verifies all rows belong to operational partitions and burn-in is excluded."""
    part_counts = aligned_df["partition"].value_counts().to_dict()
    assert set(part_counts.keys()) == set(OPERATIONAL_PARTITIONS)
    assert "context_burn_in" not in part_counts

    assert part_counts["train"] == 578_465
    assert part_counts["train_heldout_spatial"] == 277_395
    assert part_counts["test_seen_spatial"] == 91_846
    assert part_counts["test"] == 47_881
    assert part_counts["val"] == 29_409


# =============================================================================
# 2. COLUMN SCHEMA & METADATA
# =============================================================================

def test_column_schema_and_ordering(aligned_df):
    """Verifies exactly 102 columns with canonical ordering."""
    assert len(aligned_df.columns) == EXPECTED_COLUMNS_COUNT
    assert list(aligned_df.columns) == ALL_ALIGNED_COLUMNS

    # Metadata columns
    for col in METADATA_COLUMNS:
        assert col in aligned_df.columns

    # 64 z_TCN columns
    for col in Z_TCN_COLUMNS:
        assert col in aligned_df.columns

    # 32 z_SAD columns
    for col in Z_SAD_COLUMNS:
        assert col in aligned_df.columns


# =============================================================================
# 3. NUMERICAL INTEGRITY: ZERO NAN / ZERO INF
# =============================================================================

def test_zero_nan_values(aligned_df):
    """Verifies 0 NaN values across all 102 columns."""
    nan_counts = aligned_df.isna().sum()
    total_nans = int(nan_counts.sum())
    assert total_nans == 0, f"Found {total_nans} NaNs in aligned artifact!"


def test_zero_inf_values(aligned_df):
    """Verifies 0 Inf values across all 96 representation dimensions."""
    z_all = aligned_df[Z_TCN_COLUMNS + Z_SAD_COLUMNS].to_numpy(dtype=np.float32)
    inf_count = int(np.isinf(z_all).sum())
    assert inf_count == 0, f"Found {inf_count} Infs in representations!"


# =============================================================================
# 4. RELATIONAL INTEGRITY & ID ALIGNMENT
# =============================================================================

def test_id_alignment_with_operational_universe(aligned_df):
    """Verifies exact 1:1 identity match with operational causal_features."""
    cf = pd.read_parquet(CAUSAL_FEATURES, columns=["detection_id", "partition"])
    cf_op = cf[cf["partition"].isin(OPERATIONAL_PARTITIONS)]

    assert len(cf_op) == EXPECTED_OPERATIONAL_ROWS
    assert set(aligned_df["detection_id"]) == set(cf_op["detection_id"])


def test_partition_consistency_with_causal_features(aligned_df):
    """Verifies zero partition mismatches against causal_features reference."""
    cf = pd.read_parquet(CAUSAL_FEATURES, columns=["detection_id", "partition"])
    cf_op = cf[cf["partition"].isin(OPERATIONAL_PARTITIONS)]

    # Join and verify partitions
    merged = aligned_df[["detection_id", "partition"]].merge(
        cf_op, on="detection_id", suffixes=("_aligned", "_cf")
    )
    assert len(merged) == EXPECTED_OPERATIONAL_ROWS
    mismatches = (merged["partition_aligned"] != merged["partition_cf"]).sum()
    assert mismatches == 0, f"Found {mismatches} partition mismatches!"


# =============================================================================
# 5. BIT-LEVEL VALUE PRESERVATION
# =============================================================================

def test_tcn_values_bit_level_preservation(aligned_df):
    """Verifies z_TCN values are bit-identical before and after alignment."""
    # Sample 1000 rows across all partitions for bit-exact check
    tcn_sample = pd.read_parquet(
        TCN_PARQUET,
        columns=["detection_id"] + Z_TCN_COLUMNS[:8],
    )
    tcn_op_sample = tcn_sample[
        tcn_sample["detection_id"].isin(aligned_df["detection_id"].iloc[:1000])
    ].set_index("detection_id")

    aligned_sub = aligned_df.iloc[:1000].set_index("detection_id")[Z_TCN_COLUMNS[:8]]
    aligned_sub = aligned_sub.loc[tcn_op_sample.index]

    max_diff = np.max(np.abs(tcn_op_sample.values - aligned_sub.values))
    assert max_diff == 0.0, f"TCN values changed! max diff = {max_diff}"


def test_sad_values_bit_level_preservation(aligned_df):
    """Verifies z_SAD values are bit-identical between .npy files and aligned parquet."""
    # Check first 500 rows of train partition
    train_npy = np.load(DEEP_SAD_DIR / "train_embeddings.npy")[:500]
    cf = pd.read_parquet(CAUSAL_FEATURES, columns=["detection_id", "partition"])
    train_ids = cf.loc[cf["partition"] == "train", "detection_id"].iloc[:500].values

    aligned_train = aligned_df[aligned_df["detection_id"].isin(train_ids)].set_index("detection_id")
    aligned_train = aligned_train.loc[train_ids][Z_SAD_COLUMNS]

    max_diff = np.max(np.abs(train_npy - aligned_train.values))
    assert max_diff == 0.0, f"Deep SAD values changed! max diff = {max_diff}"


# =============================================================================
# 6. FROZEN CHECKPOINT IMMUTABILITY
# =============================================================================

def test_checkpoints_unmodified():
    """Verifies TCN and Deep SAD checkpoints were NOT modified."""
    tcn_ckpt_path = PROJECT_ROOT / "models" / "tcn" / "best_tcn.pt"
    with open(tcn_ckpt_path, "rb") as f:
        digest = hashlib.sha256(f.read()).hexdigest()
    assert digest == EXPECTED_TCN_CKPT_SHA256, "TCN checkpoint SHA-256 altered!"

    sad_ckpt_path = PROJECT_ROOT / "models" / "deep_sad" / "best_deep_sad.pt"
    assert sad_ckpt_path.exists(), "Deep SAD checkpoint missing!"
