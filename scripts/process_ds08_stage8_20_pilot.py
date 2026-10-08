"""
DS08 Stage 8.20 - Sentinel-2 Pilot Preprocessing Script
Extracts 512x512 chips (5120m x 5120m) at 10m common grid from downloaded SAFE products.
Aligns spectral bands [B02, B03, B04, B11, B12] (bilinear for B11/B12), resamples SCL (nearest-neighbour).
Performs pixel-level SCL quality screening (AOI contamination and Central 1km contamination).
Outputs RAW (uint16), NORMALIZED (float32 [0, 1]), SCL (uint8), per-chip metadata, and preview PNGs.
Compiles master manifest: data/reference/ds08/manifests/stage8_20/ds08_stage8_20_pilot_processed.json
"""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.patches as patches
import matplotlib.pyplot as plt
import numpy as np
import pyproj
import rasterio
from rasterio.windows import Window
from rasterio.warp import reproject, Resampling

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_V4_PATH = PROJECT_ROOT / "data" / "reference" / "ds08" / "manifests" / "stage8_19e" / "ds08_expansion_candidates_v4.json"
DEFAULT_SAFES_DIR = PROJECT_ROOT / "data" / "interim" / "ds08_stage8_20_pilot" / "safes"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "interim" / "ds08_stage8_20_pilot"
DEFAULT_MANIFEST_OUT = PROJECT_ROOT / "data" / "reference" / "ds08" / "manifests" / "stage8_20" / "ds08_stage8_20_pilot_processed.json"

APPROVED_PILOT_CHIP_IDS = [
    "DS08_EXP_S1_003",
    "DS08_EXP_S1_002",
    "DS08_EXP_S1_004",
    "DS08_EXP_S2_001",
    "DS08_EXP_S3_001",
    "DS08_EXP_S4_001",
    "DS08_EXP_S5_001",
    "DS08_EXP_S6_001",
]

REQUIRED_BANDS = ["B02", "B03", "B04", "B11", "B12", "SCL"]
BAND_ORDER_ML = ["B02", "B03", "B04", "B11", "B12"]

# SCL class definitions
SCL_CLASSES = {
    0: "NO_DATA",
    1: "SATURATED_DEFECTIVE",
    2: "DARK_AREA_PIXELS",
    3: "CLOUD_SHADOWS",
    4: "VEGETATION",
    5: "NOT_VEGETATED",
    6: "WATER",
    7: "UNCLASSIFIED",
    8: "CLOUD_MEDIUM_PROBABILITY",
    9: "CLOUD_HIGH_PROBABILITY",
    10: "THIN_CIRRUS",
    11: "SNOW_ICE",
}

SCL_COLORMAP = {
    0: (0, 0, 0),          # NO_DATA - Black
    1: (255, 0, 0),        # SATURATED_DEFECTIVE - Red
    2: (47, 79, 79),       # DARK_AREA_PIXELS - Dark Slate Gray
    3: (139, 69, 19),      # CLOUD_SHADOWS - Saddle Brown
    4: (34, 139, 34),      # VEGETATION - Forest Green
    5: (218, 165, 32),     # NOT_VEGETATED - Goldenrod
    6: (0, 0, 205),        # WATER - Medium Blue
    7: (128, 128, 128),    # UNCLASSIFIED - Gray
    8: (176, 224, 230),    # CLOUD_MEDIUM_PROBABILITY - Powder Blue
    9: (255, 255, 255),    # CLOUD_HIGH_PROBABILITY - White
    10: (211, 211, 211),   # THIN_CIRRUS - Light Gray
    11: (255, 192, 203),   # SNOW_ICE - Pink
}


def find_band_file(safe_dir: Path, band: str) -> Path:
    """Finds JP2 file corresponding to band in SAFE directory."""
    patterns = [
        f"*_{band}_*.jp2",
        f"*_{band}.jp2",
        f"*{band}*.jp2",
    ]
    for pattern in patterns:
        matches = list(safe_dir.rglob(pattern))
        if matches:
            if band in ["B02", "B03", "B04"]:
                # Ensure 10m
                ten_m = [m for m in matches if "10m" in m.name.lower()]
                if ten_m:
                    return ten_m[0]
            elif band in ["B11", "B12", "SCL"]:
                # Ensure 20m
                twenty_m = [m for m in matches if "20m" in m.name.lower()]
                if twenty_m:
                    return twenty_m[0]
            return matches[0]
    raise FileNotFoundError(f"Band {band} not found in {safe_dir}")


def percentile_stretch(arr: np.ndarray, p_low: float = 2.0, p_high: float = 98.0) -> np.ndarray:
    """Applies robust percentile contrast stretch for visualization."""
    valid = arr[~np.isnan(arr)]
    if len(valid) == 0:
        return np.zeros_like(arr, dtype=np.uint8)
    vmin = np.percentile(valid, p_low)
    vmax = np.percentile(valid, p_high)
    if vmax <= vmin:
        vmax = vmin + 1.0
    stretched = np.clip((arr - vmin) / (vmax - vmin), 0.0, 1.0)
    return (stretched * 255.0).astype(np.uint8)


def generate_rgb_preview(b04: np.ndarray, b03: np.ndarray, b02: np.ndarray, out_path: Path):
    """Generates True Color RGB preview PNG."""
    r = percentile_stretch(b04.astype(np.float32))
    g = percentile_stretch(b03.astype(np.float32))
    b = percentile_stretch(b02.astype(np.float32))
    rgb = np.stack([r, g, b], axis=-1)

    fig, ax = plt.subplots(figsize=(6, 6), dpi=150)
    ax.imshow(rgb)
    ax.set_title("True Color (B04, B03, B02)", fontsize=11, fontweight="bold")
    ax.axis("off")
    plt.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def generate_swir_preview(b12: np.ndarray, b11: np.ndarray, b04: np.ndarray, out_path: Path):
    """Generates False Color SWIR preview PNG (B12, B11, B04)."""
    r = percentile_stretch(b12.astype(np.float32))
    g = percentile_stretch(b11.astype(np.float32))
    b = percentile_stretch(b04.astype(np.float32))
    swir = np.stack([r, g, b], axis=-1)

    fig, ax = plt.subplots(figsize=(6, 6), dpi=150)
    ax.imshow(swir)
    ax.set_title("SWIR False Color (B12, B11, B04)", fontsize=11, fontweight="bold")
    ax.axis("off")
    plt.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def generate_scl_mask_preview(scl: np.ndarray, out_path: Path, quality_text: str):
    """Generates SCL categorical mask visualization with legend."""
    h, w = scl.shape
    rgb_scl = np.zeros((h, w, 3), dtype=np.uint8)
    for class_id, color in SCL_COLORMAP.items():
        rgb_scl[scl == class_id] = color

    fig, ax = plt.subplots(figsize=(7, 7), dpi=150)
    ax.imshow(rgb_scl)
    ax.set_title(f"SCL Quality Mask\n{quality_text}", fontsize=10, fontweight="bold")
    ax.axis("off")

    # Add custom legend for present classes
    present_classes = np.unique(scl)
    legend_elements = [
        patches.Patch(
            facecolor=np.array(SCL_COLORMAP[c]) / 255.0,
            edgecolor="black",
            label=f"{c}: {SCL_CLASSES.get(c, 'UNKNOWN')}"
        )
        for c in present_classes if c in SCL_COLORMAP
    ]
    ax.legend(handles=legend_elements, loc="upper right", bbox_to_anchor=(1.45, 1.0), fontsize=7)

    plt.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def generate_candidate_overlay(
    b04: np.ndarray,
    b03: np.ndarray,
    b02: np.ndarray,
    cand_col: float,
    cand_row: float,
    out_path: Path,
    title_text: str,
):
    """Generates candidate point overlay and 1 km central box on RGB preview."""
    r = percentile_stretch(b04.astype(np.float32))
    g = percentile_stretch(b03.astype(np.float32))
    b = percentile_stretch(b02.astype(np.float32))
    rgb = np.stack([r, g, b], axis=-1)

    fig, ax = plt.subplots(figsize=(7, 7), dpi=150)
    ax.imshow(rgb)

    # 1 km central evaluation box (100x100 pixels centered at candidate)
    box_x = cand_col - 50.0
    box_y = cand_row - 50.0
    rect = patches.Rectangle(
        (box_x, box_y),
        100,
        100,
        linewidth=2,
        edgecolor="yellow",
        facecolor="none",
        linestyle="--",
        label="Central 1 km Box (100x100 px)",
    )
    ax.add_patch(rect)

    # Candidate point marker (red crosshair and red circle)
    ax.plot(cand_col, cand_row, marker="o", markersize=8, color="red", markeredgecolor="white", markeredgewidth=1.5, label="Candidate Point")
    ax.axvline(cand_col, color="red", linestyle=":", alpha=0.6, linewidth=1)
    ax.axhline(cand_row, color="red", linestyle=":", alpha=0.6, linewidth=1)

    ax.set_title(title_text, fontsize=9, fontweight="bold")
    ax.legend(loc="lower left", fontsize=8, facecolor="black", labelcolor="white")
    ax.axis("off")
    plt.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def process_chip(
    rec: Dict[str, Any],
    safes_dir: Path,
    output_dir: Path,
) -> Dict[str, Any]:
    """Processes a single Sentinel-2 pilot chip."""
    chip_id = rec["chip_id"]
    scene_id = rec["stac_scene_id"]
    safe_name = scene_id if scene_id.endswith(".SAFE") else f"{scene_id}.SAFE"
    safe_dir = safes_dir / safe_name

    if not safe_dir.exists():
        raise FileNotFoundError(f"SAFE directory not found for {chip_id}: {safe_dir}")

    # 1. Locate required JP2 bands
    band_paths = {}
    for b in REQUIRED_BANDS:
        band_paths[b] = find_band_file(safe_dir, b)

    # 2. Open reference band (B02 at 10m)
    with rasterio.open(band_paths["B02"]) as ds_ref:
        target_crs = ds_ref.crs
        ref_transform = ds_ref.transform
        ref_width = ds_ref.width
        ref_height = ds_ref.height

    # 3. Project candidate coordinates to target CRS
    transformer = pyproj.Transformer.from_crs("EPSG:4326", target_crs, always_xy=True)
    cand_lon = rec["longitude"]
    cand_lat = rec["latitude"]
    cand_x, cand_y = transformer.transform(cand_lon, cand_lat)

    # 4. Continuous pixel indices in 10m scene
    col_cont = (cand_x - ref_transform.c) / ref_transform.a
    row_cont = (cand_y - ref_transform.f) / ref_transform.e

    # 5. Snap 512x512 AOI centered on candidate
    col_start = int(round(col_cont - 256.0))
    row_start = int(round(row_cont - 256.0))
    col_end = col_start + 512
    row_end = row_start + 512

    if col_start < 0 or col_end > ref_width or row_start < 0 or row_end > ref_height:
        raise ValueError(
            f"Candidate {chip_id} AOI extends outside scene boundary: "
            f"cols [{col_start}:{col_end}] in {ref_width}, rows [{row_start}:{row_end}] in {ref_height}"
        )

    # Chip physical bounds in target CRS
    chip_x_min = ref_transform.c + col_start * ref_transform.a
    chip_x_max = chip_x_min + 512 * 10.0
    chip_y_max = ref_transform.f + row_start * ref_transform.e
    chip_y_min = chip_y_max - 512 * 10.0

    # Verification: candidate coordinate strictly inside chip
    if not (chip_x_min <= cand_x <= chip_x_max and chip_y_min <= cand_y <= chip_y_max):
        raise ValueError(f"CRITICAL: Candidate coordinate ({cand_x}, {cand_y}) outside chip bounds [{chip_x_min}, {chip_x_max}] x [{chip_y_min}, {chip_y_max}]")

    cand_col_in_chip = col_cont - col_start
    cand_row_in_chip = row_cont - row_start

    if not (0.0 <= cand_col_in_chip < 512.0 and 0.0 <= cand_row_in_chip < 512.0):
        raise ValueError(f"CRITICAL: Candidate pixel position ({cand_col_in_chip}, {cand_row_in_chip}) outside [0, 512)!")

    # Chip transform
    chip_transform = rasterio.Affine(10.0, 0.0, chip_x_min, 0.0, -10.0, chip_y_max)
    win_10m = Window(col_off=col_start, row_off=row_start, width=512, height=512)

    # 6. Read 10m native bands (B02, B03, B04)
    raw_bands = {}
    for b in ["B02", "B03", "B04"]:
        with rasterio.open(band_paths[b]) as ds:
            arr = ds.read(1, window=win_10m)
            assert arr.shape == (512, 512), f"Band {b} shape {arr.shape} != (512, 512)"
            assert arr.dtype == np.uint16, f"Band {b} dtype {arr.dtype} != uint16"
            raw_bands[b] = arr

    # 7. Resample 20m bands (B11, B12) using Bilinear interpolation
    for b in ["B11", "B12"]:
        with rasterio.open(band_paths[b]) as ds_20m:
            dst_arr = np.empty((512, 512), dtype=np.uint16)
            reproject(
                source=rasterio.band(ds_20m, 1),
                destination=dst_arr,
                src_transform=ds_20m.transform,
                src_crs=ds_20m.crs,
                dst_transform=chip_transform,
                dst_crs=target_crs,
                resampling=Resampling.bilinear,
            )
            raw_bands[b] = dst_arr

    # 8. Resample SCL using Nearest-Neighbour
    with rasterio.open(band_paths["SCL"]) as ds_scl:
        scl_10m = np.empty((512, 512), dtype=np.uint8)
        reproject(
            source=rasterio.band(ds_scl, 1),
            destination=scl_10m,
            src_transform=ds_scl.transform,
            src_crs=ds_scl.crs,
            dst_transform=chip_transform,
            dst_crs=target_crs,
            resampling=Resampling.nearest,
        )
        assert scl_10m.shape == (512, 512), f"SCL shape {scl_10m.shape} != (512, 512)"
        assert scl_10m.dtype == np.uint8, f"SCL dtype {scl_10m.dtype} != uint8"

    # 9. Stack raw spectral bands: [B02, B03, B04, B11, B12]
    spectral_raw = np.stack([raw_bands[b] for b in BAND_ORDER_ML], axis=0)
    assert spectral_raw.shape == (5, 512, 512)
    assert spectral_raw.dtype == np.uint16

    # Verify no NaN or Inf
    assert not np.isnan(spectral_raw).any(), "NaN found in spectral_raw"
    assert not np.isinf(spectral_raw).any(), "Inf found in spectral_raw"

    # 10. Normalized ML representation: float32, DN / 10000.0 clipped to [0.0, 1.0]
    spectral_normalized = np.clip(spectral_raw.astype(np.float32) / 10000.0, 0.0, 1.0)
    assert spectral_normalized.shape == (5, 512, 512)
    assert spectral_normalized.dtype == np.float32
    assert not np.isnan(spectral_normalized).any(), "NaN found in spectral_normalized"
    assert not np.isinf(spectral_normalized).any(), "Inf found in spectral_normalized"

    # 11. SCL Quality Screening
    total_pixels = 512 * 512
    cloud_pixels = int(np.isin(scl_10m, [8, 9, 10]).sum())
    shadow_pixels = int((scl_10m == 3).sum())
    invalid_pixels = int(np.isin(scl_10m, [0, 1]).sum())
    contaminated_pixels = cloud_pixels + shadow_pixels
    clean_pixels = total_pixels - contaminated_pixels - invalid_pixels

    aoi_contamination_pct = round((contaminated_pixels / total_pixels) * 100.0, 4)
    aoi_cloud_pct = round((cloud_pixels / total_pixels) * 100.0, 4)
    aoi_shadow_pct = round((shadow_pixels / total_pixels) * 100.0, 4)
    aoi_clean_pct = round((clean_pixels / total_pixels) * 100.0, 4)

    # 12. Central 1 km check (100x100 pixels centered at candidate)
    c_r = int(round(cand_row_in_chip))
    c_c = int(round(cand_col_in_chip))
    scl_center = scl_10m[c_r - 50 : c_r + 50, c_c - 50 : c_c + 50]
    assert scl_center.shape == (100, 100), f"Center shape {scl_center.shape} != (100, 100)"

    center_cloud_pixels = int(np.isin(scl_center, [8, 9, 10]).sum())
    center_shadow_pixels = int((scl_center == 3).sum())
    center_invalid_pixels = int(np.isin(scl_center, [0, 1]).sum())
    center_contaminated_pixels = center_cloud_pixels + center_shadow_pixels
    center_clean_pixels = 10000 - center_contaminated_pixels - center_invalid_pixels

    center_contamination_pct = round((center_contaminated_pixels / 10000.0) * 100.0, 4)
    center_cloud_pct = round((center_cloud_pixels / 10000.0) * 100.0, 4)
    center_shadow_pct = round((center_shadow_pixels / 10000.0) * 100.0, 4)
    center_clean_pct = round((center_clean_pixels / 10000.0) * 100.0, 4)

    # 13. Quality Decision
    cloud_exception = rec.get("cloud_exception_id")
    if cloud_exception == "DEC-U5":
        # DEC-U5 cloud exception test: central 1km must be clean (<= 10.0%)
        if center_contamination_pct <= 5.0:
            quality_status = "CONDITIONAL" if aoi_contamination_pct > 5.0 else "PASS"
        elif center_contamination_pct <= 10.0:
            quality_status = "CONDITIONAL"
        else:
            quality_status = "REJECT"
    else:
        # Standard threshold: AOI contamination <= 5.0% and Central 1 km <= 5.0%
        if aoi_contamination_pct <= 5.0 and center_contamination_pct <= 5.0:
            quality_status = "PASS"
        elif center_contamination_pct <= 10.0:
            quality_status = "CONDITIONAL"
        else:
            quality_status = "REJECT"

    # 14. Per-band statistics
    spectral_stats = {}
    for idx, b in enumerate(BAND_ORDER_ML):
        band_arr = spectral_raw[idx]
        spectral_stats[b] = {
            "min": int(np.min(band_arr)),
            "max": int(np.max(band_arr)),
            "mean": round(float(np.mean(band_arr)), 2),
            "std": round(float(np.std(band_arr)), 2),
            "nan_count": int(np.isnan(band_arr).sum()),
            "inf_count": int(np.isinf(band_arr).sum()),
        }

    # 15. Save processed chip files
    chip_out_dir = output_dir / "pilot" / chip_id
    chip_out_dir.mkdir(parents=True, exist_ok=True)

    raw_path = chip_out_dir / "spectral_raw.npy"
    norm_path = chip_out_dir / "spectral_normalized.npy"
    scl_path = chip_out_dir / "scl.npy"
    meta_path = chip_out_dir / "metadata.json"

    np.save(raw_path, spectral_raw)
    np.save(norm_path, spectral_normalized)
    np.save(scl_path, scl_10m)

    # 16. Generate human-review previews
    previews_dir = output_dir / "previews" / chip_id
    previews_dir.mkdir(parents=True, exist_ok=True)

    rgb_preview_path = previews_dir / "rgb_preview.png"
    swir_preview_path = previews_dir / "swir_preview.png"
    scl_mask_path = previews_dir / "scl_mask.png"
    overlay_path = previews_dir / "candidate_overlay.png"

    generate_rgb_preview(raw_bands["B04"], raw_bands["B03"], raw_bands["B02"], rgb_preview_path)
    generate_swir_preview(raw_bands["B12"], raw_bands["B11"], raw_bands["B04"], swir_preview_path)

    scl_text = (
        f"AOI Contam: {aoi_contamination_pct:.2f}% | Clean: {aoi_clean_pct:.2f}%\n"
        f"Central 1km Contam: {center_contamination_pct:.2f}% | Status: {quality_status}"
    )
    generate_scl_mask_preview(scl_10m, scl_mask_path, scl_text)

    overlay_title = (
        f"{chip_id} ({rec['candidate_stratum_id']}: {rec['expected_target_class']})\n"
        f"Lat: {cand_lat:.4f}, Lon: {cand_lon:.4f} | Quality: {quality_status}\n"
        f"AOI Contam: {aoi_contamination_pct:.2f}%, Central 1km: {center_contamination_pct:.2f}%"
    )
    generate_candidate_overlay(
        raw_bands["B04"],
        raw_bands["B03"],
        raw_bands["B02"],
        cand_col_in_chip,
        cand_row_in_chip,
        overlay_path,
        overlay_title,
    )

    # 17. Chip metadata object
    chip_metadata = {
        "chip_id": chip_id,
        "source_product": safe_name,
        "cdse_uuid": rec.get("cdse_uuid"),
        "mgrs_tile": rec["mgrs_tile"],
        "acquisition_datetime": rec.get("s2_acquisition_datetime_utc", rec.get("acquisition_timestamp")),
        "crs": str(target_crs),
        "resolution_m": 10,
        "chip_size_px": 512,
        "chip_size_m": 5120,
        "bands": REQUIRED_BANDS,
        "band_order_ml": BAND_ORDER_ML,
        "spectral_shape": list(spectral_raw.shape),
        "scl_shape": list(scl_10m.shape),
        "cloud_metadata_pct": rec.get("s2_cloud_cover_percent", rec.get("cloud_cover_percentage")),
        "cloud_scl_pct": aoi_cloud_pct,
        "shadow_scl_pct": aoi_shadow_pct,
        "central_1km_contamination_pct": center_contamination_pct,
        "quality_status": quality_status,
        "human_confirmed_label": None,
        "expected_target_class": rec["expected_target_class"],
        "candidate_stratum_id": rec["candidate_stratum_id"],
        "candidate_lat": cand_lat,
        "candidate_lon": cand_lon,
        "projected_x": cand_x,
        "projected_y": cand_y,
        "chip_pixel_col": round(cand_col_in_chip, 3),
        "chip_pixel_row": round(cand_row_in_chip, 3),
        "chip_bounds_utm": {
            "x_min": chip_x_min,
            "x_max": chip_x_max,
            "y_min": chip_y_min,
            "y_max": chip_y_max,
        },
        "resampling_methods": {
            "B02": "native_10m",
            "B03": "native_10m",
            "B04": "native_10m",
            "B11": "bilinear_20m_to_10m",
            "B12": "bilinear_20m_to_10m",
            "SCL": "nearest_neighbour_20m_to_10m",
        },
        "normalization_applied": "DN / 10000.0, clipped to [0.0, 1.0]",
        "scl_metrics": {
            "total_pixels": total_pixels,
            "cloud_pixels": cloud_pixels,
            "shadow_pixels": shadow_pixels,
            "invalid_pixels": invalid_pixels,
            "contaminated_pixels": contaminated_pixels,
            "clean_pixels": clean_pixels,
            "aoi_contamination_pct": aoi_contamination_pct,
            "aoi_cloud_pct": aoi_cloud_pct,
            "aoi_shadow_pct": aoi_shadow_pct,
            "aoi_clean_pct": aoi_clean_pct,
            "central_1km_pixels": 10000,
            "central_1km_cloud_pixels": center_cloud_pixels,
            "central_1km_shadow_pixels": center_shadow_pixels,
            "central_1km_invalid_pixels": center_invalid_pixels,
            "central_1km_contaminated_pixels": center_contaminated_pixels,
            "central_1km_clean_pixels": center_clean_pixels,
            "central_1km_contamination_pct": center_contamination_pct,
            "central_1km_cloud_pct": center_cloud_pct,
            "central_1km_shadow_pct": center_shadow_pct,
            "central_1km_clean_pct": center_clean_pct,
        },
        "spectral_stats": spectral_stats,
        "artifacts": {
            "raw_path": str(raw_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "normalized_path": str(norm_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "scl_path": str(scl_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "metadata_path": str(meta_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "rgb_preview_path": str(rgb_preview_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "swir_preview_path": str(swir_preview_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "scl_mask_path": str(scl_mask_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "candidate_overlay_path": str(overlay_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        },
    }

    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(chip_metadata, f, indent=2)

    return chip_metadata


def process_pilot(
    v4_path: Path = DEFAULT_V4_PATH,
    safes_dir: Path = DEFAULT_SAFES_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    manifest_out: Path = DEFAULT_MANIFEST_OUT,
    target_chip_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Processes all approved pilot chips and generates processed manifest."""
    print("=" * 80)
    print("STAGE 8.20: SENTINEL-2 PILOT CHIP PREPROCESSING")
    print("=" * 80)

    chip_ids_to_process = target_chip_ids or APPROVED_PILOT_CHIP_IDS
    print(f"Target chips: {len(chip_ids_to_process)} chips -> {chip_ids_to_process}")

    with open(v4_path, "r", encoding="utf-8") as f:
        v4_data = json.load(f)

    v4_records = {r["chip_id"]: r for r in v4_data["records"]}

    processed_records = []
    status_counts = {"PASS": 0, "CONDITIONAL": 0, "REJECT": 0}

    for cid in chip_ids_to_process:
        if cid not in v4_records:
            raise KeyError(f"Chip {cid} not found in V4 manifest!")
        rec = v4_records[cid]
        print(f"\nProcessing chip: {cid} ({rec['candidate_stratum_id']}: {rec['expected_target_class']})...")
        chip_meta = process_chip(rec, safes_dir, output_dir)
        processed_records.append(chip_meta)
        status_counts[chip_meta["quality_status"]] += 1
        print(f"  Quality Status: {chip_meta['quality_status']}")
        print(f"  AOI Contamination: {chip_meta['cloud_scl_pct'] + chip_meta['shadow_scl_pct']:.2f}% (Cloud: {chip_meta['cloud_scl_pct']:.2f}%, Shadow: {chip_meta['shadow_scl_pct']:.2f}%)")
        print(f"  Central 1km Contamination: {chip_meta['central_1km_contamination_pct']:.2f}%")
        print(f"  Candidate Point: ({chip_meta['chip_pixel_col']}, {chip_meta['chip_pixel_row']}) in 512x512 grid")

    manifest_data = {
        "manifest_name": "ds08_stage8_20_pilot_processed",
        "stage": "8.20",
        "version": "1.0.0",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "total_chips": len(processed_records),
        "approved_cohort_count": len(APPROVED_PILOT_CHIP_IDS),
        "bands": REQUIRED_BANDS,
        "band_order_ml": BAND_ORDER_ML,
        "spectral_shape": [5, 512, 512],
        "scl_shape": [512, 512],
        "resolution_m": 10,
        "chip_size_px": 512,
        "chip_size_m": 5120,
        "status_distribution": status_counts,
        "records": processed_records,
    }

    manifest_out.parent.mkdir(parents=True, exist_ok=True)
    with open(manifest_out, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2)

    print(f"\nSaved processed manifest to: {manifest_out}")
    print(f"Status distribution: {status_counts}")
    return manifest_data


def main():
    parser = argparse.ArgumentParser(description="Stage 8.20 Sentinel-2 Pilot Preprocessing")
    parser.add_argument("--v4-manifest", type=Path, default=DEFAULT_V4_PATH, help="Path to V4 manifest")
    parser.add_argument("--safes-dir", type=Path, default=DEFAULT_SAFES_DIR, help="Path to extracted SAFEs directory")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Path to pilot output directory")
    parser.add_argument("--manifest-out", type=Path, default=DEFAULT_MANIFEST_OUT, help="Path to output processed manifest")
    parser.add_argument("--chip-ids", nargs="*", default=None, help="Optional subset of chip IDs to process")
    args = parser.parse_args()

    process_pilot(
        v4_path=args.v4_manifest,
        safes_dir=args.safes_dir,
        output_dir=args.output_dir,
        manifest_out=args.manifest_out,
        target_chip_ids=args.chip_ids,
    )


if __name__ == "__main__":
    main()
