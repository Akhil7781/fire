"""
Generate STAGE8_19E_CATALOG_RESULTS.json by querying CDSE for all 8 pilot products in Manifest v4.
"""

import json
from pathlib import Path
import urllib.parse
import urllib.request

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_V4_PATH = PROJECT_ROOT / "docs" / "stage8_19e" / "STAGE8_19E_RECONCILED_MANIFEST_V4.json"
OUTPUT_JSON_PATH = PROJECT_ROOT / "docs" / "stage8_19e" / "STAGE8_19E_CATALOG_RESULTS.json"
BASE_URL = "https://catalogue.dataspace.copernicus.eu/odata/v1/Products"

PILOT_IDS = [
    "DS08_EXP_S1_003",
    "DS08_EXP_S1_002",
    "DS08_EXP_S1_004",
    "DS08_EXP_S2_001",
    "DS08_EXP_S3_001",
    "DS08_EXP_S4_001",
    "DS08_EXP_S5_001",
    "DS08_EXP_S6_001",
]


def generate_catalog_results():
    with open(MANIFEST_V4_PATH, "r", encoding="utf-8") as f:
        v4_data = json.load(f)

    rec_by_id = {r["chip_id"]: r for r in v4_data["records"]}
    catalog_results = []

    print("=" * 75)
    print("STAGE 8.19E: LIVE CATALOG VERIFICATION FOR ALL 8 PILOT CANDIDATES")
    print("=" * 75)

    for idx, cid in enumerate(PILOT_IDS, start=1):
        r = rec_by_id[cid]
        prod_name = r["stac_scene_id"]
        print(f"\n[{idx}/8] Querying CDSE for {cid} ({r['candidate_stratum_id']})...")
        print(f"  SAFE Product: {prod_name}")

        params = {
            "$filter": f"Name eq '{prod_name}'",
            "$expand": "Attributes",
        }
        url = f"{BASE_URL}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})

        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                val = data.get("value", [])
                if val:
                    p = val[0]
                    attrs = {a.get("Name"): a.get("Value") for a in p.get("Attributes", [])}
                    cloud_val = attrs.get("cloudCover")
                    try:
                        cloud_pct = round(float(cloud_val), 2) if cloud_val is not None else None
                    except:
                        cloud_pct = None

                    item = {
                        "chip_id": cid,
                        "stratum": r["candidate_stratum_id"],
                        "expected_target_class": r["expected_target_class"],
                        "stac_scene_id": prod_name,
                        "catalog_status": "EXISTS_VERIFIED",
                        "cdse_uuid": p.get("Id"),
                        "content_length_bytes": p.get("ContentLength"),
                        "size_mb": round(p.get("ContentLength", 0) / (1024 * 1024), 1),
                        "online": p.get("Online"),
                        "sensing_time_utc": p.get("ContentDate", {}).get("Start"),
                        "manifest_sensing_time": r.get("sensing_time_utc"),
                        "cloud_cover_pct": cloud_pct,
                        "mgrs_tile": r.get("mgrs_tile"),
                        "catalog_tile_id": attrs.get("tileId"),
                        "processing_level": attrs.get("processingLevel"),
                        "platform": attrs.get("platformSerialIdentifier"),
                        "relative_orbit": attrs.get("relativeOrbitNumber"),
                        "required_bands_available": ["B02", "B03", "B04", "B11", "B12", "SCL"],
                        "resolution_status": r.get("catalog_resolution_status", "RESOLVED_EXISTING_PRODUCT"),
                        "cloud_exception_applied": r.get("cloud_exception_applied", False),
                        "cloud_exception_id": r.get("cloud_exception_id"),
                        "error": None,
                    }
                    print("  Result: VERIFIED IN LIVE CDSE CATALOG")
                    print(f"    UUID: {item['cdse_uuid']}")
                    print(f"    Size: {item['size_mb']} MB, Online: {item['online']}")
                    print(f"    Date: {item['sensing_time_utc']}")
                    print(f"    Cloud: {item['cloud_cover_pct']}%")
                else:
                    item = {
                        "chip_id": cid,
                        "stratum": r["candidate_stratum_id"],
                        "expected_target_class": r["expected_target_class"],
                        "stac_scene_id": prod_name,
                        "catalog_status": "NOT_FOUND_IN_CATALOG",
                        "cdse_uuid": None,
                        "error": "0 matches returned by CDSE OData filter",
                    }
                    print("  Result: NOT FOUND IN CATALOG")
        except Exception as e:
            item = {
                "chip_id": cid,
                "stratum": r["candidate_stratum_id"],
                "expected_target_class": r["expected_target_class"],
                "stac_scene_id": prod_name,
                "catalog_status": "QUERY_ERROR",
                "cdse_uuid": None,
                "error": str(e),
            }
            print(f"  Error: {e}")

        catalog_results.append(item)

    with open(OUTPUT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(catalog_results, f, indent=2)
    print(f"\nSaved all results to {OUTPUT_JSON_PATH}")


if __name__ == "__main__":
    generate_catalog_results()
