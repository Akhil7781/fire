"""
Stage 8.29 Automated Test Suite:
Verifies Independent-Registry Provenance, Target-Proxy Audit, Ablation Results,
Temporal Loss Normalization, and Spatial Memorization Diagnostics.
"""

import hashlib
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

PROJECT_ROOT = Path("d:/DATA PREPROCESSING")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

@pytest.fixture(scope="session")
def summary_json():
    p = PROJECT_ROOT / "artifacts" / "stage8_29" / "stage8_29_summary.json"
    assert p.exists(), f"Missing {p}"
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)

@pytest.fixture(scope="session")
def proxy_audit_df():
    p = PROJECT_ROOT / "artifacts" / "stage8_29" / "registry_target_proxy_audit.csv"
    assert p.exists(), f"Missing {p}"
    return pd.read_csv(p)

@pytest.fixture(scope="session")
def no_reg_horizon_df():
    p = PROJECT_ROOT / "artifacts" / "stage8_29" / "no_registry_horizon_results.csv"
    assert p.exists(), f"Missing {p}"
    return pd.read_csv(p)

@pytest.fixture(scope="session")
def flips_df():
    p = PROJECT_ROOT / "artifacts" / "stage8_29" / "prediction_flip_analysis.csv"
    assert p.exists(), f"Missing {p}"
    return pd.read_csv(p)

# 1. Frozen Test Manifest Integrity
def test_stage8_25_test_manifest_frozen():
    p = PROJECT_ROOT / "data" / "reference" / "ds08" / "manifests" / "stage8_25" / "independent_test_manifest.json"
    assert p.exists()
    h = hashlib.sha256(p.read_bytes()).hexdigest()
    assert h == "5686345a1300282407d303c943e190867b63c0c5d5ea536973d4859cd8a95d6c"
    with open(p, "r", encoding="utf-8") as f:
        d = json.load(f)
    assert len(d["events"]) == 28

# 2. Stage 8.28 Artifacts Preserved
def test_stage8_28_artifacts_preserved():
    p_enc = PROJECT_ROOT / "models" / "stage8_28" / "causal_temporal_encoder.pt"
    p_clf = PROJECT_ROOT / "models" / "stage8_28" / "causal_classifier.pt"
    p_sum = PROJECT_ROOT / "artifacts" / "stage8_28" / "stage8_28_summary.json"
    assert p_enc.exists()
    assert p_clf.exists()
    assert p_sum.exists()

# 3. Persistent Registry Provenance Document Exists
def test_persistent_registry_provenance_doc():
    p = PROJECT_ROOT / "artifacts" / "stage8_29" / "persistent_registry_provenance.md"
    assert p.exists()
    content = p.read_text(encoding="utf-8")
    assert "TEST_DERIVED" in content
    assert "TRAIN_DERIVED" in content

# 4. Target Proxy Audit Confirms Direct Association
def test_registry_target_proxy_audit(proxy_audit_df):
    assert len(proxy_audit_df) == 28
    pers_rows = proxy_audit_df[proxy_audit_df["class_id"] == 3]
    acute_rows = proxy_audit_df[proxy_audit_df["class_id"] != 3]

    assert len(pers_rows) == 10
    assert len(acute_rows) == 18

    # Every persistent test event is within 100 meters of a registry source
    assert pers_rows["dist_to_persistent_registry_km"].max() < 0.1
    assert pers_rows["within_1km"].all()
    assert pers_rows["spatially_associated_with_same_event"].all()

    # Every acute fire is far away (> 70 km)
    assert acute_rows["dist_to_persistent_registry_km"].min() > 70.0
    assert not acute_rows["within_1km"].any()

# 5. Ablations Evaluated & Performance Drop Verified
def test_ablation_results(summary_json):
    abls = summary_json["ablations_h0"]
    assert len(abls) == 8

    full_res = next(a for a in abls if a["Model"] == "Stage 8.28 FULL")
    no_reg_res = next(a for a in abls if a["Model"] == "NO_PERSISTENT_REGISTRY")
    no_stat_res = next(a for a in abls if a["Model"] == "NO_STATIC_REGISTRIES")

    assert full_res["H0_Accuracy"] >= 0.95
    # NO_PERSISTENT_REGISTRY drops below 85%
    assert no_reg_res["H0_Accuracy"] < 0.85
    assert no_stat_res["H0_Accuracy"] < 0.85

# 6. No-Registry Multi-Horizon Results
def test_no_registry_horizon_results(no_reg_horizon_df):
    assert len(no_reg_horizon_df) == 8
    horizons = no_reg_horizon_df["horizon"].tolist()
    for h in ["H0", "H1", "H2", "H3", "H6", "H12", "H24", "Retro"]:
        assert h in horizons

# 7. Temporal Loss Audit Exists & Verified
def test_temporal_loss_audit():
    p = PROJECT_ROOT / "artifacts" / "stage8_29" / "temporal_loss_audit.csv"
    assert p.exists()
    df = pd.read_csv(p)
    dt_row = df[df["target_name"] == "raw_DeltaT_hours"].iloc[0]
    assert dt_row["unnormalized_mse_scale"] > 1e7
    assert dt_row["normalized_mse_scale"] < 10.0

# 8. Prediction Flip Analysis
def test_prediction_flip_analysis(flips_df):
    assert len(flips_df) == 28
    assert "prediction_flipped" in flips_df.columns
    flips_count = flips_df["prediction_flipped"].sum()
    assert flips_count > 0

# 9. Spatial Memorization Separation
def test_spatial_memorization_separation(summary_json):
    sm = summary_json["spatial_memorization"]
    assert sm["nearest_train_distance_km_min"] > 50.0

# 10. Random Registry Control Collapses
def test_random_registry_control(summary_json):
    rp = summary_json["registry_permutation_test"]
    assert rp["random_registry_accuracy"] < 0.80

# 11. All Required Stage 8.29 Artifacts Exist
def test_all_stage8_29_artifacts_exist():
    required_files = [
        "persistent_registry_provenance.md",
        "registry_target_proxy_audit.csv",
        "no_registry_horizon_results.csv",
        "prediction_flip_analysis.csv",
        "temporal_loss_audit.csv",
        "stage8_29_summary.json",
        "artifact_hashes.json",
        "stage8_29_final_report.md"
    ]
    for rf in required_files:
        fp = PROJECT_ROOT / "artifacts" / "stage8_29" / rf
        assert fp.exists(), f"Missing artifact: {fp}"
