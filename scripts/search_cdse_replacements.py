import json
import requests

v4 = json.load(open("data/reference/ds08/manifests/stage8_19e/ds08_expansion_candidates_v4.json", "r", encoding="utf-8"))
s1_candidates = [x for x in v4["records"] if x.get("candidate_stratum_id") == "STR-1"]

print(f"Total STR-1 candidates: {len(s1_candidates)}")

for r in s1_candidates:
    cid = r["chip_id"]
    tile = r["mgrs_tile"]
    date_str = r["sensing_time_utc"][:10].replace("-", "")
    scene = r["stac_scene_id"]
    clean_name = scene.replace(".SAFE", "")
    
    # Try exact match with .SAFE and without .SAFE
    url1 = f"https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Name eq '{scene}'"
    res1 = requests.get(url1)
    items1 = res1.json().get("value", []) if res1.status_code == 200 else []
    
    if items1:
        print(f"[{cid}] EXACT MATCH with .SAFE: {items1[0]['Id']} | {items1[0]['Name']} | {items1[0].get('ContentLength')}")
        continue
        
    url2 = f"https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Name eq '{clean_name}'"
    res2 = requests.get(url2)
    items2 = res2.json().get("value", []) if res2.status_code == 200 else []
    
    if items2:
        print(f"[{cid}] EXACT MATCH without .SAFE: {items2[0]['Id']} | {items2[0]['Name']} | {items2[0].get('ContentLength')}")
        continue
        
    # Search by tile and date
    url3 = f"https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=contains(Name,'{tile}') and contains(Name,'{date_str}') and contains(Name,'MSIL2A')"
    res3 = requests.get(url3)
    items3 = res3.json().get("value", []) if res3.status_code == 200 else []
    print(f"[{cid}] Tile+Date search found {len(items3)} products:")
    for it in items3[:3]:
        print(f"   -> {it['Id']} | {it['Name']} | {it.get('ContentLength')}")
