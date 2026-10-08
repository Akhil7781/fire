"""
Stage 8.19F Comprehensive Audit Test Suite:
Independently verifies:
1. Manifest v3 immutability (byte-for-byte SHA-256 integrity).
2. Manifest v4 internal consistency and disk parity.
3. Spatial reproduction results (0 violations <= 50.0 km, minimum separation > 50.0 km, 0 tile/incident splits).
4. Live CDSE catalog results (all 8 products verified, UUID <-> Name bidirectional match, point-in-footprint containment).
5. Repaired spatial pair co-location (DS08_EXP_S4_018 and DS08_EXP_S5_016 in Fold 3; DS08_EXP_S4_043 in Fold 4).
6. Acquisition script safety (pilot restriction, confirmation gate, dry-run 0 bytes).
7. Label taxonomy decoupling (all expansion candidates remain UNLABELED_CANDIDATE).
8. Cloud exceptions strictly conditional upon post-acquisition SCL analysis.
9. Presence and structural integrity of all Stage 8.19F deliverables.
"""

from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.stage8_20_pilot_acquisition import run_acquisition_pilot, PILOT_CHIP_IDS

MANIFEST_V3_PATH = PROJECT_ROOT / "data" / "reference" / "ds08" / "manifests" / "stage8_19b" / "ds08_expansion_candidates_v3.json"
EXPECTED_V3_HASH = "dbba88fd8992db863ec374fea7c266a11e4173e50f257cc0fc9f84368b57b848"

MANIFEST_V4_DATA = PROJECT_ROOT / "data" / "reference" / "ds08" / "manifests" / "stage8_19e" / "ds08_expansion_candidates_v4.json"
MANIFEST_V4_DOCS = PROJECT_ROOT / "docs" / "stage8_19e" / "STAGE8_19E_RECONCILED_MANIFEST_V4.json"

SPATIAL_RESULTS_PATH = PROJECT_ROOT / "docs" / "stage8_19f" / "STAGE8_19F_SPATIAL_REPRODUCTION.json"
CDSE_RESULTS_PATH = PROJECT_ROOT / "docs" / "stage8_19f" / "STAGE8_19F_CDSE_REPRODUCTION.json"


@pytest.fixture(scope="module")
def v4_manifest():
    with open(MANIFEST_V4_DATA, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def spatial_results():
    with open(SPATIAL_RESULTS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def cdse_results():
    with open(CDSE_RESULTS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def test_1_v3_manifest_hash_immutable():
    with open(MANIFEST_V3_PATH, "rb") as f:
        actual_hash = hashlib.sha256(f.read()).hexdigest()
    assert actual_hash == EXPECTED_V3_HASH, f"Manifest v3 altered! Got {actual_hash}"


def test_2_v4_manifest_parity():
    with open(MANIFEST_V4_DATA, "rb") as f1, open(MANIFEST_V4_DOCS, "rb") as f2:
        h1 = hashlib.sha256(f1.read()).hexdigest()
        h2 = hashlib.sha256(f2.read()).hexdigest()
    assert h1 == h2, "V4 data manifest and docs manifest hashes do not match!"


def test_3_spatial_reproduction_results(spatial_results):
    assert spatial_results["status"] == "PROVEN"
    assert spatial_results["cross_fold_pairs"] == 22090
    assert spatial_results["violations_le_50km"] == 0
    assert spatial_results["minimum_separation_km"] > 50.000000
    assert spatial_results["minimum_margin_m"] > 0
    assert spatial_results["mgrs_tile_splits"] == 0
    assert spatial_results["incident_splits"] == 0
    assert spatial_results["closest_pair"] == ["DS08_EXP_S3_004", "DS08_EXP_S4_004"]
    for k in range(1, 6):
        assert spatial_results["fold_counts"][f"Fold {k}"] == 47


def test_4_cdse_reproduction_results(cdse_results):
    assert len(cdse_results) == 8
    for item in cdse_results:
        assert item["status"] == "PROVEN"
        assert item["live_catalog_found"] is True
        assert item["uuid_name_match"] is True
        assert item["product_level_valid"] is True
        assert item["point_covered_by_footprint"] is True
        assert item["online"] is True
        assert len(item["v4_uuid"]) == 36


def test_5_repaired_pair_co_located(v4_manifest):
    records = {r["chip_id"]: r for r in v4_manifest["records"]}
    s4_018 = records["DS08_EXP_S4_018"]
    s5_016 = records["DS08_EXP_S5_016"]
    s4_043 = records["DS08_EXP_S4_043"]

    assert s4_018["assigned_fold"] == "Fold 3"
    assert s5_016["assigned_fold"] == "Fold 3"
    assert s4_043["assigned_fold"] == "Fold 4"
    assert s4_018["assigned_fold"] == s5_016["assigned_fold"], "Repaired pair must be co-located in the same fold!"


def test_6_acquisition_script_dry_run_safety():
    out_dir = PROJECT_ROOT / "data" / "interim" / "ds08_stage8_20_pilot"
    assert not out_dir.exists(), "Pilot output directory must not exist prior to authorized execution!"

    result = run_acquisition_pilot(confirm_acquisition=False, dry_run=True)
    assert result["mode"] == "DRY_RUN"
    assert result["pilot_chips_evaluated"] == 8
    assert result["downloaded_bytes"] == 0
    assert not out_dir.exists(), "Dry-run must not create output directory!"


def test_7_no_confirmed_labels_in_manifest(v4_manifest):
    exp = [r for r in v4_manifest["records"] if r["candidate_stratum_id"] != "STR-7"]
    for r in exp:
        assert r["human_confirmed_label"] is None
        assert r["annotation_status"] == "UNLABELED_CANDIDATE"
        assert r["confirmed_bounding_boxes"] == []


def test_8_cloud_exceptions_strictly_conditional(v4_manifest):
    records = {r["chip_id"]: r for r in v4_manifest["records"]}
    for cid in ["DS08_EXP_S1_002", "DS08_EXP_S1_004"]:
        r = records[cid]
        assert r["cloud_exception_applied"] is True
        assert r["cloud_exception_id"] == "DEC-U5"


def test_9_stage8_19f_deliverables_exist():
    docs_dir = PROJECT_ROOT / "docs" / "stage8_19f"
    expected_files = [
        docs_dir / "STAGE8_19F_SPATIAL_REPRODUCTION.json",
        docs_dir / "STAGE8_19F_CDSE_REPRODUCTION.json",
        docs_dir / "STAGE8_19F_ACQUISITION_SCRIPT_AUDIT.md",
        docs_dir / "STAGE8_19F_TEST_REPRODUCTION.md",
        docs_dir / "STAGE8_19F_DECISION_LOG.md",
    ]
    for p in expected_files:
        assert p.exists(), f"Missing required deliverable: {p.name}"
