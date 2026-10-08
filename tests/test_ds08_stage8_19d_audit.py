"""
Stage 8.19D Audit Test Suite:
Validates Stage 8.19D deliverables, native UTM footprint geometry calculations,
manifest immutability, and Stage 8.20 acquisition script safety invariants.
"""

import hashlib
import json
from pathlib import Path
import sys
import pytest
from pyproj import Geod, Transformer

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

MANIFEST_V3_PATH = PROJECT_ROOT / "data" / "reference" / "ds08" / "manifests" / "stage8_19b" / "ds08_expansion_candidates_v3.json"
EXPECTED_MANIFEST_HASH = "dbba88fd8992db863ec374fea7c266a11e4173e50f257cc0fc9f84368b57b848"
REPORT_PATH = PROJECT_ROOT / "docs" / "stage8_19d" / "STAGE8_19D_NATIVE_GEOMETRY_AND_STAC_AUDIT.md"
MIRROR_REPORT_PATH = PROJECT_ROOT / "data" / "reference" / "ds08" / "annotations" / "review" / "stage8_19d_native_geometry_and_stac_audit.md"


def test_deliverables_exist():
    assert REPORT_PATH.exists(), f"Report missing: {REPORT_PATH}"
    assert REPORT_PATH.stat().st_size > 2000
    assert MIRROR_REPORT_PATH.exists(), f"Mirror report missing: {MIRROR_REPORT_PATH}"
    assert MIRROR_REPORT_PATH.stat().st_size > 2000

    report_content = REPORT_PATH.read_text(encoding="utf-8")
    assert "BLOCKED — RESOLUTION REQUIRED" in report_content
    assert "Native UTM Footprint Separation" in report_content
    assert "49.9940 km" in report_content or "49.993988" in report_content
    assert "Live STAC Verification" in report_content


def test_manifest_hash_integrity():
    with open(MANIFEST_V3_PATH, "rb") as f:
        actual_hash = hashlib.sha256(f.read()).hexdigest()
    assert actual_hash == EXPECTED_MANIFEST_HASH


def test_native_raster_geometry_reproducibility():
    """Reproduces the native UTM raster geometry calculation on the closest cross-fold pair."""
    with open(MANIFEST_V3_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    r1 = next(r for r in data["records"] if r["chip_id"] == "DS08_EXP_S4_018")
    r2 = next(r for r in data["records"] if r["chip_id"] == "DS08_EXP_S5_016")

    geod = Geod(ellps="WGS84")

    # Center-to-center distance
    _, _, d_center_m = geod.inv(r1["longitude"], r1["latitude"], r2["longitude"], r2["latitude"])
    d_center_km = d_center_m / 1000.0
    assert pytest.approx(d_center_km, rel=1e-4) == 56.9915

    # Native UTM rotated footprint calculation
    def get_native_corners(r, half_m=2560.0):
        zone = int(r["mgrs_tile"][1:3])
        t_to_utm = Transformer.from_crs("EPSG:4326", f"EPSG:{32600 + zone}", always_xy=True)
        t_to_wgs = Transformer.from_crs(f"EPSG:{32600 + zone}", "EPSG:4326", always_xy=True)
        e, n = t_to_utm.transform(r["longitude"], r["latitude"])
        corners_utm = [
            (e - half_m, n - half_m),
            (e + half_m, n - half_m),
            (e + half_m, n + half_m),
            (e - half_m, n + half_m),
        ]
        return [t_to_wgs.transform(x, y) for x, y in corners_utm]

    c1_native = get_native_corners(r1)
    c2_native = get_native_corners(r2)

    min_native_d_m = min(geod.inv(x1, y1, x2, y2)[2] for x1, y1 in c1_native for x2, y2 in c2_native)
    min_native_d_km = min_native_d_m / 1000.0

    # Must be 49.9940 km (+/- 0.001 km)
    assert pytest.approx(min_native_d_km, rel=1e-4) == 49.9940
    # Must be less than 50.0000 km by ~6 meters
    assert min_native_d_km < 50.0000
    shortfall_m = 50000.0 - min_native_d_m
    assert pytest.approx(shortfall_m, abs=0.5) == 6.01


def test_pilot_cohort_and_acquisition_safety():
    """Validates the 8-chip pilot batch configuration and dry-run safety behavior."""
    from scripts.stage8_20_pilot_acquisition import PILOT_CHIP_IDS, run_acquisition_pilot

    assert len(PILOT_CHIP_IDS) == 8

    # Dry run execution must download 0 bytes and not modify disk
    result = run_acquisition_pilot(confirm_acquisition=False, dry_run=True)
    assert result["mode"] == "DRY_RUN"
    assert result["downloaded_bytes"] == 0
    assert result["pilot_chips_evaluated"] == 8
