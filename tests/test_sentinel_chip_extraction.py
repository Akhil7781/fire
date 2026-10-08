"""
Unit tests for Sentinel-2 L2A Single Chip Extraction (Stage 8.5).

Verifies:
- AOI UTM calculation and bounds
- Processing API payload construction
- Multi-band GeoTIFF structural validation (5 bands, 512x512, 10m res, EPSG:32643, FLOAT32)
- Rejection of invalid rasters (wrong band count, wrong shape, wrong dtype, out of bounds)
- Non-authoritative RGB and SWIR preview generation
- Metadata sidecar schema, checksum consistency, and zero credential leakage
- Frozen predecessor artifact integrity
"""

from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import sys
from typing import Any, Dict
import unittest.mock as mock

import numpy as np
from PIL import Image
import pytest
import rasterio
from rasterio.transform import from_origin

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.extract_test_sentinel_chip import (
    BAND_ORDER,
    CHIP_PIXELS,
    CHIP_SPAN_M,
    DEFAULT_JSON_PATH,
    DEFAULT_PREVIEW_DIR,
    DEFAULT_TIFF_PATH,
    PIXEL_RESOLUTION_M,
    UTM_EPSG,
    VALIDATED_FIRMS,
    VALIDATED_SENTINEL2,
    build_processing_payload,
    compute_aoi,
    generate_preview_images,
    save_metadata_sidecar,
    validate_raster,
)

FROZEN_HASHES = {
    "models/tcn/best_tcn.pt": "dfa2decb772cf71b65601a4cb83a12b73ee1706ff47e2acb23a9f53c84506f16",
    "models/deep_sad/best_deep_sad.pt": "a7f99f521cf56e3d651101259543f967eee535df82736aae3ae4271922947eaa",
    "models/yolo/infrastructure/best_infrastructure.pt": "bad5d3942f469b74a7778762696bb390174619cb0f403dbcc93be1066ba5dcf6",
    "models/yolo/fire_smoke/best_fire_smoke.pt": "29ab42eda1cd05d7141525927ab1c502c249082b5b2bbf5f2e0c9e8847c3d227",
    "data/embeddings/fusion/india_2025_tcn_sad_aligned.parquet": "49505cb4705516aef8d77af628debc485be894fae75dc19e3269b3ba6df7e931",
}


def test_compute_aoi():
    """Verifies 5.12 km x 5.12 km AOI computation centered on FIRMS detection."""
    aoi = compute_aoi(
        lat=VALIDATED_FIRMS["latitude"],
        lon=VALIDATED_FIRMS["longitude"],
        chip_span_m=CHIP_SPAN_M,
        utm_epsg=UTM_EPSG,
    )

    assert aoi["utm_epsg"] == 32643
    assert aoi["chip_span_meters"] == 5120.0
    min_x, min_y, max_x, max_y = aoi["utm_bbox"]
    assert pytest.approx(max_x - min_x, abs=0.1) == 5120.0
    assert pytest.approx(max_y - min_y, abs=0.1) == 5120.0

    # FIRMS coordinates must be strictly inside bbox
    center_x = aoi["center_utm"]["x"]
    center_y = aoi["center_utm"]["y"]
    assert min_x < center_x < max_x
    assert min_y < center_y < max_y


def test_build_processing_payload():
    """Verifies that Processing API payload correctly implements all specifications."""
    aoi = compute_aoi()
    payload = build_processing_payload(aoi)

    # Input bounds
    bounds = payload["input"]["bounds"]
    assert bounds["bbox"] == aoi["utm_bbox"]
    assert "EPSG/0/32643" in bounds["properties"]["crs"]

    # Input data filters and resampling
    data = payload["input"]["data"][0]
    assert data["type"] == "sentinel-2-l2a"
    assert data["dataFilter"]["maxCloudCoverage"] == 10
    assert data["processing"]["upsampling"] == "BILINEAR"
    assert data["processing"]["downsampling"] == "BILINEAR"

    # Output specifications
    out = payload["output"]
    assert out["width"] == 512
    assert out["height"] == 512
    assert out["responses"][0]["format"]["type"] == "image/tiff"

    # Evalscript specifications
    script = payload["evalscript"]
    assert "//VERSION=3" in script
    for band in BAND_ORDER:
        assert f'"{band}"' in script
    assert 'units: "REFLECTANCE"' in script
    assert 'sampleType: "FLOAT32"' in script
    assert "bands: 5" in script


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
    """Helper function to create synthetic test GeoTIFFs."""
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


def test_validate_raster_success(tmp_path: Path):
    """Verifies that a valid 5-band 512x512 GeoTIFF passes all 15 validation checks."""
    test_tif = tmp_path / "valid_test.tif"
    _create_mock_geotiff(test_tif, bands=5, width=512, height=512, dtype="float32", res=10.0)

    val = validate_raster(
        test_tif,
        firms_lat=VALIDATED_FIRMS["latitude"],
        firms_lon=VALIDATED_FIRMS["longitude"],
        expected_bands=5,
        expected_dim=512,
        expected_res=10.0,
    )

    assert val["is_valid"] is True
    assert val["band_count"] == 5
    assert val["width"] == 512
    assert val["height"] == 512
    assert val["firms_point_inside_chip"] is True
    assert len(val["band_statistics"]) == 5
    for band_name in BAND_ORDER:
        assert band_name in val["band_statistics"]
        assert val["band_statistics"][band_name]["valid_pixel_count"] == 512 * 512


def test_validate_raster_rejections(tmp_path: Path):
    """Verifies that validate_raster raises ValueError for non-compliant rasters."""
    # 1. Wrong band count (4 bands instead of 5)
    tif_4bands = tmp_path / "wrong_bands.tif"
    _create_mock_geotiff(tif_4bands, bands=4)
    with pytest.raises(ValueError, match="Expected 5 bands"):
        validate_raster(tif_4bands)

    # 2. Wrong dimension (256x256 instead of 512x512)
    tif_wrong_dim = tmp_path / "wrong_dim.tif"
    _create_mock_geotiff(tif_wrong_dim, width=256, height=256)
    with pytest.raises(ValueError, match="Expected dimensions 512x512"):
        validate_raster(tif_wrong_dim)

    # 3. Wrong data type (int16 instead of float32)
    tif_wrong_dtype = tmp_path / "wrong_dtype.tif"
    _create_mock_geotiff(tif_wrong_dtype, dtype="int16")
    with pytest.raises(ValueError, match="Expected all bands to be float32"):
        validate_raster(tif_wrong_dtype)

    # 4. Wrong resolution (20m instead of 10m)
    tif_wrong_res = tmp_path / "wrong_res.tif"
    _create_mock_geotiff(tif_wrong_res, res=20.0)
    with pytest.raises(ValueError, match="Expected pixel resolution ~10.0m"):
        validate_raster(tif_wrong_res)

    # 5. Empty band (all NaN)
    tif_empty = tmp_path / "empty_band.tif"
    _create_mock_geotiff(tif_empty, fill_empty=True)
    with pytest.raises(ValueError, match="is entirely empty"):
        validate_raster(tif_empty)

    # 6. FIRMS point outside raster bounds
    tif_far = tmp_path / "far_bounds.tif"
    _create_mock_geotiff(tif_far, top_left=(100000.0, 100000.0))
    with pytest.raises(ValueError, match="not inside raster bounds"):
        validate_raster(tif_far)


def test_generate_preview_images(tmp_path: Path):
    """Verifies generation of RGB and SWIR PNG preview images."""
    test_tif = tmp_path / "preview_source.tif"
    _create_mock_geotiff(test_tif, bands=5, width=512, height=512)

    previews = generate_preview_images(test_tif, preview_dir=tmp_path, file_prefix="test_chip")
    rgb_path = previews["rgb_preview"]
    swir_path = previews["swir_preview"]

    assert rgb_path.exists()
    assert swir_path.exists()

    with Image.open(rgb_path) as img:
        assert img.size == (512, 512)
        assert img.mode == "RGB"

    with Image.open(swir_path) as img:
        assert img.size == (512, 512)
        assert img.mode == "RGB"


def test_save_metadata_sidecar_and_security(tmp_path: Path):
    """Verifies metadata schema and strict absence of secret tokens."""
    json_path = tmp_path / "metadata_test.json"
    firms_info = VALIDATED_FIRMS
    sentinel2_info = VALIDATED_SENTINEL2
    aoi = compute_aoi()
    extraction_info = {
        "processing_api_endpoint": "https://sh.dataspace.copernicus.eu/process/v1",
        "aoi": aoi,
        "crs": "EPSG:32643",
        "output_width_pixels": 512,
        "output_height_pixels": 512,
        "output_resolution_meters": 10.0,
        "band_order": BAND_ORDER,
        "input_units": "REFLECTANCE",
        "resampling_method": "BILINEAR",
        "output_data_type": "FLOAT32",
        "extraction_timestamp_utc": "2026-09-29T13:00:00Z",
        "file_size_bytes": 3022470,
        "sha256_checksum": "abcdef123456",
        "previews": {},
        "band_statistics": {},
    }

    save_metadata_sidecar(json_path, firms_info, sentinel2_info, extraction_info)
    assert json_path.exists()

    content = json_path.read_text(encoding="utf-8")
    assert "client_secret" not in content.lower()
    assert "access_token" not in content.lower()
    assert "bearer" not in content.lower()
    assert "authorization" not in content.lower()

    data = json.loads(content)
    assert data["status"] == "VALIDATED_SINGLE_CHIP_EXTRACTION"
    assert data["firms_detection"]["detection_id"] == VALIDATED_FIRMS["detection_id"]
    assert data["sentinel2_scene"]["product_id"] == VALIDATED_SENTINEL2["product_id"]
    assert data["extraction"]["output_width_pixels"] == 512
    assert data["extraction"]["band_order"] == BAND_ORDER


def test_live_chip_integrity_if_downloaded():
    """If the live authoritative chip exists, verifies its raster and checksum integrity."""
    if not DEFAULT_TIFF_PATH.exists():
        pytest.skip("Live chip GeoTIFF not yet downloaded.")

    assert DEFAULT_JSON_PATH.exists()
    val = validate_raster(DEFAULT_TIFF_PATH)
    assert val["is_valid"] is True
    assert val["band_count"] == 5
    assert val["width"] == 512
    assert val["height"] == 512
    assert val["firms_point_inside_chip"] is True

    # Verify checksum matches sidecar JSON
    with open(DEFAULT_JSON_PATH, "r", encoding="utf-8") as f:
        meta = json.load(f)

    calculated_hash = hashlib.sha256(DEFAULT_TIFF_PATH.read_bytes()).hexdigest()
    assert meta["extraction"]["sha256_checksum"] == calculated_hash


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
