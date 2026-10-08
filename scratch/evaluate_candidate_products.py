import urllib.parse
import urllib.request
import json

BASE_URL = "https://catalogue.dataspace.copernicus.eu/odata/v1/Products"

CANDIDATES = [
    {
        "chip_id": "DS08_EXP_S2_001",
        "lat": 32.76166,
        "lon": 72.62834,
        "target_date": "2025-06-11",
        "date_start": "2025-05-25",
        "date_end": "2025-06-25",
        "stratum": "STR-2",
        "class": "Other Thermal Source"
    },
    {
        "chip_id": "DS08_EXP_S3_001",
        "lat": 30.30482,
        "lon": 74.48767,
        "target_date": "2025-05-16",
        "date_start": "2025-05-10",
        "date_end": "2025-05-22",
        "stratum": "STR-3",
        "class": "Forest Fire"
    },
    {
        "chip_id": "DS08_EXP_S4_001",
        "lat": 30.57704,
        "lon": 76.33285,
        "target_date": "2024-10-23",
        "date_start": "2024-10-15",
        "date_end": "2024-10-31",
        "stratum": "STR-4",
        "class": "Agricultural Fire"
    },
    {
        "chip_id": "DS08_EXP_S5_001",
        "lat": 28.38,
        "lon": 77.24,
        "target_date": "2025-01-15",
        "date_start": "2025-01-05",
        "date_end": "2025-01-25",
        "stratum": "STR-5",
        "class": "NO_VISIBLE_TARGET"
    },
    {
        "chip_id": "DS08_EXP_S6_001",
        "lat": 28.25,
        "lon": 78.35,
        "target_date": "2025-02-12",
        "date_start": "2025-02-05",
        "date_end": "2025-02-25",
        "stratum": "STR-6",
        "class": "NO_VISIBLE_TARGET"
    }
]

evaluated_results = {}

for cand in CANDIDATES:
    cid = cand['chip_id']
    lat, lon = cand['lat'], cand['lon']
    ds, de = cand['date_start'], cand['date_end']
    
    filter_q = (
        f"contains(Name, 'MSIL2A') and "
        f"OData.CSC.Intersects(area=geography'SRID=4326;POINT({lon} {lat})') and "
        f"ContentDate/Start ge {ds}T00:00:00.000Z and "
        f"ContentDate/Start le {de}T23:59:59.000Z"
    )
    params = {
        "$filter": filter_q,
        "$expand": "Attributes",
        "$top": 15,
        "$orderby": "ContentDate/Start asc"
    }
    url = f"{BASE_URL}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    print(f"\nQuerying CDSE for {cid} ({cand['class']}) [{ds} to {de}]...")
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            products = data.get('value', [])
            print(f"  Found {len(products)} products")
            cand_prods = []
            for p in products:
                attrs = {a.get('Name'): a.get('Value') for a in p.get('Attributes', [])}
                cloud = attrs.get('cloudCover')
                try:
                    cloud_pct = round(float(cloud), 2) if cloud is not None else None
                except:
                    cloud_pct = None
                prod_info = {
                    "Name": p['Name'],
                    "Id": p['Id'],
                    "ContentLength": p.get('ContentLength'),
                    "Online": p.get('Online'),
                    "Start": p.get('ContentDate', {}).get('Start'),
                    "cloud_cover_pct": cloud_pct,
                    "tileId": attrs.get('tileId'),
                    "processingLevel": attrs.get('processingLevel'),
                    "platform": attrs.get('platformSerialIdentifier'),
                    "relativeOrbit": attrs.get('relativeOrbitNumber')
                }
                cand_prods.append(prod_info)
                print(f"    {p['Name']}")
                print(f"      UUID: {p['Id']}, Date: {prod_info['Start']}, Cloud: {cloud_pct}%, Online: {prod_info['Online']}, Size: {round(prod_info['ContentLength']/(1024*1024), 1)} MB")
            evaluated_results[cid] = {
                "candidate": cand,
                "products": cand_prods
            }
    except Exception as e:
        print(f"  Error querying {cid}: {e}")

with open("scratch/evaluated_cdse_products.json", "w", encoding="utf-8") as f:
    json.dump(evaluated_results, f, indent=2)

print("\nFinished evaluation. Saved to scratch/evaluated_cdse_products.json")
