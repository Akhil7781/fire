import urllib.parse
import urllib.request
import json

BASE_URL = "https://catalogue.dataspace.copernicus.eu/odata/v1/Products"

q = (
    "contains(Name, 'MSIL2A') and "
    "OData.CSC.Intersects(area=geography'SRID=4326;POINT(77.24 28.38)') and "
    "ContentDate/Start ge 2024-12-01T00:00:00.000Z and "
    "ContentDate/Start le 2025-03-01T23:59:59.000Z"
)
params = {
    "$filter": q,
    "$expand": "Attributes",
    "$top": 30,
    "$orderby": "ContentDate/Start asc"
}
url = f"{BASE_URL}?{urllib.parse.urlencode(params)}"
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req, timeout=25) as resp:
    data = json.loads(resp.read().decode('utf-8'))
    products = data.get('value', [])
    print(f"Total products found for Noida SEZ (lat=28.38, lon=77.24): {len(products)}")
    for p in products:
        attrs = {a.get('Name'): a.get('Value') for a in p.get('Attributes', [])}
        cloud = attrs.get('cloudCover')
        try:
            cloud_pct = round(float(cloud), 2)
        except:
            cloud_pct = cloud
        if cloud_pct is not None and cloud_pct <= 10.0:
            print(f"  {p['Name']}")
            print(f"    Date: {p.get('ContentDate', {}).get('Start')}, Cloud: {cloud_pct}%, UUID: {p['Id']}, Size: {round(p.get('ContentLength', 0)/(1024*1024), 1)} MB, Online: {p.get('Online')}")
