"""
Tests for Stage 8.25 Dataset and Multi-Year Ingestion Integrity.
Validates:
- No duplicate physical events
- No detection duplication
- Correct multi-year sensor normalization
- Correct event construction
- Zero NaN / Inf values
- Full provenance metadata
- Frozen predecessor model checkpoint hashes
"""

import hashlib
import json
from pathlib import Path
import pytest
import numpy as np
import pandas as pd

PROJECT_ROOT = Path("d:/DATA PREPROCESSING")

FROZEN_PREDECESSORS = {
    "models/tcn/best_tcn.pt": "dfa2decb772cf71b65601a4cb83a12b73ee1706ff47e2acb23a9f53c84506f16",
    "models/deep_sad/best_deep_sad.pt": "a7f99f521cf56e3d651101259543f967eee535df82736aae3ae4271922947eaa",
    "models/s2_encoder/best_s2_encoder.pt": "5ec8a02dfe1064d77060c7fb04f08b03cf5a31c4ebf3007bc80d11f0e0f36b87",
    "models/yolo/infrastructure/best_infrastructure.pt": "bad5d3942f469b74a7778762696bb390174619cb0f403dbcc93be1066ba5dcf6",
    "models/yolo/fire_smoke/best_fire_smoke.pt": "29ab42eda1cd05d7141525927ab1c502c249082b5b2bbf5f2e0c9e8847c3d227",
    "models/fusion/best_multimodal_fusion.pt": "7398b7f0539637091cac763eeca0c23be0e5f8cd99860872d3d9f75d84f1481c",
}

def test_frozen_predecessor_hashes_unchanged():
    for rel_path, expected_hash in FROZEN_PREDECESSORS.items():
        file_path = PROJECT_ROOT / rel_path
        assert file_path.exists(), f"Predecessor checkpoint missing: {rel_path}"
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            hasher.update(f.read())
        actual_hash = hasher.hexdigest()
        assert actual_hash == expected_hash, f"Hash mismatch for frozen predecessor {rel_path}!"

def test_source_registry_integrity():
    reg_path = PROJECT_ROOT / "data" / "reference" / "ds08" / "manifests" / "stage8_25" / "source_registry.json"
    assert reg_path.exists(), "Source registry missing"
    with open(reg_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert "sources" in data
    assert len(data["sources"]) >= 20
    for s in data["sources"]:
        assert "source_name" in s
        assert "organization" in s
        assert "target_domain" in s
        assert "tier" in s

def test_multiyear_firms_normalization():
    firms_path = PROJECT_ROOT / "data" / "interim" / "ds08_stage8_25_multiyear_firms.parquet"
    if not firms_path.exists():
        pytest.skip("ds08_stage8_25_multiyear_firms.parquet not yet materialized")
    df = pd.read_parquet(firms_path)
    required_cols = [
        "detection_id", "sensor", "satellite", "latitude", "longitude",
        "acq_datetime_utc", "bright_ti4", "bright_ti5", "frp", "confidence",
        "scan", "track", "daynight", "source_product", "processing_version"
    ]
    for col in required_cols:
        assert col in df.columns, f"Missing required FIRMS column {col}"
    # No duplicate detections
    assert df["detection_id"].is_unique, "Detection ID duplication detected in multi-year FIRMS!"
    # Numerical validity
    assert not df["latitude"].isna().any()
    assert not df["longitude"].isna().any()
    assert not df["frp"].isna().any()
    assert (df["frp"] >= 0.0).all()

def test_physical_events_no_duplicates():
    events_path = PROJECT_ROOT / "data" / "interim" / "ds08_stage8_25_physical_events.parquet"
    if not events_path.exists():
        pytest.skip("ds08_stage8_25_physical_events.parquet not yet materialized")
    df = pd.read_parquet(events_path)
    assert df["event_id"].is_unique, "Duplicate physical event IDs found!"
    assert len(df) >= 100, "Insufficient physical events constructed"
    for col in ["centroid_lat", "centroid_lon", "mean_frp", "max_frp", "duration_hours"]:
        assert not df[col].isna().any(), f"NaN values in physical events column {col}"
        assert not np.isinf(df[col]).any(), f"Inf values in physical events column {col}"
