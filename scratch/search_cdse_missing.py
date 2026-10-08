"""
Search CDSE OData catalog for the 5 missing candidates using geographic coordinates and defensible temporal windows.
"""

import json
import urllib.parse
import urllib.request

BASE_URL = "https://catalogue.dataspace.copernicus.eu/odata/v1/Products"

CANDIDATES = [
    {
        "chip_id": "DS08_EXP_S2_001",
        "stratum": "STR-2",
        "class": "Other Thermal Source",
        "lat": 32.76166,
        "lon": 72.62834,
        "tile": "T43TBB",
        "nominal_date": "2025-06-11",
        "date_min": "2025-06-01",
        "date_max": "2025-06-20",
    },
    {
        "chip_id": "DS08_EXP_S3_001",
        "stratum": "STR-3",
        "class": "Forest Fire",
        "lat": 30.30482,
        "lon": 74.48767,
        "tile": "T43SEM",
        "nominal_date": "2025-05-16",
        "date_min": "2025-05-10",
        "date_max": "2025-05-22",
    },
    {
        "chip_id": "DS08_EXP_S4_001",
        "stratum": "STR-4",
        "class": "Agricultural Fire",
        "lat": 30.57704,
        "lon": 76.33285,
        "tile": "T43SIN",
        "nominal_date": "2024-10-23",
        "date_min": "2024-10-18",
        "date_max": "2024-10-28",
    },
    {
        "chip_id": "DS08_EXP_S5_001",
        "stratum": "STR-5",
        "class": "NO_VISIBLE_TARGET",
        "lat": 28.38,
        "lon": 77.24,
        "tile": "T43SKI",
        "nominal_date": "2025-01-15",
        "date_min": "2025-01-10",
        "date_max": "2025-01-20",
    },
    {
        "chip_id": "DS08_EXP_S6_001",
        "stratum": "STR-6",
        "class": "NO_VISIBLE_TARGET",
        "lat": 28.25,
        "lon": 78.35,
        "tile": "T44SAI",
        "nominal_date": "2025-02-12",
        "date_min": "2025-02-05",
        "date_max": "2025-02-18",
    },
]


def query_cdse(tile, start_date, end_date):
    filter_q = (
        f"Collection/Name eq 'SENTINEL-2' and "
        f"contains(Name, 'MSIL2A') and "
        f"contains(Name, '{tile}') and "
        f"ContentDate/Start ge {start_date}T00:00:00.000Z and "
        f"ContentDate/Start le {end_date}T23:59:59.000Z"
    )
    params = {
        "$filter": filter_q,
        "$top": 20,
        "$orderby": "ContentDate/Start asc"
    }
    url = f"{BASE_URL}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=25) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        return data.get("value", [])


def main():
    results = {}
    for cand in CANDIDATES:
        cid = cand["chip_id"]
        tile = cand["tile"]
        s_date = cand["date_min"]
        e_date = cand["date_max"]
        print(f"Querying for {cid} ({cand['class']}) in tile {tile} [{s_date} to {e_date}]...")
        try:
            products = query_cdse(tile, s_date, e_date)
            print(f"  Found {len(products)} products")
            results[cid] = {
                "candidate": cand,
                "count": len(products),
                "products": [
                    {
                        "Name": p["Name"],
                        "Id": p["Id"],
                        "ContentLength": p.get("ContentLength"),
                        "ContentDate": p.get("ContentDate"),
                        "Online": p.get("Online"),
                        "OriginDate": p.get("OriginDate"),
                    }
                    for p in products
                ],
            }
            for p in products:
                print(f"    {p['Name']} (Id: {p['Id']}, Online: {p.get('Online')}, Size: {p.get('ContentLength', 0)/(1024*1024):.1f} MB)")
        except Exception as e:
            print(f"  Error: {e}")
            results[cid] = {"candidate": cand, "error": str(e)}

    with open("scratch/cdse_missing_search_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print("Done! Saved to scratch/cdse_missing_search_results.json")


if __name__ == "__main__":
    main()
