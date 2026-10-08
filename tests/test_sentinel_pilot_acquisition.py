"""
Unit tests for Sentinel-2 L2A Dataset Acquisition Pilot (Stage 8.6).

Verifies:
- UTM zone calculation and AOI generation across Indian longitudes
- Geographic region classification
- Processing API request payload conformance
- GeoTIFF structural raster validation (5 bands, 512x512, 10m res, float32)
- Rejection of non-compliant rasters
- Metadata sidecar schema, zero credential leakage, and strict UNLABELED policy
- Integrity of acquired pilot chips and audit summary (if present)
- Invariant integrity of all 5 frozen predecessor artifacts
"""

from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import sys
from typing import Any, Dict, List, Tuple
import unittest.mock as mock

import numpy as np
from PIL import Image
import pytest
import rasterio
from rasterio.transform import from_origin

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.run_sentinel_pilot_acquisition import (
    AUDIT_SUMMARY_PATH,
    BAND_ORDER,
    CHIP_PIXELS,
    CHIP_SPAN_M,
    CHIPS_DIR,
    METADATA_DIR,
    PIXEL_RESOLUTION_M,
    PILOT_TARGET_COUNT,
    build_processing_payload,
    classify_indian_region,
    compute_aoi_for_point,
    get_utm_epsg,
    save_pilot_sidecar_json,
    validate_chip_raster,
)

FROZEN_HASHES = {
    "models/tcn/best_tcn.pt": "dfa2decb772cf71b65601a4cb83a12b73ee1706ff47e2acb23a9f53c84506f16",
    "models/deep_sad/best_deep_sad.pt": "a7f99f521cf56e3d651101259543f967eee535df82736aae3ae4271922947eaa",
    "models/yolo/infrastructure/best_infrastructure.pt": "bad5d3942f469b74a7778762696bb390174619cb0f403dbcc93be1066ba5dcf6",
    "models/yolo/fire_smoke/best_fire_smoke.pt": "29ab42eda1cd05d7141525927ab1c502c249082b5b2bbf5f2e0c9e8847c3d227",
    "data/embeddings/fusion/india_2025_tcn_sad_aligned.parquet": "49505cb4705516aef8d77af628debc485be894fae75dc19e3269b3ba6df7e931",
}


def test_utm_zone_and_epsg_computation():
    """Verifies UTM zone and EPSG computation across India's geographic span."""
    # West India (Gujarat/Rajasthan, ~70°E) -> Zone 42N
    zone_w, epsg_w, _ = get_utm_epsg(70.0)
    assert zone_w == 42
    assert epsg_w == 32642

    # Central India (~76°E) -> Zone 43N
    zone_c, epsg_c, _ = get_utm_epsg(76.0)
    assert zone_c == 43
    assert epsg_c == 32643

    # Central-East India (~80°E) -> Zone 44N
    zone_ce, epsg_ce, _ = get_utm_epsg(80.0)
    assert zone_ce == 44
    assert epsg_ce == 32644

    # East India (~86°E) -> Zone 45N
    zone_e, epsg_e, _ = get_utm_epsg(86.0)
    assert zone_e == 45
    assert epsg_e == 32645

    # Northeast India (~92°E) -> Zone 46N
    zone_ne, epsg_ne, _ = get_utm_epsg(92.0)
    assert zone_ne == 46
    assert epsg_ne == 32646


def test_classify_indian_region():
    """Verifies geographic region classification."""
    assert classify_indian_region(30.5, 75.0) == "NORTH"  # Punjab
    assert classify_indian_region(11.0, 78.0) == "SOUTH"  # Tamil Nadu
    assert classify_indian_region(20.0, 85.0) == "EAST"   # Odisha
    assert classify_indian_region(22.0, 71.0) == "WEST"   # Gujarat
    assert classify_indian_region(23.0, 78.0) == "CENTRAL" # Madhya Pradesh


def test_compute_aoi_for_point():
    """Verifies 5.12 km x 5.12 km AOI computation for diverse locations."""
    aoi = compute_aoi_for_point(lat=21.63424, lon=76.66431, span_m=5120.0)
    assert aoi["utm_epsg"] == 32643
    assert aoi["chip_span_meters"] == 5120.0

    min_x, min_y, max_x, max_y = aoi["utm_bbox"]
    assert pytest.approx(max_x - min_x, abs=0.1) == 5120.0
    assert pytest.approx(max_y - min_y, abs=0.1) == 5120.0

    center_x = aoi["center_utm"]["x"]
    center_y = aoi["center_utm"]["y"]
    assert min_x < center_x < max_x
    assert min_y < center_y < max_y


def test_build_processing_payload():
    """Verifies Processing API request payload structure and evalscript."""
    aoi = compute_aoi_for_point(lat=21.63424, lon=76.66431)
    payload = build_processing_payload(aoi, time_from="2025-03-11T05:30:00Z", time_to="2025-03-11T05:35:00Z")

    assert payload["input"]["bounds"]["bbox"] == aoi["utm_bbox"]
    assert "EPSG/0/32643" in payload["input"]["bounds"]["properties"]["crs"]

    data_elem = payload["input"]["data"][0]
    assert data_elem["type"] == "sentinel-2-l2a"
    assert data_elem["dataFilter"]["maxCloudCoverage"] == 10
    assert data_elem["processing"]["upsampling"] == "BILINEAR"
    assert data_elem["processing"]["downsampling"] == "BILINEAR"

    assert payload["output"]["width"] == 512
    assert payload["output"]["height"] == 512
    assert payload["output"]["responses"][0]["format"]["type"] == "image/tiff"

    script = payload["evalscript"]
    assert "//VERSION=3" in script
    for b in BAND_ORDER:
        assert f'"{b}"' in script
    assert 'units: "REFLECTANCE"' in script
    assert 'sampleType: "FLOAT32"' in script


def _create_mock_geotiff(
    path: Path,
    bands: int = 5,
    width: int = 512,
    height: int = 512,
    dtype: str = "float32",
    epsg: int = 32643,
    res: float = 10.0,
    top_left: Tuple[float, float] = (669686.28, 2395825.85),
    fill_empty: bool = False,
) -> None:
    transform = from_origin(top_left[0], top_left[1], res, res)
    if fill_empty:
        data = np.full((bands, height, width), np.nan, dtype=dtype)
    else:
        data = np.random.uniform(0.05, 0.4, size=(bands, height, width)).astype(dtype)

    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=height,
        width=width,
        count=bands,
        dtype=dtype,
        crs=f"EPSG:{epsg}",
        transform=transform,
    ) as dst:
        dst.write(data)


def test_validate_chip_raster_success(tmp_path: Path):
    """Verifies that a valid 5-band 512x512 GeoTIFF passes validation."""
    tif_path = tmp_path / "mock_chip.tif"
    _create_mock_geotiff(tif_path, bands=5, width=512, height=512, dtype="float32", epsg=32643)

    val = validate_chip_raster(
        tiff_path=tif_path,
        expected_lat=21.63424,
        expected_lon=76.66431,
        expected_epsg=32643,
    )

    assert val["is_valid"] is True
    assert val["band_count"] == 5
    assert val["width"] == 512
    assert val["height"] == 512
    assert val["center_point_inside_chip"] is True
    assert len(val["band_statistics"]) == 5


def test_validate_chip_raster_rejections(tmp_path: Path):
    """Verifies that non-compliant rasters raise appropriate ValueErrors."""
    # Band count != 5
    tif_bad_bands = tmp_path / "bad_bands.tif"
    _create_mock_geotiff(tif_bad_bands, bands=3)
    with pytest.raises(ValueError, match="Expected 5 bands"):
        validate_chip_raster(tif_bad_bands, 21.63424, 76.66431, 32643)

    # Dimensions != 512x512
    tif_bad_dim = tmp_path / "bad_dim.tif"
    _create_mock_geotiff(tif_bad_dim, width=256, height=256)
    with pytest.raises(ValueError, match="Expected 512x512"):
        validate_chip_raster(tif_bad_dim, 21.63424, 76.66431, 32643)

    # Empty band (all NaN)
    tif_empty = tmp_path / "empty.tif"
    _create_mock_geotiff(tif_empty, fill_empty=True)
    with pytest.raises(ValueError, match="is entirely empty"):
        validate_chip_raster(tif_empty, 21.63424, 76.66431, 32643)

    # Point outside raster bounds
    tif_far = tmp_path / "far.tif"
    _create_mock_geotiff(tif_far, top_left=(100000.0, 100000.0))
    with pytest.raises(ValueError, match="outside raster bounds"):
        validate_chip_raster(tif_far, 21.63424, 76.66431, 32643)


def test_save_pilot_sidecar_json_security_and_unlabeled(tmp_path: Path):
    """Verifies that sidecar JSON strictly contains UNLABELED policy and zero credentials."""
    json_path = tmp_path / "pilot_test.json"
    firms_info = {
        "detection_id": "test_det_123",
        "latitude": 21.5,
        "longitude": 76.5,
        "acquisition_datetime_utc": "2025-03-11T08:00:00Z",
        "frp": 15.0,
        "region": "CENTRAL",
    }
    sentinel2_info = {
        "product_id": "S2B_MSIL2A_TEST.SAFE",
        "platform": "sentinel-2b",
        "acquisition_datetime_utc": "2025-03-11T05:30:00Z",
        "temporal_gap_hours": 2.5,
        "cloud_cover_pct": 1.2,
        "collection": "sentinel-2-l2a",
        "tile_id": "T43QFD",
    }
    aoi = compute_aoi_for_point(21.5, 76.5)
    extraction_info = {
        "processing_api_endpoint": "https://sh.dataspace.copernicus.eu/process/v1",
        "aoi_geometry": aoi["utm_geometry"],
        "aoi_bbox_utm": aoi["utm_bbox"],
        "aoi_bbox_wgs84": aoi["wgs84_bbox"],
        "projected_crs": "EPSG:32643",
        "output_crs": "EPSG:32643",
        "output_width_pixels": 512,
        "output_height_pixels": 512,
        "output_resolution_meters": 10.0,
        "band_order": BAND_ORDER,
        "input_units": "REFLECTANCE",
        "resampling_method": "BILINEAR",
        "output_dtype": "FLOAT32",
        "extraction_timestamp_utc": "2026-09-29T13:00:00Z",
        "file_size_bytes": 3022470,
        "sha256_checksum": "test_hash_123456",
        "previews": {},
        "band_statistics": {},
    }

    save_pilot_sidecar_json(json_path, "PILOT_01_CENTRAL", firms_info, sentinel2_info, extraction_info)
    assert json_path.exists()

    content = json_path.read_text(encoding="utf-8")
    assert "client_secret" not in content.lower()
    assert "access_token" not in content.lower()
    assert "bearer" not in content.lower()
    assert "authorization" not in content.lower()

    data = json.loads(content)
    assert data["label_status"] == "UNLABELED"
    assert data["firms_metadata"]["association_status"] == "candidate_context_only"
    # Ensure no supervised class labels were attached
    forbidden_classes = ["Industrial Fire", "Forest Fire", "Agricultural Fire", "Other Thermal Source"]
    for fc in forbidden_classes:
        assert fc not in content


def test_live_pilot_chips_integrity_if_acquired():
    """If pilot audit summary exists, verifies that all chips are real, valid, and unlabelled."""
    if not AUDIT_SUMMARY_PATH.exists():
        pytest.skip("Pilot audit summary not yet generated.")

    with open(AUDIT_SUMMARY_PATH, "r", encoding="utf-8") as f:
        summary = json.load(f)

    acquired_count = summary["pilot_size_acquired"]
    assert acquired_count > 0, "No pilot chips acquired."
    assert acquired_count <= PILOT_TARGET_COUNT
    assert summary["label_status_policy"].startswith("STRICT_UNLABELED")
    assert summary["validation_failure_count"] == 0

    extracted_chips = summary["extracted_chips"]
    assert len(extracted_chips) == acquired_count

    seen_scenes = set()
    for chip in extracted_chips:
        tif_path = Path(chip["tif_path"])
        json_path = Path(chip["json_path"])
        assert tif_path.exists(), f"Missing chip GeoTIFF: {tif_path}"
        assert json_path.exists(), f"Missing chip JSON: {json_path}"

        # Re-verify checksum
        calc_hash = hashlib.sha256(tif_path.read_bytes()).hexdigest()
        assert chip["tif_sha256"] == calc_hash

        # Uniqueness check: no duplicate scenes
        prod = chip["product_id"]
        assert prod not in seen_scenes, f"Duplicate scene {prod} in pilot!"
        seen_scenes.add(prod)

        # Cloud cover check
        assert chip["cloud_cover_pct"] <= 10.0


def test_frozen_predecessor_integrity():
    """Strict invariant: verifies all 5 frozen artifacts remain byte-for-byte unmodified."""
    for rel_path, expected_hash in FROZEN_HASHES.items():
        full_path = PROJECT_ROOT / rel_path
        assert full_path.exists(), f"Missing frozen artifact: {rel_path}"
        actual_hash = hashlib.sha256(full_path.read_bytes()).hexdigest()
        assert actual_hash == expected_hash, (
            f"MUTATION DETECTED in frozen artifact {rel_path}!\n"
            f"Expected: {expected_hash}\n"
            f"Actual:   {actual_hash}"
        )
