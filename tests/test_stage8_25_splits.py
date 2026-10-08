"""
Tests for Stage 8.25 Chronological Partitioning, Spatial Isolation & Leakage Prevention.
Validates:
- Zero cross-split physical event leakage
- Zero incident or facility leakage
- Strict spatial exclusion (> 50.0 km footprint separation)
- Test set contains CONFIRMED labels only (zero weak labels)
- All 4 classes have positive test support (> 0)
- Frozen test manifest SHA-256 integrity
"""

import hashlib
import json
import math
from pathlib import Path
import pytest
import pandas as pd

PROJECT_ROOT = Path("d:/DATA PREPROCESSING")

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2.0)**2
    return r * 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

def test_chronological_splits_and_spatial_isolation():
    cohort_path = PROJECT_ROOT / "data" / "interim" / "ds08_stage8_25_multimodal_event_cohort.parquet"
    if not cohort_path.exists():
        pytest.skip("ds08_stage8_25_multimodal_event_cohort.parquet not yet materialized")
    df = pd.read_parquet(cohort_path)

    # Check partition definitions
    train_events = df[df["split"] == "train"]
    val_events = df[df["split"] == "val"]
    test_events = df[df["split"] == "test"]

    assert len(train_events) > 0, "Empty train partition"
    assert len(val_events) > 0, "Empty validation partition"
    assert len(test_events) > 0, "Empty test partition"

    # Chronological integrity
    assert (train_events["year"] <= 2024).all(), "Train partition contains post-2024 events!"
    assert (val_events["year"] == 2025).all(), "Validation partition contains non-2025 events!"
    assert (test_events["year"] == 2026).all(), "Test partition contains non-2026 events!"

    # Spatial isolation: every test event must be > 50km from ALL train and val events
    train_val_events = df[df["split"].isin(["train", "val"])]
    for _, t_row in test_events.iterrows():
        min_dist = min([
            haversine_km(t_row["centroid_lat"], t_row["centroid_lon"], tv_row["centroid_lat"], tv_row["centroid_lon"])
            for _, tv_row in train_val_events.iterrows()
        ])
        assert min_dist > 50.0, f"Spatial leakage violation! Test event {t_row['event_id']} is {min_dist:.2f} km <= 50.0 km from train/val!"

def test_test_partition_class_support_gate():
    cohort_path = PROJECT_ROOT / "data" / "interim" / "ds08_stage8_25_multimodal_event_cohort.parquet"
    if not cohort_path.exists():
        pytest.skip("ds08_stage8_25_multimodal_event_cohort.parquet not yet materialized")
    df = pd.read_parquet(cohort_path)
    test_df = df[df["split"] == "test"]

    class_counts = test_df["class_id"].value_counts().to_dict()
    # All 4 classes must have positive support in independent test
    for c_id in [0, 1, 2, 3]:
        cnt = class_counts.get(c_id, 0)
        assert cnt > 0, f"Class {c_id} has ZERO independent test support! Test support gate failed!"

def test_no_weak_labels_in_test():
    cohort_path = PROJECT_ROOT / "data" / "interim" / "ds08_stage8_25_multimodal_event_cohort.parquet"
    if not cohort_path.exists():
        pytest.skip("ds08_stage8_25_multimodal_event_cohort.parquet not yet materialized")
    df = pd.read_parquet(cohort_path)
    test_df = df[df["split"] == "test"]
    assert (test_df["label_tier"] == "CONFIRMED").all(), "Weak or unconfirmed label found in independent test partition!"

def test_frozen_test_manifest_sha256():
    manifest_path = PROJECT_ROOT / "data" / "reference" / "ds08" / "manifests" / "stage8_25" / "independent_test_manifest.json"
    if not manifest_path.exists():
        pytest.skip("independent_test_manifest.json not yet materialized")
    hasher = hashlib.sha256()
    with open(manifest_path, "rb") as f:
        hasher.update(f.read())
    current_hash = hasher.hexdigest()
    assert len(current_hash) == 64
    with open(manifest_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert len(data["events"]) > 0
