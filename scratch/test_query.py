import urllib.parse
import urllib.request
import json

BASE_URL = "https://catalogue.dataspace.copernicus.eu/odata/v1/Products"

CANDIDATES = [
    {
        "chip_id": "DS08_EXP_S2_001",
        "lat": 32.76166,
        "lon": 72.62834,
        "date_start": "2025-06-01",
        "date_end": "2025-06-25",
    },
    {
        "chip_id": "DS08_EXP_S3_001",
        "lat": 30.30482,
        "lon": 74.48767,
        "date_start": "2025-05-10",
        "date_end": "2025-05-25",
    },
    {
        "chip_id": "DS08_EXP_S4_001",
        "lat": 30.57704,
        "lon": 76.33285,
        "date_start": "2024-10-15",
        "date_end": "2024-10-31",
    },
    {
        "chip_id": "DS08_EXP_S5_001",
        "lat": 28.38,
        "lon": 77.24,
        "date_start": "2025-01-05",
        "date_end": "2025-01-25",
    },
    {
        "chip_id": "DS08_EXP_S6_001",
        "lat": 28.25,
        "lon": 78.35,
        "date_start": "2025-02-05",
        "date_end": "2025-02-25",
    },
]

for cand in CANDIDATES:
    lat = cand['lat']
    lon = cand['lon']
    ds = cand['date_start']
    de = cand['date_end']
    cid = cand['chip_id']
    
    # OData spatial intersection query
    q = (
        f"contains(Name, 'MSIL2A') and "
        f"OData.CSC.Intersects(area=geography'SRID=4326;POINT({lon} {lat})') and "
        f"ContentDate/Start ge {ds}T00:00:00.000Z and "
        f"ContentDate/Start le {de}T23:59:59.000Z"
    )
    url = f"{BASE_URL}?$filter={urllib.parse.quote(q)}&$top=5&$orderby={urllib.parse.quote('ContentDate/Start asc')}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            val = data.get('value', [])
            print(f"Candidate {cid} (lat={lat}, lon={lon}): Found {len(val)} products")
            for p in val:
                print("  Name:", p['Name'])
                print("  UUID:", p['Id'])
                print("  Date:", p.get('ContentDate', {}).get('Start'))
                print("  Online:", p.get('Online'))
                print("  Size MB:", round(p.get('ContentLength', 0) / (1024*1024), 1))
    except Exception as e:
        print(f"Candidate {cid} error:", e)
