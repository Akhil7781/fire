"""
Stage 8.21 Replacement Preprocessing Script
Extracts 512x512 chips (5120m x 5120m) at 10m common UTM grid from replacement SAFE products.
Aligns spectral bands [B02, B03, B04, B11, B12] (bilinear for B11/B12), resamples SCL (nearest-neighbour).
Performs pixel-level SCL quality screening (AOI contamination and Central 1km contamination).
Outputs RAW (uint16), NORMALIZED (float32 [0, 1]), SCL (uint8), per-chip metadata, and preview PNGs.
Compiles master replacement manifest: data/reference/ds08/manifests/stage8_21/ds08_stage8_21_replacements_processed.json
"""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional

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

REPLACEMENT_MANIFEST_PATH = PROJECT_ROOT / "data" / "reference" / "ds08" / "manifests" / "stage8_21" / "ds08_stage8_21_replacement_manifest.json"
SAFES_DIR = PROJECT_ROOT / "data" / "interim" / "ds08_stage8_21_replacements" / "safes"
OUTPUT_DIR = PROJECT_ROOT / "data" / "interim" / "ds08_stage8_21_replacements"
PROCESSED_MANIFEST_OUT = PROJECT_ROOT / "data" / "reference" / "ds08" / "manifests" / "stage8_21" / "ds08_stage8_21_replacements_processed.json"

REQUIRED_BANDS = ["B02", "B03", "B04", "B11", "B12", "SCL"]
BAND_ORDER_ML = ["B02", "B03", "B04", "B11", "B12"]

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
    0: (0, 0, 0),
    1: (255, 0, 0),
    2: (47, 79, 79),
    3: (139, 69, 19),
    4: (34, 139, 34),
    5: (218, 165, 32),
    6: (0, 0, 205),
    7: (128, 128, 128),
    8: (176, 224, 230),
    9: (255, 255, 255),
    10: (211, 211, 211),
    11: (255, 192, 203),
}


def find_band_file(safe_dir: Path, band: str) -> Path:
    patterns = [f"*_{band}_*.jp2", f"*_{band}.jp2", f"*{band}*.jp2"]
    for pattern in patterns:
        matches = list(safe_dir.rglob(pattern))
        if matches:
            if band in ["B02", "B03", "B04"]:
                ten_m = [m for m in matches if "10m" in m.name.lower()]
                if ten_m:
                    return ten_m[0]
            elif band in ["B11", "B12", "SCL"]:
                twenty_m = [m for m in matches if "20m" in m.name.lower()]
                if twenty_m:
                    return twenty_m[0]
            return matches[0]
    raise FileNotFoundError(f"Band {band} not found in {safe_dir}")


def percentile_stretch(arr: np.ndarray, p_low: float = 2.0, p_high: float = 98.0) -> np.ndarray:
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
    h, w = scl.shape
    rgb_scl = np.zeros((h, w, 3), dtype=np.uint8)
    for class_id, color in SCL_COLORMAP.items():
        rgb_scl[scl == class_id] = color

    fig, ax = plt.subplots(figsize=(7, 7), dpi=150)
    ax.imshow(rgb_scl)
    ax.set_title(f"SCL Quality Mask\n{quality_text}", fontsize=10, fontweight="bold")
    ax.axis("off")

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
    r = percentile_stretch(b04.astype(np.float32))
    g = percentile_stretch(b03.astype(np.float32))
    b = percentile_stretch(b02.astype(np.float32))
    rgb = np.stack([r, g, b], axis=-1)

    fig, ax = plt.subplots(figsize=(7, 7), dpi=150)
    ax.imshow(rgb)

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

    ax.plot(cand_col, cand_row, marker="o", markersize=8, color="red", markeredgecolor="white", markeredgewidth=1.5, label="Candidate Point")
    ax.axvline(cand_col, color="red", linestyle=":", alpha=0.6, linewidth=1)
    ax.axhline(cand_row, color="red", linestyle=":", alpha=0.6, linewidth=1)

    ax.set_title(title_text, fontsize=9, fontweight="bold")
    ax.legend(loc="lower left", fontsize=8, facecolor="black", labelcolor="white")
    ax.axis("off")
    plt.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def process_replacement_chip(
    rec: Dict[str, Any],
    safes_dir: Path,
    output_dir: Path,
) -> Dict[str, Any]:
    sample_id = rec["replacement_sample_id"]
    scene_id = rec["stac_scene_id"]
    safe_name = scene_id if scene_id.endswith(".SAFE") else f"{scene_id}.SAFE"
    safe_dir = safes_dir / safe_name

    if not safe_dir.exists():
        raise FileNotFoundError(f"SAFE directory not found for {sample_id}: {safe_dir}")

    band_paths = {}
    for b in REQUIRED_BANDS:
        band_paths[b] = find_band_file(safe_dir, b)

    with rasterio.open(band_paths["B02"]) as ds_ref:
        target_crs = ds_ref.crs
        ref_transform = ds_ref.transform
        ref_width = ds_ref.width
        ref_height = ds_ref.height

    transformer = pyproj.Transformer.from_crs("EPSG:4326", target_crs, always_xy=True)
    cand_lon = rec["longitude"]
    cand_lat = rec["latitude"]
    cand_x, cand_y = transformer.transform(cand_lon, cand_lat)

    col_cont = (cand_x - ref_transform.c) / ref_transform.a
    row_cont = (cand_y - ref_transform.f) / ref_transform.e

    col_start = int(round(col_cont - 256.0))
    row_start = int(round(row_cont - 256.0))
    col_end = col_start + 512
    row_end = row_start + 512

    if col_start < 0 or col_end > ref_width or row_start < 0 or row_end > ref_height:
        raise ValueError(
            f"Candidate {sample_id} AOI extends outside scene boundary: "
            f"cols [{col_start}:{col_end}] in {ref_width}, rows [{row_start}:{row_end}] in {ref_height}"
        )

    chip_x_min = ref_transform.c + col_start * ref_transform.a
    chip_x_max = chip_x_min + 512 * 10.0
    chip_y_max = ref_transform.f + row_start * ref_transform.e
    chip_y_min = chip_y_max - 512 * 10.0

    if not (chip_x_min <= cand_x <= chip_x_max and chip_y_min <= cand_y <= chip_y_max):
        raise ValueError(f"CRITICAL: Candidate coordinate outside chip bounds!")

    cand_col_in_chip = col_cont - col_start
    cand_row_in_chip = row_cont - row_start

    chip_transform = rasterio.Affine(10.0, 0.0, chip_x_min, 0.0, -10.0, chip_y_max)
    win_10m = Window(col_off=col_start, row_off=row_start, width=512, height=512)

    raw_bands = {}
    for b in ["B02", "B03", "B04"]:
        with rasterio.open(band_paths[b]) as ds:
            arr = ds.read(1, window=win_10m)
            assert arr.shape == (512, 512)
            assert arr.dtype == np.uint16
            raw_bands[b] = arr

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
        assert scl_10m.shape == (512, 512)
        assert scl_10m.dtype == np.uint8

    spectral_raw = np.stack([raw_bands[b] for b in BAND_ORDER_ML], axis=0)
    assert spectral_raw.shape == (5, 512, 512)
    assert spectral_raw.dtype == np.uint16
    assert not np.isnan(spectral_raw).any()
    assert not np.isinf(spectral_raw).any()

    spectral_normalized = np.clip(spectral_raw.astype(np.float32) / 10000.0, 0.0, 1.0)
    assert spectral_normalized.shape == (5, 512, 512)
    assert spectral_normalized.dtype == np.float32

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

    c_r = int(round(cand_row_in_chip))
    c_c = int(round(cand_col_in_chip))
    scl_center = scl_10m[c_r - 50 : c_r + 50, c_c - 50 : c_c + 50]
    assert scl_center.shape == (100, 100)

    center_cloud_pixels = int(np.isin(scl_center, [8, 9, 10]).sum())
    center_shadow_pixels = int((scl_center == 3).sum())
    center_invalid_pixels = int(np.isin(scl_center, [0, 1]).sum())
    center_contaminated_pixels = center_cloud_pixels + center_shadow_pixels
    center_clean_pixels = 10000 - center_contaminated_pixels - center_invalid_pixels

    center_contamination_pct = round((center_contaminated_pixels / 10000.0) * 100.0, 4)
    center_cloud_pct = round((center_cloud_pixels / 10000.0) * 100.0, 4)
    center_shadow_pct = round((center_shadow_pixels / 10000.0) * 100.0, 4)
    center_clean_pct = round((center_clean_pixels / 10000.0) * 100.0, 4)

    # Standard threshold applies (0.0% cloud candidate)
    if aoi_contamination_pct <= 5.0 and center_contamination_pct <= 5.0:
        quality_status = "PASS"
    elif center_contamination_pct <= 10.0:
        quality_status = "CONDITIONAL"
    else:
        quality_status = "REJECT"

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

    chip_out_dir = output_dir / "pilot" / sample_id
    chip_out_dir.mkdir(parents=True, exist_ok=True)

    raw_path = chip_out_dir / "spectral_raw.npy"
    norm_path = chip_out_dir / "spectral_normalized.npy"
    scl_path = chip_out_dir / "scl.npy"
    meta_path = chip_out_dir / "metadata.json"

    np.save(raw_path, spectral_raw)
    np.save(norm_path, spectral_normalized)
    np.save(scl_path, scl_10m)

    previews_dir = output_dir / "previews" / sample_id
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
        f"{sample_id} (REPLACES {rec['replaces_sample_id']} | {rec['candidate_stratum_id']}: {rec['expected_target_class']})\n"
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

    chip_metadata = {
        "sample_id": sample_id,
        "replaces_sample_id": rec["replaces_sample_id"],
        "v4_candidate_id": rec["v4_candidate_id"],
        "source_product": safe_name,
        "cdse_uuid": rec.get("cdse_product_uuid"),
        "mgrs_tile": rec["mgrs_tile"],
        "assigned_fold": rec["assigned_fold"],
        "acquisition_datetime": rec.get("sensing_time_utc"),
        "crs": str(target_crs),
        "resolution_m": 10,
        "chip_size_px": 512,
        "chip_size_m": 5120,
        "bands": REQUIRED_BANDS,
        "band_order_ml": BAND_ORDER_ML,
        "spectral_shape": list(spectral_raw.shape),
        "scl_shape": list(scl_10m.shape),
        "cloud_metadata_pct": rec.get("cloud_cover_pct"),
        "cloud_scl_pct": aoi_cloud_pct,
        "shadow_scl_pct": aoi_shadow_pct,
        "central_1km_contamination_pct": center_contamination_pct,
        "quality_status": quality_status,
        "human_confirmed_label": None,
        "expected_target_class": rec["expected_target_class"],
        "candidate_stratum_id": rec["candidate_stratum_id"],
        "facility_name": rec["facility_name"],
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


def process_replacements(
    manifest_path: Path = REPLACEMENT_MANIFEST_PATH,
    safes_dir: Path = SAFES_DIR,
    output_dir: Path = OUTPUT_DIR,
    manifest_out: Path = PROCESSED_MANIFEST_OUT,
) -> Dict[str, Any]:
    print("=" * 80)
    print("STAGE 8.21: REPLACEMENT CHIP PREPROCESSING")
    print("=" * 80)

    with open(manifest_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    records = data["replacement_records"]
    processed = []
    status_counts = {"PASS": 0, "CONDITIONAL": 0, "REJECT": 0}

    for r in records:
        sid = r["replacement_sample_id"]
        print(f"\nProcessing replacement chip: {sid} (replaces {r['replaces_sample_id']}: {r['facility_name']})...")
        meta = process_replacement_chip(r, safes_dir, output_dir)
        processed.append(meta)
        status_counts[meta["quality_status"]] += 1
        print(f"  Quality Status: {meta['quality_status']}")
        print(f"  AOI Contamination: {meta['cloud_scl_pct'] + meta['shadow_scl_pct']:.2f}%")
        print(f"  Central 1km Contamination: {meta['central_1km_contamination_pct']:.2f}%")
        print(f"  Candidate Point: ({meta['chip_pixel_col']}, {meta['chip_pixel_row']})")

    out_data = {
        "manifest_name": "ds08_stage8_21_replacements_processed",
        "stage": "8.21",
        "version": "1.0.0",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "total_chips": len(processed),
        "status_distribution": status_counts,
        "records": processed,
    }

    manifest_out.parent.mkdir(parents=True, exist_ok=True)
    with open(manifest_out, "w", encoding="utf-8") as f:
        json.dump(out_data, f, indent=2)

    print(f"\nSaved processed replacement manifest to: {manifest_out}")
    print(f"Status distribution: {status_counts}")
    return out_data


if __name__ == "__main__":
    process_replacements()
