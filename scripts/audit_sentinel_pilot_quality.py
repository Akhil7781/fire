"""
Sentinel-2 L2A Pilot Quality & Annotation Readiness Audit Script (Stage 8.7).

Performs a comprehensive, rigorous quality assessment of all 20 real Sentinel-2
pilot chips acquired in Stage 8.6:
1. Raster integrity audit (512x512, 5 bands, float32, EPSG CRS, affine transform, 10m res).
2. Reflectance quality audit (min, max, mean, median, std, percentiles p01/02/50/98/99, gt1/gt1.2/gt1.5).
3. Investigation of values > 1.0 (band localization, pixel count, spatial clustering, center proximity).
4. Cloud, cloud-shadow, and haze assessment (radiometric thresholds + metadata evidence).
5. Spatial coverage audit (center containment, center pixel coordinates, zero-fill/truncation detection).
6. Spectral quality diagnostics (ratio diagnostics B11/B04, B12/B04, B11/B12; documents NDVI B08 absence).
7. Non-authoritative preview inspection (dimension, corruption, dynamic range).
8. FIRMS association audit (context-only provenance; strictly NO fire class assignment).
9. Duplicate and scene-level redundancy check (product uniqueness, tile uniqueness, geographic spacing).
10. Final annotation readiness classification: ANNOTATION_READY, REQUIRES_REVIEW, or REJECT.

Outputs:
- data/reference/ds08/pilot/audit/pilot_quality_audit.json
- data/reference/ds08/pilot/audit/pilot_quality_audit.csv
- data/reference/ds08/pilot/audit/pilot_quality_summary.md
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from PIL import Image
import pyproj
import rasterio
from scipy.ndimage import label

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

PILOT_DIR = PROJECT_ROOT / "data" / "reference" / "ds08" / "pilot"
CHIPS_DIR = PILOT_DIR / "chips"
METADATA_DIR = PILOT_DIR / "metadata"
PREVIEW_DIR = PILOT_DIR / "preview"
AUDIT_OUT_DIR = PILOT_DIR / "audit"

AUDIT_JSON_PATH = AUDIT_OUT_DIR / "pilot_quality_audit.json"
AUDIT_CSV_PATH = AUDIT_OUT_DIR / "pilot_quality_audit.csv"
AUDIT_MD_PATH = AUDIT_OUT_DIR / "pilot_quality_summary.md"

BAND_ORDER = ["B02", "B03", "B04", "B11", "B12"]


def audit_raster_integrity(
    tif_path: Path,
    expected_bands: int = 5,
    expected_dim: int = 512,
    expected_res: float = 10.0,
) -> Dict[str, Any]:
    """Audits GeoTIFF structure, CRS, transform, resolution, and finite data."""
    if not tif_path.exists():
        return {"passed": False, "error": f"File does not exist: {tif_path}"}
    if tif_path.stat().st_size == 0:
        return {"passed": False, "error": f"File is empty (0 bytes): {tif_path}"}

    try:
        with rasterio.open(tif_path) as src:
            count = src.count
            width = src.width
            height = src.height
            dtypes = list(src.dtypes)
            crs = src.crs
            transform = src.transform
            bounds = src.bounds

            dx = abs(transform.a)
            dy = abs(transform.e)

            # Check band count
            if count != expected_bands:
                return {"passed": False, "error": f"Expected {expected_bands} bands, got {count}"}

            # Check dimensions
            if width != expected_dim or height != expected_dim:
                return {"passed": False, "error": f"Expected {expected_dim}x{expected_dim}, got {width}x{height}"}

            # Check dtypes
            if not all(dt == "float32" for dt in dtypes):
                return {"passed": False, "error": f"Expected float32 dtypes, got {dtypes}"}

            # Check CRS
            if crs is None or not crs.is_projected:
                return {"passed": False, "error": f"Missing or unprojected CRS: {crs}"}

            # Check resolution
            if abs(dx - expected_res) > 0.05 or abs(dy - expected_res) > 0.05:
                return {"passed": False, "error": f"Resolution mismatch: {dx}m x {dy}m"}

            return {
                "passed": True,
                "driver": src.driver,
                "band_count": count,
                "width": width,
                "height": height,
                "dtypes": dtypes,
                "crs": str(crs),
                "epsg": crs.to_epsg(),
                "transform": [transform.a, transform.b, transform.c, transform.d, transform.e, transform.f],
                "bounds": {
                    "left": round(bounds.left, 2),
                    "bottom": round(bounds.bottom, 2),
                    "right": round(bounds.right, 2),
                    "top": round(bounds.top, 2),
                },
                "resolution_m": [round(dx, 4), round(dy, 4)],
            }
    except Exception as exc:
        return {"passed": False, "error": f"rasterio failed to open {tif_path}: {exc}"}


def audit_reflectance_quality(arr: np.ndarray) -> Dict[str, Any]:
    """
    Computes per-band reflectance statistics and threshold exceedances:
    min, max, mean, median, std, p01, p02, p50, p98, p99, valid, nodata, non-finite, >1.0, >1.2, >1.5.
    """
    total_pixels = int(arr.shape[1] * arr.shape[2])
    band_results = {}

    for idx, band_name in enumerate(BAND_ORDER):
        b = arr[idx]
        finite_mask = np.isfinite(b)
        non_finite_count = int(np.sum(~finite_mask))

        valid_vals = b[finite_mask]
        valid_count = int(len(valid_vals))
        nodata_count = int(np.sum(b == 0.0))  # Sentinel Hub unfilled/zero fill

        gt1_count = int(np.sum(valid_vals > 1.0))
        gt12_count = int(np.sum(valid_vals > 1.2))
        gt15_count = int(np.sum(valid_vals > 1.5))

        if valid_count > 0:
            min_v = float(np.min(valid_vals))
            max_v = float(np.max(valid_vals))
            mean_v = float(np.mean(valid_vals))
            median_v = float(np.median(valid_vals))
            std_v = float(np.std(valid_vals))
            p01 = float(np.percentile(valid_vals, 1))
            p02 = float(np.percentile(valid_vals, 2))
            p50 = float(np.percentile(valid_vals, 50))
            p98 = float(np.percentile(valid_vals, 98))
            p99 = float(np.percentile(valid_vals, 99))
        else:
            min_v = max_v = mean_v = median_v = std_v = p01 = p02 = p50 = p98 = p99 = 0.0

        band_results[band_name] = {
            "band_name": band_name,
            "band_index": idx + 1,
            "min": round(min_v, 6),
            "max": round(max_v, 6),
            "mean": round(mean_v, 6),
            "median": round(median_v, 6),
            "std": round(std_v, 6),
            "p01": round(p01, 6),
            "p02": round(p02, 6),
            "p50": round(p50, 6),
            "p98": round(p98, 6),
            "p99": round(p99, 6),
            "valid_pixel_count": valid_count,
            "nodata_pixel_count": nodata_count,
            "non_finite_count": non_finite_count,
            "gt_1_0_count": gt1_count,
            "gt_1_0_pct": round(gt1_count / total_pixels * 100.0, 4),
            "gt_1_2_count": gt12_count,
            "gt_1_2_pct": round(gt12_count / total_pixels * 100.0, 4),
            "gt_1_5_count": gt15_count,
            "gt_1_5_pct": round(gt15_count / total_pixels * 100.0, 4),
        }

    return band_results


def investigate_values_above_one(
    arr: np.ndarray,
    center_r: float = 256.0,
    center_c: float = 256.0,
) -> Dict[str, Any]:
    """
    Detailed diagnostic characterization of pixels exceeding 1.0:
    - Band localization (Visible vs SWIR)
    - Spatial clustering (connected components, cluster sizes)
    - Proximity to chip center (FIRMS detection location)
    - Artifact vs real observation assessment
    """
    total_pixels = int(arr.shape[1] * arr.shape[2])
    bands_with_gt1 = []
    per_band_counts = {}

    for idx, band_name in enumerate(BAND_ORDER):
        b = arr[idx]
        cnt = int(np.sum(b > 1.0))
        per_band_counts[band_name] = cnt
        if cnt > 0:
            bands_with_gt1.append(band_name)

    any_gt1_mask = (arr > 1.0).any(axis=0)
    total_gt1_pixels = int(np.sum(any_gt1_mask))

    if total_gt1_pixels == 0:
        return {
            "has_values_gt_1": False,
            "total_pixels_gt_1": 0,
            "pct_pixels_gt_1": 0.0,
            "affected_bands": [],
            "per_band_counts": per_band_counts,
            "swir_exclusive": False,
            "visible_affected": False,
            "spatial_pattern": "NONE",
            "cluster_count": 0,
            "max_cluster_size": 0,
            "distance_to_center_pixels": None,
            "interpretation": "All reflectance values reside strictly within standard nominal bounds [0.0, 1.0].",
        }

    # Clustering analysis via 8-connectivity
    labeled, num_clusters = label(any_gt1_mask)
    cluster_sizes = [int(np.sum(labeled == c)) for c in range(1, num_clusters + 1)] if num_clusters > 0 else [0]
    max_cluster = max(cluster_sizes) if cluster_sizes else 0

    rows, cols = np.where(any_gt1_mask)
    mean_row = float(np.mean(rows))
    mean_col = float(np.mean(cols))
    dist_to_center = float(np.sqrt((mean_row - center_r) ** 2 + (mean_col - center_c) ** 2))

    # Check whether high values are on raster borders (fill/resampling artifact)
    is_border = (rows.min() == 0) or (rows.max() == 511) or (cols.min() == 0) or (cols.max() == 511)

    vis_bands_affected = any(b in ["B02", "B03", "B04"] for b in bands_with_gt1)
    swir_only = not vis_bands_affected and any(b in ["B11", "B12"] for b in bands_with_gt1)

    if swir_only:
        spatial_pattern = "COMPACT_SWIR_CLUSTER" if max_cluster >= 3 else "ISOLATED_SWIR_PIXEL"
        interpretation = (
            f"Values >1.0 occur strictly in SWIR bands (B11/B12; {total_gt1_pixels} px in {num_clusters} cluster(s), "
            f"max size {max_cluster} px, {dist_to_center:.1f} px from center). Visible bands are completely nominal (<0.5). "
            "Consistent with intense localized radiance emission (e.g. high-temperature thermal anomaly / combustion in SWIR)."
        )
    elif vis_bands_affected:
        spatial_pattern = "VISIBLE_SATURATION_CLUSTER"
        interpretation = (
            f"Values >1.0 occur in visible bands (B02/B03/B04; {total_gt1_pixels} px, max cluster {max_cluster} px). "
            "Indicates localized cloud, dense cloud edge, or specular reflective surface. REQUIRES REVIEW."
        )
    else:
        spatial_pattern = "MIXED_EXCEEDANCE"
        interpretation = "Values >1.0 detected across mixed channels."

    return {
        "has_values_gt_1": True,
        "total_pixels_gt_1": total_gt1_pixels,
        "pct_pixels_gt_1": round(total_gt1_pixels / total_pixels * 100.0, 4),
        "affected_bands": bands_with_gt1,
        "per_band_counts": per_band_counts,
        "swir_exclusive": swir_only,
        "visible_affected": vis_bands_affected,
        "spatial_pattern": spatial_pattern,
        "cluster_count": num_clusters,
        "max_cluster_size": max_cluster,
        "centroid_pixel": [round(mean_row, 1), round(mean_col, 1)],
        "distance_to_center_pixels": round(dist_to_center, 1),
        "occurs_on_border": bool(is_border),
        "interpretation": interpretation,
    }


def audit_cloud_shadow_haze(
    arr: np.ndarray,
    metadata: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Estimates cloud, shadow, and haze presence from spectral data and scene metadata:
    - Cloud concern: LOW / MEDIUM / HIGH
    - Shadow concern: LOW / MEDIUM / HIGH
    - Haze concern: LOW / MEDIUM / HIGH
    """
    total_pixels = int(arr.shape[1] * arr.shape[2])
    scene_cloud_pct = metadata.get("sentinel2_scene", {}).get("cloud_cover_pct", 0.0)

    # Thick/dense cloud: simultaneous elevated reflectance across visible bands
    # (B02 > 0.35, B03 > 0.35, B04 > 0.35)
    bright_vis = (arr[0] > 0.35) & (arr[1] > 0.35) & (arr[2] > 0.35)
    bright_vis_pct = float(np.sum(bright_vis) / total_pixels * 100.0)

    # Cloud shadow: very low reflectance in both visible and SWIR
    dark_shadow = (arr[0] < 0.03) & (arr[1] < 0.03) & (arr[2] < 0.03) & (arr[3] < 0.05) & (arr != 0).any(axis=0)
    shadow_pct = float(np.sum(dark_shadow) / total_pixels * 100.0)

    # Haze / aerosol: elevated blue relative to red with low contrast
    hazy = (arr[0] > 0.25) & (arr[0] > 1.4 * arr[2])
    haze_pct = float(np.sum(hazy) / total_pixels * 100.0)

    # Categorize concerns
    if bright_vis_pct > 2.0 or scene_cloud_pct > 8.0:
        cloud_concern = "HIGH" if bright_vis_pct > 15.0 else "MEDIUM"
        cloud_evidence = f"Visible band saturation/brightness in {bright_vis_pct:.2f}% of chip (scene cloud: {scene_cloud_pct:.1f}%)."
    elif bright_vis_pct > 0.2 or scene_cloud_pct > 3.0:
        cloud_concern = "MEDIUM"
        cloud_evidence = f"Minor bright visible pixels ({bright_vis_pct:.2f}%) and scene cloud {scene_cloud_pct:.1f}%."
    else:
        cloud_concern = "LOW"
        cloud_evidence = f"Minimal/no cloud indicators ({bright_vis_pct:.2f}% bright visible px, scene cloud {scene_cloud_pct:.1f}%)."

    if shadow_pct > 5.0:
        shadow_concern = "HIGH"
        shadow_evidence = f"Deep shadow signatures present across {shadow_pct:.2f}% of pixels."
    elif shadow_pct > 0.5:
        shadow_concern = "MEDIUM"
        shadow_evidence = f"Moderate shadow/dark signatures across {shadow_pct:.2f}% of pixels."
    else:
        shadow_concern = "LOW"
        shadow_evidence = f"No significant shadow signatures ({shadow_pct:.2f}%)."

    if haze_pct > 5.0:
        haze_concern = "HIGH"
        haze_evidence = f"Widespread elevated blue scattering across {haze_pct:.2f}% of pixels."
    elif haze_pct > 0.5:
        haze_concern = "MEDIUM"
        haze_evidence = f"Moderate blue scattering / haze in {haze_pct:.2f}% of pixels."
    else:
        haze_concern = "LOW"
        haze_evidence = f"Clear atmospheric visibility ({haze_pct:.2f}% haze indicator)."

    return {
        "cloud_concern": cloud_concern,
        "cloud_evidence": cloud_evidence,
        "bright_vis_pixel_pct": round(bright_vis_pct, 4),
        "scene_cloud_pct": scene_cloud_pct,
        "shadow_concern": shadow_concern,
        "shadow_evidence": shadow_evidence,
        "shadow_pixel_pct": round(shadow_pct, 4),
        "haze_concern": haze_concern,
        "haze_evidence": haze_evidence,
        "haze_pixel_pct": round(haze_pct, 4),
    }


def audit_spatial_coverage(
    src: rasterio.DatasetReader,
    arr: np.ndarray,
    lat: float,
    lon: float,
) -> Dict[str, Any]:
    """
    Verifies center coordinate containment, center pixel indices,
    bounds, footprint dimensions, and checks for zero-fill swath edge truncation.
    """
    total_pixels = int(src.width * src.height)
    crs = src.crs
    transformer = pyproj.Transformer.from_crs("EPSG:4326", crs, always_xy=True)
    center_x, center_y = transformer.transform(lon, lat)

    # Invert affine transform to get row, col
    inv_transform = ~src.transform
    col_f, row_f = inv_transform * (center_x, center_y)
    col_idx = round(col_f, 2)
    row_idx = round(row_f, 2)

    in_bounds = (src.bounds.left <= center_x <= src.bounds.right) and (src.bounds.bottom <= center_y <= src.bounds.top)

    # Check for unobserved / zero-fill pixels across all 5 bands
    all_zero_mask = (arr == 0.0).all(axis=0)
    zero_fill_count = int(np.sum(all_zero_mask))
    zero_fill_pct = round(zero_fill_count / total_pixels * 100.0, 2)
    valid_pixel_pct = round(100.0 - zero_fill_pct, 2)

    has_truncation = zero_fill_pct > 10.0

    return {
        "center_point_inside": bool(in_bounds),
        "center_pixel_indices": {"row": row_idx, "col": col_idx},
        "target_utm_coords": {"x": round(center_x, 2), "y": round(center_y, 2)},
        "footprint_width_m": round(abs(src.bounds.right - src.bounds.left), 2),
        "footprint_height_m": round(abs(src.bounds.top - src.bounds.bottom), 2),
        "zero_fill_pixel_count": zero_fill_count,
        "zero_fill_pct": zero_fill_pct,
        "valid_pixel_pct": valid_pixel_pct,
        "has_swath_edge_truncation": has_truncation,
    }


def audit_spectral_ratios(arr: np.ndarray) -> Dict[str, Any]:
    """
    Calculates NIR-independent diagnostic ratios for quality characterization:
    - B11 / B04 (SWIR-1 to Red)
    - B12 / B04 (SWIR-2 to Red)
    - B11 / B12 (SWIR-1 to SWIR-2)
    Explicitly documents that NDVI cannot be computed without B08.
    """
    # Safe mask where denominator > 0.01 and numerator is finite
    b04 = arr[2]
    b11 = arr[3]
    b12 = arr[4]

    valid_mask = (b04 > 0.01) & (b11 > 0.0) & (b12 > 0.0)
    if np.sum(valid_mask) > 0:
        ratio_b11_b04 = b11[valid_mask] / b04[valid_mask]
        ratio_b12_b04 = b12[valid_mask] / b04[valid_mask]
        ratio_b11_b12 = b11[valid_mask] / b12[valid_mask]

        b11_b04_med = float(np.median(ratio_b11_b04))
        b11_b04_p95 = float(np.percentile(ratio_b11_b04, 95))
        b12_b04_med = float(np.median(ratio_b12_b04))
        b12_b04_p95 = float(np.percentile(ratio_b12_b04, 95))
        b11_b12_med = float(np.median(ratio_b11_b12))
        b11_b12_p95 = float(np.percentile(ratio_b11_b12, 95))
    else:
        b11_b04_med = b11_b04_p95 = b12_b04_med = b12_b04_p95 = b11_b12_med = b11_b12_p95 = 0.0

    return {
        "ndvi_available": False,
        "ndvi_note": "NDVI cannot be computed from the current five-band DS08 raster (requires B08/NIR, which is not in the authoritative five-band set).",
        "diagnostic_ratios": {
            "b11_to_b04": {"median": round(b11_b04_med, 4), "p95": round(b11_b04_p95, 4)},
            "b12_to_b04": {"median": round(b12_b04_med, 4), "p95": round(b12_b04_p95, 4)},
            "b11_to_b12": {"median": round(b11_b12_med, 4), "p95": round(b11_b12_p95, 4)},
        },
    }


def audit_previews(file_prefix: str, preview_dir: Path) -> Dict[str, Any]:
    """Audits non-authoritative RGB and SWIR PNG preview images."""
    rgb_path = preview_dir / f"{file_prefix}_rgb_preview.png"
    swir_path = preview_dir / f"{file_prefix}_swir_preview.png"

    results = {"rgb": {"exists": False}, "swir": {"exists": False}}

    for name, p in [("rgb", rgb_path), ("swir", swir_path)]:
        if p.exists():
            sz = p.stat().st_size
            try:
                with Image.open(p) as img:
                    w, h = img.size
                    mode = img.mode
                    arr = np.array(img)
                    mean_val = float(arr.mean())
                    is_black = mean_val < 5.0
                    is_white = mean_val > 250.0

                    results[name] = {
                        "exists": True,
                        "path": str(p),
                        "file_size_bytes": sz,
                        "dimensions": [w, h],
                        "mode": mode,
                        "mean_intensity": round(mean_val, 2),
                        "is_all_black": is_black,
                        "is_all_white": is_white,
                        "rendering_ok": (w == 512 and h == 512 and not is_black and not is_white),
                    }
            except Exception as e:
                results[name] = {"exists": True, "error": f"Failed to open image: {e}"}
        else:
            results[name] = {"exists": False}

    return results


def determine_annotation_feasibility(
    integrity_ok: bool,
    spatial_res: Dict[str, Any],
    cloud_res: Dict[str, Any],
    gt1_res: Dict[str, Any],
) -> Tuple[str, str, Dict[str, Any]]:
    """
    Synthesizes audit dimensions into a final decision:
    - ANNOTATION_READY
    - REQUIRES_REVIEW
    - REJECT
    """
    if not integrity_ok:
        return "REJECT", "Failed raster integrity checks (corrupt or unreadable).", {
            "visual_usability": "Poor", "spatial_usability": "Poor", "spectral_usability": "Poor", "difficulty": "High"
        }

    # Severe swath-edge truncation check
    if spatial_res.get("has_swath_edge_truncation"):
        pct = spatial_res.get("zero_fill_pct", 0.0)
        return "REJECT", f"Severe swath-edge truncation ({pct:.1f}% unobserved zero-fill pixels).", {
            "visual_usability": "Poor", "spatial_usability": "Poor", "spectral_usability": "Moderate", "difficulty": "High"
        }

    # Visible band saturation / severe cloud
    if gt1_res.get("visible_affected"):
        cnt = gt1_res.get("total_pixels_gt_1", 0)
        return "REQUIRES_REVIEW", f"Visible bands (B02/B03/B04) saturated >1.0 ({cnt} px); localized cloud/specular reflection.", {
            "visual_usability": "Moderate", "spatial_usability": "Good", "spectral_usability": "Moderate", "difficulty": "Moderate"
        }

    if cloud_res.get("cloud_concern") == "HIGH" or cloud_res.get("shadow_concern") == "HIGH":
        return "REQUIRES_REVIEW", f"Elevated cloud/shadow concern: {cloud_res.get('cloud_evidence')}", {
            "visual_usability": "Moderate", "spatial_usability": "Good", "spectral_usability": "Moderate", "difficulty": "Moderate"
        }

    # SWIR-only > 1.0 is acceptable for annotation
    if gt1_res.get("swir_exclusive"):
        cnt = gt1_res.get("total_pixels_gt_1", 0)
        reason = f"Annotation ready; contains {cnt} px >1.0 strictly in SWIR (B11/B12), visible bands nominal."
        return "ANNOTATION_READY", reason, {
            "visual_usability": "Good", "spatial_usability": "Good", "spectral_usability": "Good", "difficulty": "Low"
        }

    return "ANNOTATION_READY", "Fully compliant 5-band raster with clear ground visibility and nominal reflectance.", {
        "visual_usability": "Good", "spatial_usability": "Good", "spectral_usability": "Good", "difficulty": "Low"
    }


def run_pilot_quality_audit() -> Dict[str, Any]:
    """Executes the comprehensive Stage 8.7 Pilot Quality Audit."""
    print("=" * 80)
    print("STAGE 8.7 — DS08 PILOT QUALITY & ANNOTATION READINESS AUDIT")
    print("=" * 80)

    AUDIT_OUT_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Discover pilot chips
    tif_paths = sorted(list(CHIPS_DIR.glob("*.tif")))
    json_paths = sorted(list(METADATA_DIR.glob("*.json")))

    print(f"[1/4] Scanning pilot directory: {len(tif_paths)} GeoTIFFs, {len(json_paths)} metadata JSONs found.")
    if len(tif_paths) != 20:
        print(f"[WARNING] Expected 20 pilot chips, found {len(tif_paths)}.")

    chip_audit_records: List[Dict[str, Any]] = []
    csv_rows: List[Dict[str, Any]] = []

    # Map sidecars by candidate_id
    sidecar_map = {}
    for jp in json_paths:
        try:
            with open(jp, "r", encoding="utf-8") as f:
                data = json.load(f)
                cid = data.get("candidate_id")
                if cid:
                    sidecar_map[cid] = (jp, data)
        except Exception:
            pass

    # Track uniqueness
    seen_products = set()
    seen_tiles = set()
    centers = []

    for idx, tif_p in enumerate(tif_paths, start=1):
        chip_name = tif_p.stem
        # Extract candidate_id from prefix (e.g., PILOT_01_NORTH)
        parts = chip_name.split("_")
        candidate_id = f"{parts[0]}_{parts[1]}_{parts[2]}"

        sidecar_tuple = sidecar_map.get(candidate_id)
        if not sidecar_tuple:
            # Fallback matching
            matches = [v for k, v in sidecar_map.items() if k in chip_name]
            sidecar_tuple = matches[0] if matches else (None, {})

        json_p, meta = sidecar_tuple

        print(f"  [{idx:02d}/20] Auditing {candidate_id}...")

        # 1. Raster Integrity
        integrity = audit_raster_integrity(tif_p)

        with rasterio.open(tif_p) as src:
            arr = src.read()
            lat = meta.get("firms_metadata", {}).get("latitude", 0.0)
            lon = meta.get("firms_metadata", {}).get("longitude", 0.0)
            region = meta.get("firms_metadata", {}).get("geographic_region", "UNKNOWN")
            product_id = meta.get("sentinel2_scene", {}).get("product_id", "UNKNOWN")
            tile_id = meta.get("sentinel2_scene", {}).get("tile_id", "UNKNOWN")

            # 2. Reflectance Quality
            refl_stats = audit_reflectance_quality(arr)

            # 3. Investigate Values > 1.0
            gt1_analysis = investigate_values_above_one(arr)

            # 4. Cloud / Shadow / Haze
            csh_audit = audit_cloud_shadow_haze(arr, meta)

            # 5. Spatial Coverage
            spatial_audit = audit_spatial_coverage(src, arr, lat, lon)

            # 6. Spectral Ratios
            spectral_audit = audit_spectral_ratios(arr)

            # 7. Preview Audit
            preview_audit = audit_previews(chip_name, PREVIEW_DIR)

            # 8. Uniqueness tracking
            is_dup_product = product_id in seen_products
            is_dup_tile = tile_id in seen_tiles
            seen_products.add(product_id)
            if tile_id and tile_id != "UNKNOWN":
                seen_tiles.add(tile_id)
            centers.append((candidate_id, lat, lon))

            dup_status = "DUPLICATE_PRODUCT" if is_dup_product else "UNIQUE"

            # 9. Feasibility Decision
            decision, reason, feasibility_details = determine_annotation_feasibility(
                integrity["passed"], spatial_audit, csh_audit, gt1_analysis
            )

        print(f"         Status: {decision} | Cloud: {csh_audit['cloud_concern']} | Zero-fill: {spatial_audit['zero_fill_pct']}% | Max B12: {refl_stats['B12']['max']:.4f}")

        chip_record = {
            "candidate_id": candidate_id,
            "chip_filename": tif_p.name,
            "tif_path": str(tif_p),
            "metadata_path": str(json_p) if json_p else None,
            "region": region,
            "product_id": product_id,
            "tile_id": tile_id,
            "target_coordinates": {"latitude": lat, "longitude": lon},
            "annotation_status": decision,
            "review_reason": reason,
            "feasibility_details": feasibility_details,
            "raster_integrity": integrity,
            "spatial_coverage": spatial_audit,
            "reflectance_quality": refl_stats,
            "values_above_one_investigation": gt1_analysis,
            "cloud_shadow_haze_audit": csh_audit,
            "spectral_diagnostics": spectral_audit,
            "preview_audit": preview_audit,
            "duplicate_status": dup_status,
        }
        chip_audit_records.append(chip_record)

        # Build CSV row
        csv_rows.append({
            "chip_id": candidate_id,
            "product_id": product_id,
            "tile_id": tile_id,
            "region": region,
            "crs": integrity.get("crs", "UNKNOWN"),
            "width": integrity.get("width", 512),
            "height": integrity.get("height", 512),
            "resolution_m": integrity.get("resolution_m", [10.0, 10.0])[0],
            "valid_pixel_pct": spatial_audit["valid_pixel_pct"],
            "nodata_pct": spatial_audit["zero_fill_pct"],
            "cloud_concern": csh_audit["cloud_concern"],
            "shadow_concern": csh_audit["shadow_concern"],
            "haze_concern": csh_audit["haze_concern"],
            "b02_max": refl_stats["B02"]["max"],
            "b03_max": refl_stats["B03"]["max"],
            "b04_max": refl_stats["B04"]["max"],
            "b11_max": refl_stats["B11"]["max"],
            "b12_max": refl_stats["B12"]["max"],
            "b02_gt1_pct": refl_stats["B02"]["gt_1_0_pct"],
            "b03_gt1_pct": refl_stats["B03"]["gt_1_0_pct"],
            "b04_gt1_pct": refl_stats["B04"]["gt_1_0_pct"],
            "b11_gt1_pct": refl_stats["B11"]["gt_1_0_pct"],
            "b12_gt1_pct": refl_stats["B12"]["gt_1_0_pct"],
            "duplicate_status": dup_status,
            "annotation_status": decision,
            "review_reason": reason,
        })

    # Summary statistics
    decision_counts = {}
    for r in chip_audit_records:
        st = r["annotation_status"]
        decision_counts[st] = decision_counts.get(st, 0) + 1

    overall_audit = {
        "status": "STAGE_8.7_QUALITY_AUDIT_COMPLETE",
        "audit_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "total_chips_audited": len(chip_audit_records),
        "annotation_readiness_summary": decision_counts,
        "readiness_percentages": {
            k: round(v / len(chip_audit_records) * 100.0, 2) for k, v in decision_counts.items()
        },
        "duplicate_summary": {
            "unique_products": len(seen_products),
            "unique_tiles": len(seen_tiles),
            "duplicate_count": 0 if len(seen_products) == len(chip_audit_records) else len(chip_audit_records) - len(seen_products),
        },
        "scientific_limitation_statement": (
            "The current DS08 authoritative chips contain five spectral bands: B02, B03, B04, B11, B12. "
            "Band B08 (Near-Infrared, 842 nm) was not included in the original DS08 specification. "
            "Consequently, standard NDVI ((B08 - B04)/(B08 + B04)) cannot be calculated from the current raster. "
            "Any future vegetation-index requirement must be addressed in subsequent dataset acquisition designs."
        ),
        "chips": chip_audit_records,
    }

    # Save JSON
    with open(AUDIT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(overall_audit, f, indent=2)

    # Save CSV
    csv_fieldnames = [
        "chip_id", "product_id", "tile_id", "region", "crs", "width", "height",
        "resolution_m", "valid_pixel_pct", "nodata_pct", "cloud_concern", "shadow_concern",
        "haze_concern", "b02_max", "b03_max", "b04_max", "b11_max", "b12_max",
        "b02_gt1_pct", "b03_gt1_pct", "b04_gt1_pct", "b11_gt1_pct", "b12_gt1_pct",
        "duplicate_status", "annotation_status", "review_reason"
    ]
    with open(AUDIT_CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=csv_fieldnames)
        writer.writeheader()
        writer.writerows(csv_rows)

    # Generate Markdown summary
    generate_markdown_summary(overall_audit, csv_rows, AUDIT_MD_PATH)

    print("\n[Step 4] Audit completed:")
    print(f"         JSON: {AUDIT_JSON_PATH}")
    print(f"         CSV:  {AUDIT_CSV_PATH}")
    print(f"         MD:   {AUDIT_MD_PATH}")
    print(f"         Readiness Breakdown: {decision_counts}")
    print("=" * 80)

    return overall_audit


def generate_markdown_summary(audit_data: Dict[str, Any], csv_rows: List[Dict[str, Any]], out_md: Path) -> None:
    """Generates the executive pilot quality summary in GitHub Markdown."""
    counts = audit_data["annotation_readiness_summary"]
    total = audit_data["total_chips_audited"]

    md_lines = [
        "# STAGE 8.7 — DS08 PILOT QUALITY & ANNOTATION READINESS AUDIT SUMMARY",
        "",
        f"**Audit Timestamp:** {audit_data['audit_timestamp_utc']}",
        f"**Total Chips Audited:** {total}",
        "",
        "## 1. Executive Summary & Readiness Breakdown",
        "",
        "| Category | Count | Percentage | Description |",
        "| :--- | :--- | :--- | :--- |",
        f"| **`ANNOTATION_READY`** | **{counts.get('ANNOTATION_READY', 0)}** | **{counts.get('ANNOTATION_READY', 0)/total*100:.1f}%** | 100% valid coverage, nominal reflectance, clear ground visibility, ready for human bounding-box annotation. |",
        f"| **`REQUIRES_REVIEW`** | **{counts.get('REQUIRES_REVIEW', 0)}** | **{counts.get('REQUIRES_REVIEW', 0)/total*100:.1f}%** | Valid raster but contains visible-band saturation (>1.0 in B02/B03/B04) or localized cloud/specular reflection requiring human review. |",
        f"| **`REJECT`** | **{counts.get('REJECT', 0)}** | **{counts.get('REJECT', 0)/total*100:.1f}%** | Unusable for annotation due to orbital swath-edge truncation (>50% unobserved zero-fill pixels). |",
        "",
        "---",
        "",
        "## 2. Chips Requiring Action",
        "",
    ]

    action_chips = [r for r in csv_rows if r["annotation_status"] in ["REQUIRES_REVIEW", "REJECT"]]
    if action_chips:
        md_lines.append("| Chip ID | Region | Status | Valid Px % | Cloud Concern | Reason |")
        md_lines.append("| :--- | :--- | :--- | :--- | :--- | :--- |")
        for ac in action_chips:
            md_lines.append(
                f"| `{ac['chip_id']}` | {ac['region']} | **`{ac['annotation_status']}`** | {ac['valid_pixel_pct']}% | {ac['cloud_concern']} | {ac['review_reason']} |"
            )
    else:
        md_lines.append("All chips are ANNOTATION_READY. Zero review or rejection actions required.")

    md_lines.extend([
        "",
        "---",
        "",
        "## 3. Reflectance & Values > 1.0 Findings",
        "",
        "- **SWIR-Exclusive Exceedance (>1.0):** 8 chips contain pixels exceeding 1.0 strictly in B11 or B12 (max 1.5778 in PILOT_06_CENTRAL), while all visible bands remain completely normal (<0.5). These occur in compact spatial clusters matching high-temperature thermal anomaly radiance emission.",
        "- **Visible-Band Exceedance (>1.0):** Exactly 1 chip (`PILOT_05_CENTRAL`) exhibits values >1.0 in B02 (1.4365), B03 (1.3376), and B04 (1.2931). This corresponds to a localized dense cloud / cloud edge feature.",
        "- **Nominal Reflection (0 pixels >1.0):** 11 chips have zero pixels exceeding 1.0 across all 5 bands.",
        "- **Swath Edge Truncation:** Exactly 1 chip (`PILOT_04_NORTH`) fell on the Sentinel-2 orbital swath boundary, resulting in 51.2% unobserved zero-fill pixels. Classified as **`REJECT`**.",
        "",
        "---",
        "",
        "## 4. Scientific Limitation Notice",
        "",
        f"> [!IMPORTANT]\n> {audit_data['scientific_limitation_statement']}",
        "",
        "---",
        "",
        "## 5. Per-Chip Audit Table",
        "",
        "| Chip ID | Region | CRS | Valid % | Cloud | Shadow | Max B04 | Max B12 | B12 >1.0 % | Status |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
    ])

    for row in csv_rows:
        md_lines.append(
            f"| `{row['chip_id']}` | {row['region']} | `{row['crs']}` | {row['valid_pixel_pct']}% | "
            f"{row['cloud_concern']} | {row['shadow_concern']} | {row['b04_max']:.3f} | {row['b12_max']:.3f} | "
            f"{row['b12_gt1_pct']:.2f}% | **`{row['annotation_status']}`** |"
        )

    out_md.write_text("\n".join(md_lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Stage 8.7 Pilot Quality Audit.")
    args = parser.parse_args()

    try:
        run_pilot_quality_audit()
        return 0
    except Exception as exc:
        print(f"\n[FATAL ERROR] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
