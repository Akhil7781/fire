"""
Stage 8.21 Phase B: Sentinel-2 Chip Inventory Builder
Constructs a machine-readable inventory of all Stage 8.20 Sentinel-2 chips.
Excludes all target classes (preserving strict separation from visual labels).
Outputs JSON and Parquet artifacts under data/interim/.
"""

import json
from pathlib import Path
from typing import Any, Dict, List
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent

PROCESSED_MANIFEST_V20 = PROJECT_ROOT / "data" / "reference" / "ds08" / "manifests" / "stage8_20" / "ds08_stage8_20_pilot_processed.json"
OUTPUT_INVENTORY_JSON = PROJECT_ROOT / "data" / "interim" / "ds08_stage8_21_chip_inventory.json"
OUTPUT_INVENTORY_PARQUET = PROJECT_ROOT / "data" / "interim" / "ds08_stage8_21_chip_inventory.parquet"


def build_chip_inventory(
    manifest_path: Path = PROCESSED_MANIFEST_V20,
    output_json: Path = OUTPUT_INVENTORY_JSON,
    output_parquet: Path = OUTPUT_INVENTORY_PARQUET,
) -> List[Dict[str, Any]]:
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest_data = json.load(f)

    records = manifest_data["records"]
    inventory_items = []

    for r in records:
        cid = r["chip_id"]
        status = r["quality_status"]
        aoi_contam = r["scl_metrics"]["aoi_contamination_pct"]
        c1k_contam = r["scl_metrics"]["central_1km_contamination_pct"]

        if status == "PASS":
            acc_status = "ACCEPTED"
            rej_reason = None
        else:
            acc_status = "REJECTED"
            if c1k_contam > 10.0:
                rej_reason = (
                    f"Central 1 km target evaluation area exceeds 10.0% contamination limit: "
                    f"{c1k_contam:.2f}% cloud/shadow (SCL 8,9,10,3). Target is visually occluded."
                )
            else:
                rej_reason = (
                    f"AOI contamination {aoi_contam:.2f}% exceeds standard 5.0% threshold."
                )

        item = {
            "sample_id": cid,
            "source_product": r["source_product"],
            "product_uuid": r.get("cdse_uuid"),
            "acquisition_timestamp": r.get("acquisition_datetime"),
            "candidate_latitude": float(r["candidate_lat"]),
            "candidate_longitude": float(r["candidate_lon"]),
            "mgrs_tile": r["mgrs_tile"],
            "chip_dimensions": [int(r["chip_size_px"]), int(r["chip_size_px"])],
            "resolution": float(r["resolution_m"]),
            "spectral_channels": ["B02", "B03", "B04", "B11", "B12"],
            "aoi_scl_contamination": float(aoi_contam),
            "central_1km_scl_contamination": float(c1k_contam),
            "acceptance_rejection_status": acc_status,
            "rejection_reason": rej_reason,
            "path_to_raw_array": r["artifacts"]["raw_path"],
            "path_to_normalized_array": r["artifacts"]["normalized_path"],
            "path_to_scl": r["artifacts"]["scl_path"],
            "path_to_previews": f"data/interim/ds08_stage8_20_pilot/previews/{cid}",
        }
        inventory_items.append(item)

    # Save JSON
    output_json.parent.mkdir(parents=True, exist_ok=True)
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(inventory_items, f, indent=2)

    # Save Parquet
    df = pd.DataFrame(inventory_items)
    # Convert list columns to string representation for parquet compatibility
    df_parquet = df.copy()
    df_parquet["chip_dimensions"] = df_parquet["chip_dimensions"].apply(lambda x: f"{x[0]}x{x[1]}")
    df_parquet["spectral_channels"] = df_parquet["spectral_channels"].apply(lambda x: ",".join(x))
    df_parquet.to_parquet(output_parquet, index=False)

    print(f"Generated inventory with {len(inventory_items)} items.")
    print(f"JSON saved to: {output_json}")
    print(f"Parquet saved to: {output_parquet}")
    return inventory_items


if __name__ == "__main__":
    build_chip_inventory()
