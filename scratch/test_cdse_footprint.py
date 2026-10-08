import urllib.request
import urllib.parse
import json

BASE_URL = 'https://catalogue.dataspace.copernicus.eu/odata/v1/Products'
prod_name = 'S2B_MSIL2A_20250608T054639_N0511_R048_T43SBS_20250608T074909.SAFE'
params = {
    '$filter': f"Name eq '{prod_name}'",
    '$expand': 'Attributes'
}
url = f"{BASE_URL}?{urllib.parse.urlencode(params)}"
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req, timeout=20) as resp:
    data = json.loads(resp.read().decode('utf-8'))
val = data.get('value', [])
if val:
    p = val[0]
    print('Product keys:', list(p.keys()))
    print('Footprint:', p.get('Footprint'))
    print('GeoFootprint:', p.get('GeoFootprint'))
