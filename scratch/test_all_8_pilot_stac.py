import json
import time
import requests

with open("data/reference/ds08/manifests/stage8_19b/ds08_expansion_candidates_v3.json", "r", encoding="utf-8") as f:
    manifest = json.load(f)

pilot_ids = [
    "DS08_EXP_S1_003",
    "DS08_EXP_S1_002",
    "DS08_EXP_S1_004",
    "DS08_EXP_S2_001",
    "DS08_EXP_S3_001",
    "DS08_EXP_S4_001",
    "DS08_EXP_S5_001",
    "DS08_EXP_S6_001"
]

manifest_chips = {r["chip_id"]: r for r in manifest["records"]}

results = []
print("=" * 75)
print("LIVE READ-ONLY CDSE CATALOG VERIFICATION (METADATA ONLY — 0 BYTES DOWNLOADED)")
print("=" * 75)

for idx, cid in enumerate(pilot_ids, 1):
    r = manifest_chips[cid]
    prod_name = r["stac_scene_id"]
    print(f"\n[{idx}/8] Verifying {cid} ({r['candidate_stratum_id']})...")
    print(f"  Target Product: {prod_name}")
    
    url = f"https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Name eq '{prod_name}'"
    try:
        resp = requests.get(url, timeout=15)
        if resp.status_code == 200:
            val = resp.json().get("value", [])
            if len(val) > 0:
                p = val[0]
                res_item = {
                    "chip_id": cid,
                    "stratum": r["candidate_stratum_id"],
                    "product_name": prod_name,
                    "catalog_status": "EXISTS_VERIFIED",
                    "cdse_uuid": p.get("Id"),
                    "content_length_bytes": p.get("ContentLength"),
                    "origin_date": p.get("OriginDate"),
                    "manifest_match": True,
                    "error": None
                }
                print(f"  Result: VERIFIED IN LIVE CATALOG")
                print(f"    UUID: {p.get('Id')}")
                print(f"    Size: {p.get('ContentLength')} bytes (~{p.get('ContentLength', 0)/(1024*1024):.1f} MB)")
                print(f"    OriginDate: {p.get('OriginDate')}")
            else:
                res_item = {
                    "chip_id": cid,
                    "stratum": r["candidate_stratum_id"],
                    "product_name": prod_name,
                    "catalog_status": "NOT_FOUND_IN_CATALOG",
                    "cdse_uuid": None,
                    "content_length_bytes": None,
                    "origin_date": None,
                    "manifest_match": False,
                    "error": "0 matches returned by CDSE OData filter"
                }
                print("  Result: NOT FOUND IN LIVE CATALOG (0 matches)")
        else:
            res_item = {
                "chip_id": cid,
                "stratum": r["candidate_stratum_id"],
                "product_name": prod_name,
                "catalog_status": f"HTTP_ERROR_{resp.status_code}",
                "error": resp.text[:200]
            }
            print(f"  Result: HTTP ERROR {resp.status_code}")
    except Exception as e:
        res_item = {
            "chip_id": cid,
            "stratum": r["candidate_stratum_id"],
            "product_name": prod_name,
            "catalog_status": "NETWORK_TIMEOUT_OR_ERROR",
            "error": str(e)
        }
        print(f"  Result: NETWORK ERROR: {e}")
        
    results.append(res_item)
    # Enforce 2.0s polite delay between requests (DEC-U3)
    time.sleep(2.0)

print("\n" + "=" * 75)
print("LIVE STAC CATALOG AUDIT SUMMARY:")
verified_count = sum(1 for x in results if x.get("catalog_status") == "EXISTS_VERIFIED")
print(f"  Total Verified in Live Catalog: {verified_count} / {len(pilot_ids)}")
print("=" * 75)

with open("scratch/live_stac_pilot_results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2)
