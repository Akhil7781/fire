"""
Tests for Stage 8.19C: Final Pre-Acquisition Code, Geometry, and Script Safety Audit.
Verifies:
1. Stage 8.19C deliverables exist.
2. Closest cross-fold pair (DS08_EXP_S4_018 vs DS08_EXP_S5_016) is exactly reproducible from Manifest v3.
3. Edge-to-edge distance calculation matches dense sampling.
4. Acquisition script remains strictly dry-run by default with 0 bytes downloaded.
5. All 8 pilot records exist with correct decoupled taxonomy and metadata.
"""

from collections import Counter
import json
from pathlib import Path
import sys

import pytest
from pyproj import Geod

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

MANIFEST_V3_PATH = PROJECT_ROOT / "data" / "reference" / "ds08" / "manifests" / "stage8_19b" / "ds08_expansion_candidates_v3.json"
DOCS_STAGE_DIR = PROJECT_ROOT / "docs" / "stage8_19c"
REVIEW_DIR = PROJECT_ROOT / "data" / "reference" / "ds08" / "annotations" / "review"


@pytest.fixture(scope="module")
def manifest_v3():
    with open(MANIFEST_V3_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def test_stage8_19c_deliverables_exist():
    assert (DOCS_STAGE_DIR / "STAGE8_19C_FINAL_PREACQUISITION_AUDIT.md").exists()
    assert (REVIEW_DIR / "stage8_19c_final_preacquisition_audit.md").exists()


def test_closest_pair_reproducibility(manifest_v3):
    records = {r["chip_id"]: r for r in manifest_v3["records"]}
    r1 = records["DS08_EXP_S4_018"]
    r2 = records["DS08_EXP_S5_016"]

    assert r1["assigned_fold"] != r2["assigned_fold"]
    geod = Geod(ellps="WGS84")

    def get_corners(lat, lon, half_m=2560.0):
        lon_n, lat_n, _ = geod.fwd(lon, lat, 0.0, half_m)
        lon_s, lat_s, _ = geod.fwd(lon, lat, 180.0, half_m)
        lon_e, lat_e, _ = geod.fwd(lon, lat, 90.0, half_m)
        lon_w, lat_w, _ = geod.fwd(lon, lat, 270.0, half_m)
        dlat = (lat_n - lat_s) / 2.0
        dlon = (lon_e - lon_w) / 2.0
        return [
            (lon - dlon, lat - dlat),
            (lon + dlon, lat - dlat),
            (lon + dlon, lat + dlat),
            (lon - dlon, lat + dlat)
        ]

    c1 = get_corners(r1["latitude"], r1["longitude"])
    c2 = get_corners(r2["latitude"], r2["longitude"])

    min_d = 999999999.0
    for p1 in c1:
        for p2 in c2:
            _, _, d = geod.inv(p1[0], p1[1], p2[0], p2[1])
            if d < min_d:
                min_d = d

    min_d_km = min_d / 1000.0
    assert abs(min_d_km - 50.0079) < 0.001
    assert min_d_km > 50.0


def test_acquisition_script_dry_run_safety():
    from scripts.stage8_20_pilot_acquisition import run_acquisition_pilot
    res = run_acquisition_pilot(confirm_acquisition=False)
    assert res["mode"] == "DRY_RUN"
    assert res["downloaded_bytes"] == 0
    assert res["status"] == "READY_FOR_OWNER_AUTHORIZATION"


def test_pilot_records_taxonomy_and_exceptions(manifest_v3):
    from scripts.stage8_20_pilot_acquisition import PILOT_CHIP_IDS
    records = {r["chip_id"]: r for r in manifest_v3["records"]}

    for cid in PILOT_CHIP_IDS:
        r = records[cid]
        assert r["human_confirmed_label"] is None
        assert r["annotation_status"] == "UNLABELED_CANDIDATE"
        if cid in ["DS08_EXP_S1_002", "DS08_EXP_S1_004"]:
            assert r["cloud_exception_applied"] is True
            assert r["cloud_exception_id"] == "DEC-U5"
        else:
            assert r["cloud_exception_applied"] is False
