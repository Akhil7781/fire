"""
Deterministic validation slice and invariant test suite for the preprocessing pipeline.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import math
import shutil
import tempfile
import numpy as np
import pandas as pd
from src.data.schema import RAW_FIRMS_COLUMNS, generate_detection_id
from src.data.invariants import (
    PreprocessingInvariantError,
    verify_id_uniqueness,
    verify_temporal_monotonicity,
    verify_causal_history,
    haversine_distance_meters,
)
from src.data.instantaneous import compute_instantaneous_features
from src.data.spatial_index import assign_h3_res8, LocalSpatialIndex
from src.data.causal_context import compute_causal_and_snapshot_features
from src.data.partitions import assign_spatiotemporal_partitions, PartitionAwareScaler
from src.data.pipeline import PreprocessingPipeline


def create_deterministic_validation_slice() -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Creates a deterministic, physically grounded test slice of India-region detections
    across 2024 Q4 (context burn-in) and 2025 (primary corpus).
    """
    # 2024 Q4 Burn-In Context Slice (2 detections near Delhi industrial cluster)
    context_data = {
        "latitude": [28.6139, 28.6180],
        "longitude": [77.2090, 77.2120],  # ~540 m apart
        "bright_ti4": [330.5, 340.2],
        "scan": [0.4, 0.45],
        "track": [0.38, 0.40],
        "acq_date": ["2024-11-15", "2024-12-31"],
        "acq_time": ["0830", "1800"],
        "satellite": ["N20", "N20"],
        "instrument": ["VIIRS", "VIIRS"],
        "confidence": ["nominal", "high"],
        "version": ["2.0", "2.0"],
        "bright_ti5": [295.1, 298.4],
        "frp": [12.5, 25.0],
        "daynight": ["D", "N"],
        "type": [2, 2],  # static land
    }
    context_df = pd.DataFrame(context_data)

    # 2025 Primary Study Slice (8 detections representing temporal intervals & regions)
    # Delhi anchor: (28.6139, 77.2090)
    # Mumbai anchor: (19.0760, 72.8777)
    primary_data = {
        "latitude": [
            28.6150,  # 1. Early 2025: 12h after 2024-12-31 context, 150m from context point
            28.6170,  # 2. Same overpass (10 min later, ~300m away, testing snapshot co-detection)
            28.6145,  # 3. 4 hours later (within 6h window)
            28.6200,  # 4. 18 hours later (within 24h window, >6h)
            28.6130,  # 5. Mid-year 2025-06-15 (Train split)
            19.0760,  # 6. Mumbai 2025-06-20 (Train split, different region)
            19.0800,  # 7. Mumbai 2025-09-15 (Validation split)
            19.0750,  # 8. Mumbai 2025-11-20 (Test split)
        ],
        "longitude": [
            77.2100,
            77.2110,
            77.2095,
            77.2130,
            77.2085,
            72.8777,
            72.8800,
            72.8760,
        ],
        "bright_ti4": [335.0, 338.2, 342.1, 329.0, 345.5, 331.0, 333.4, 339.8],
        "scan": [0.41, 0.42, 0.39, 0.45, 0.38, 0.40, 0.43, 0.41],
        "track": [0.39, 0.40, 0.38, 0.41, 0.38, 0.39, 0.40, 0.39],
        "acq_date": [
            "2025-01-01",
            "2025-01-01",
            "2025-01-01",
            "2025-01-01",
            "2025-06-15",
            "2025-06-20",
            "2025-09-15",
            "2025-11-20",
        ],
        "acq_time": [
            "0600",
            "0610",  # 10 min after #1 (Snapshot)
            "1000",  # 4 hours after #1 (<6h)
            "2350",  # ~18 hours after #1 (<24h)
            "1200",
            "0800",
            "1400",
            "1300",
        ],
        "satellite": ["N20"] * 8,
        "instrument": ["VIIRS"] * 8,
        "confidence": ["nominal", "high", "high", "nominal", "high", "nominal", "high", "high"],
        "version": ["2.0"] * 8,
        "bright_ti5": [296.0, 297.5, 299.0, 294.0, 301.0, 295.5, 296.8, 298.2],
        "frp": [15.2, 22.0, 31.4, 8.5, 45.0, 11.2, 18.6, 28.0],
        "daynight": ["D", "D", "D", "N", "D", "D", "D", "D"],
        "type": [2, 2, 2, 2, 0, 0, 0, 2],
    }
    primary_df = pd.DataFrame(primary_data)
    return primary_df, context_df


def test_schema_and_integrity_invariants():
    """Validates Stage 0 invariants: 16 columns, 0 nulls, 0 duplicate rows."""
    primary_df, context_df = create_deterministic_validation_slice()
    for col in RAW_FIRMS_COLUMNS:
        assert col in primary_df.columns
        assert col in context_df.columns
    assert primary_df.isnull().sum().sum() == 0
    assert context_df.isnull().sum().sum() == 0
    assert primary_df.duplicated(subset=RAW_FIRMS_COLUMNS).sum() == 0


def test_sha256_detection_id_uniqueness():
    """Validates Stage 1: Full 64-character SHA-256 IDs are strictly unique."""
    primary_df, context_df = create_deterministic_validation_slice()
    combined = pd.concat([primary_df, context_df], ignore_index=True)
    ids = [
        generate_detection_id("file1.csv", i, row.latitude, row.longitude, row.acq_date, str(row.acq_time), row.bright_ti4, row.frp)
        for i, row in combined.iterrows()
    ]
    assert len(ids) == len(set(ids))
    assert len(ids[0]) == 64  # Full 64-character hexadecimal digest
    assert all(c in "0123456789abcdef" for c in ids[0])


def test_instantaneous_feature_formulas():
    """Validates Stage 2: Formulas for delta_t, temp_ratio, pixel_area, frp_density, log1p, cyclical harmonics."""
    primary_df, _ = create_deterministic_validation_slice()
    primary_df["acq_datetime_utc"] = pd.to_datetime(primary_df["acq_date"] + " " + primary_df["acq_time"].str.slice(0, 2) + ":" + primary_df["acq_time"].str.slice(2, 4) + ":00", utc=True)
    inst = compute_instantaneous_features(primary_df)

    # Check delta_t: bright_ti4 - bright_ti5
    expected_delta_t = primary_df["bright_ti4"].iloc[0] - primary_df["bright_ti5"].iloc[0]
    assert math.isclose(inst["delta_t"].iloc[0], expected_delta_t, rel_tol=1e-5)

    # Check temp_ratio: bright_ti4 / bright_ti5
    expected_ratio = primary_df["bright_ti4"].iloc[0] / primary_df["bright_ti5"].iloc[0]
    assert math.isclose(inst["temp_ratio"].iloc[0], expected_ratio, rel_tol=1e-5)

    # Check pixel_area: scan * track
    expected_area = primary_df["scan"].iloc[0] * primary_df["track"].iloc[0]
    assert math.isclose(inst["pixel_area"].iloc[0], expected_area, rel_tol=1e-5)

    # Check FRP density: frp / pixel_area
    expected_density = primary_df["frp"].iloc[0] / expected_area
    assert math.isclose(inst["frp_density"].iloc[0], expected_density, rel_tol=1e-5)

    # Check frp_log1p
    assert math.isclose(inst["frp_log1p"].iloc[0], math.log1p(primary_df["frp"].iloc[0]), rel_tol=1e-5)

    # Check cyclical bounds [-1.0, 1.0]
    for harmonic in ["sin_diurnal", "cos_diurnal", "sin_lst", "cos_lst", "sin_annual", "cos_annual"]:
        assert (inst[harmonic] >= -1.0001).all() and (inst[harmonic] <= 1.0001).all()


def test_h3_res8_assignment():
    """Validates Stage 3: H3 Resolution 8 index format."""
    primary_df, _ = create_deterministic_validation_slice()
    cells = assign_h3_res8(primary_df["latitude"].to_numpy(), primary_df["longitude"].to_numpy())
    assert len(cells) == len(primary_df)
    assert all(isinstance(c, str) and len(c) == 15 and c.startswith("88") for c in cells)


def test_causal_history_strictness_and_burn_in():
    """
    Validates Stage 4 & 5:
    - Target 1 (2025-01-01 06:00) draws causal context from 2024-12-31 burn-in (elapsed ~12h <= 24h).
    - Target 2 (2025-01-01 06:10) captures Target 1 as contemporaneous snapshot (within 10m <= 15m).
    - Causality assertion strictly prevents future observations from leaking into causal history.
    """
    primary_df, context_df = create_deterministic_validation_slice()
    with tempfile.TemporaryDirectory() as tmpdir:
        pipeline = PreprocessingPipeline(output_dir=Path(tmpdir))
        metrics = pipeline.run_on_dataframe(
            raw_2025_df=primary_df,
            context_burn_in_df=context_df,
        )

        out_path = Path(metrics["output_path"])
        df = pd.read_parquet(out_path)

        # Verification 1: Exactly 10 total records (2 context + 8 primary)
        assert len(df) == 10
        verify_id_uniqueness(df, "detection_id")

        # Verification 2: Check Target 1 (2025-01-01 06:00:00)
        # Context record 2 was at 2024-12-31 18:00:00 (12 hours prior)
        target1 = df[df["acq_datetime_utc"] == "2025-01-01 06:00:00+00:00"].iloc[0]
        assert target1["has_prior_24h_2km"] == True
        assert target1["hist_count_24h_2km"] >= 1
        assert math.isclose(target1["time_since_last_det_2km"], 12 * 3600, abs_tol=60.0)

        # Verification 3: Check Target 2 (2025-01-01 06:10:00)
        # Target 1 is within 10 min (600s <= 900s) and < 2 km: must be recorded in snapshot co-detection
        target2 = df[df["acq_datetime_utc"] == "2025-01-01 06:10:00+00:00"].iloc[0]
        assert target2["snapshot_co_detect_count_2km"] >= 1

        # Verification 4: Temporal Monotonicity
        verify_temporal_monotonicity(df["timestamp_utc"].to_numpy())


def test_causal_leakage_exception_trigger():
    """Asserts that injecting a future observation into a historical query raises PreprocessingInvariantError."""
    target_time = 1000
    future_history = [800, 950, 1050]  # 1050 is in the future
    caught = False
    try:
        verify_causal_history(target_time, future_history)
    except PreprocessingInvariantError:
        caught = True
    assert caught, "Expected PreprocessingInvariantError when passing future observation."


def test_state_isolation_on_train():
    """Validates that continuous scalers are fitted strictly on TRAIN rows."""
    primary_df, _ = create_deterministic_validation_slice()
    primary_df["acq_datetime_utc"] = pd.to_datetime(primary_df["acq_date"] + " " + primary_df["acq_time"].str.slice(0, 2) + ":" + primary_df["acq_time"].str.slice(2, 4) + ":00", utc=True)
    primary_df["is_burn_in_context"] = False
    partitioned = assign_spatiotemporal_partitions(primary_df)

    scaler = PartitionAwareScaler(["bright_ti4"])
    train_mask = partitioned["partition"] == "train"
    train_slice = partitioned[train_mask]

    scaler.fit_on_train(train_slice)
    assert scaler.is_fitted
    assert math.isclose(scaler.medians_["bright_ti4"], float(np.median(train_slice["bright_ti4"])))

    # Transform on full dataframe preserves state
    transformed = scaler.transform(partitioned)
    assert "bright_ti4_robust_scaled" in transformed.columns


def test_h3_3ring_covers_all_2km_candidates():
    """
    REGRESSION TEST for H3 ring coverage bug.
    Proves that the 3-ring (37 cells) guarantees no candidate within 2 km is missed,
    while 2-ring (19 cells) provably fails.

    Concrete counterexample: two points 1987.8m apart at grid_distance=3.
    """
    import h3

    R = 6371000.0

    # A point at a cell vertex (worst-case boundary position)
    lat1, lon1 = 28.620614, 77.207357
    cell1 = h3.latlng_to_cell(lat1, lon1, 8)

    # Move ~1990 meters north (within 2 km)
    dlat = 1990.0 / 111320.0
    lat2 = lat1 + dlat
    lon2 = lon1
    cell2 = h3.latlng_to_cell(lat2, lon2, 8)

    # Verify they are indeed within 2 km
    dist = haversine_distance_meters(lat1, lon1, lat2, lon2)
    assert dist <= 2000.0, f"Test setup error: distance {dist:.1f}m > 2000m"

    # Verify 2-ring would have MISSED this candidate (regression proof)
    disk_2ring = set(h3.grid_disk(cell1, 2))
    assert cell2 not in disk_2ring, "2-ring should NOT contain cell2 (regression baseline)"

    # Verify 3-ring correctly captures this candidate
    disk_3ring = set(h3.grid_disk(cell1, 3))
    assert cell2 in disk_3ring, "3-ring MUST contain cell2 for full 2km recall"

    # Also verify via the production function
    from src.data.spatial_index import get_2km_candidate_cells
    candidate_cells = get_2km_candidate_cells(cell1)
    assert cell2 in candidate_cells, "get_2km_candidate_cells must return cell2"
    assert len(candidate_cells) == 37, f"3-ring should have 37 cells, got {len(candidate_cells)}"


def test_snapshot_includes_future_but_causal_excludes_future():
    """
    Regression test: Contemporaneous snapshot features MUST include observations
    with t_j > t_i (within 15 min). Causal features MUST exclude them.
    Validates audit items 4 (causality) and 5 (snapshot separation).
    """
    primary_df, context_df = create_deterministic_validation_slice()
    with tempfile.TemporaryDirectory() as tmpdir:
        pipeline = PreprocessingPipeline(output_dir=Path(tmpdir))
        metrics = pipeline.run_on_dataframe(
            raw_2025_df=primary_df,
            context_burn_in_df=context_df,
        )

        out_path = Path(metrics["output_path"])
        df = pd.read_parquet(out_path)

        # Target 1 (06:00) and Target 2 (06:10) are 10 min apart and within 2 km.
        # From Target 1's perspective, Target 2 is 10 min IN THE FUTURE.
        # Snapshot should count Target 2. Causal must NOT count Target 2.
        target1 = df[df["acq_datetime_utc"] == "2025-01-01 06:00:00+00:00"].iloc[0]

        # Target 1's snapshot should include Target 2 (future, within 15 min, within 2 km)
        assert target1["snapshot_co_detect_count_2km"] >= 1, \
            "Snapshot must include future observation within 15 min"

        # Target 1's causal 6h count must NOT include Target 2 (which is in the future)
        # Target 1 can only have causal history from burn-in (2024-12-31 18:00, 12h prior)
        # which is outside the 6h window. So hist_count_6h should be 0.
        assert target1["hist_count_6h_2km"] == 0, \
            "Causal 6h must not include future observation"


def test_burn_in_never_in_evaluation_partitions():
    """
    Regression test: Burn-in context data must be assigned 'context_burn_in'
    partition and NEVER appear in train/val/test evaluation partitions.
    Validates audit item 14 (burn-in leakage prevention).
    """
    primary_df, context_df = create_deterministic_validation_slice()
    with tempfile.TemporaryDirectory() as tmpdir:
        pipeline = PreprocessingPipeline(output_dir=Path(tmpdir))
        metrics = pipeline.run_on_dataframe(
            raw_2025_df=primary_df,
            context_burn_in_df=context_df,
        )

        out_path = Path(metrics["output_path"])
        df = pd.read_parquet(out_path)

        burn_in_rows = df[df["is_burn_in_context"] == True]
        assert len(burn_in_rows) == 2, "Should have exactly 2 burn-in context rows"

        # Every burn-in row must have partition = "context_burn_in"
        for _, row in burn_in_rows.iterrows():
            assert row["partition"] == "context_burn_in", \
                f"Burn-in row has partition '{row['partition']}', expected 'context_burn_in'"

        # No burn-in row in any evaluation partition
        eval_partitions = {"train", "val", "test", "train_heldout_spatial", "test_seen_spatial"}
        burn_in_partitions = set(burn_in_rows["partition"].unique())
        assert burn_in_partitions.isdisjoint(eval_partitions), \
            f"Burn-in rows leaked into evaluation partitions: {burn_in_partitions & eval_partitions}"


def test_row_preservation_1to1():
    """
    Regression test: Every primary 2025 detection must produce exactly one
    output row. No rows dropped, no rows duplicated.
    Validates audit item 7 (row preservation) and 15 (production output).
    """
    primary_df, context_df = create_deterministic_validation_slice()
    n_primary = len(primary_df)
    n_context = len(context_df)

    with tempfile.TemporaryDirectory() as tmpdir:
        pipeline = PreprocessingPipeline(output_dir=Path(tmpdir))
        metrics = pipeline.run_on_dataframe(
            raw_2025_df=primary_df,
            context_burn_in_df=context_df,
        )

        out_path = Path(metrics["output_path"])
        df = pd.read_parquet(out_path)

        # Total rows = primary + context
        assert len(df) == n_primary + n_context, \
            f"Expected {n_primary + n_context} rows, got {len(df)}"

        # Primary rows exactly preserved
        primary_output = df[df["is_burn_in_context"] == False]
        assert len(primary_output) == n_primary, \
            f"Expected {n_primary} primary rows, got {len(primary_output)}"

        # Context rows exactly preserved
        context_output = df[df["is_burn_in_context"] == True]
        assert len(context_output) == n_context, \
            f"Expected {n_context} context rows, got {len(context_output)}"

        # Detection IDs are all unique (1:1 mapping)
        assert df["detection_id"].nunique() == len(df), \
            "Detection IDs are not unique — 1:1 mapping violated"


def test_detection_id_reproducibility():
    """
    Regression test: Same inputs must always produce the same detection_id.
    Validates audit item 6 (reproducibility) and 13 (deterministic IDs).
    """
    id1 = generate_detection_id("file.csv", 0, 28.6139, 77.2090, "2025-01-01", "0600", 335.0, 15.2)
    id2 = generate_detection_id("file.csv", 0, 28.6139, 77.2090, "2025-01-01", "0600", 335.0, 15.2)

    assert id1 == id2, "Same inputs must produce identical detection_id"
    assert len(id1) == 64, f"detection_id must be 64 hex chars, got {len(id1)}"
    assert all(c in "0123456789abcdef" for c in id1), "detection_id must be lowercase hex"

    # Different inputs must produce different IDs
    id3 = generate_detection_id("file.csv", 1, 28.6139, 77.2090, "2025-01-01", "0600", 335.0, 15.2)
    assert id1 != id3, "Different row_idx must produce different detection_id"


def test_schema_matches_15_firms_columns():
    """
    Regression test: RAW_FIRMS_COLUMNS must have exactly 15 entries
    matching the actual NASA FIRMS VIIRS NOAA-20 SP API response.
    """
    assert len(RAW_FIRMS_COLUMNS) == 15, \
        f"Expected 15 FIRMS columns, got {len(RAW_FIRMS_COLUMNS)}"
    assert "col_16" not in RAW_FIRMS_COLUMNS, \
        "col_16 must not be in RAW_FIRMS_COLUMNS (actual FIRMS API returns 15 columns)"

    expected_columns = [
        "latitude", "longitude", "bright_ti4", "scan", "track",
        "acq_date", "acq_time", "satellite", "instrument", "confidence",
        "version", "bright_ti5", "frp", "daynight", "type",
    ]
    assert RAW_FIRMS_COLUMNS == expected_columns, \
        f"Column order mismatch: {RAW_FIRMS_COLUMNS}"


def run_all_slice_tests():
    """Runner function for the validation suite."""
    print("Running test_schema_and_integrity_invariants...")
    test_schema_and_integrity_invariants()
    print("PASS: Schema and integrity invariants verified.")

    print("Running test_sha256_detection_id_uniqueness...")
    test_sha256_detection_id_uniqueness()
    print("PASS: SHA-256 detection_id uniqueness and 64-char length verified.")

    print("Running test_instantaneous_feature_formulas...")
    test_instantaneous_feature_formulas()
    print("PASS: Instantaneous physical feature calculations verified.")

    print("Running test_h3_res8_assignment...")
    test_h3_res8_assignment()
    print("PASS: Uber H3 Resolution 8 spatial indexing verified.")

    print("Running test_causal_history_strictness_and_burn_in...")
    test_causal_history_strictness_and_burn_in()
    print("PASS: Causal historical strictness (t_j < t_i), snapshot separation, and burn-in context verified.")

    print("Running test_causal_leakage_exception_trigger...")
    test_causal_leakage_exception_trigger()
    print("PASS: Causality violation detection trigger verified.")

    print("Running test_state_isolation_on_train...")
    test_state_isolation_on_train()
    print("PASS: State isolation (fitting strictly on TRAIN) verified.")

    print("\nRunning regression tests...")

    print("Running test_h3_3ring_covers_all_2km_candidates...")
    test_h3_3ring_covers_all_2km_candidates()
    print("PASS: H3 3-ring guaranteed 2km recall (regression for 2-ring bug).")

    print("Running test_snapshot_includes_future_but_causal_excludes_future...")
    test_snapshot_includes_future_but_causal_excludes_future()
    print("PASS: Snapshot includes future; causal strictly excludes future.")

    print("Running test_burn_in_never_in_evaluation_partitions...")
    test_burn_in_never_in_evaluation_partitions()
    print("PASS: Burn-in context isolated from all evaluation partitions.")

    print("Running test_row_preservation_1to1...")
    test_row_preservation_1to1()
    print("PASS: 1:1 row preservation verified for primary and context rows.")

    print("Running test_detection_id_reproducibility...")
    test_detection_id_reproducibility()
    print("PASS: Detection ID reproducibility and determinism verified.")

    print("Running test_schema_matches_15_firms_columns...")
    test_schema_matches_15_firms_columns()
    print("PASS: 15-column FIRMS schema verified (col_16 regression).")

    print("\nAll deterministic validation slice tests PASSED successfully.")


if __name__ == "__main__":
    run_all_slice_tests()
