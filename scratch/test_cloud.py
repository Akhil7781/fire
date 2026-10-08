import urllib.request
import urllib.parse
import json

BASE_URL = "https://catalogue.dataspace.copernicus.eu/odata/v1/Products"

uid = "34ce33d0-75a0-4c86-b3c8-d7904711640b"
params = {
    "$filter": f"Id eq {uid}",
    "$expand": "Attributes"
}
url = f"{BASE_URL}?{urllib.parse.urlencode(params)}"
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
try:
    with urllib.request.urlopen(req, timeout=15) as resp:
        d = json.loads(resp.read().decode('utf-8'))
        val = d.get('value', [])
        if val:
            attrs = val[0].get('Attributes', [])
            print(f"Product has {len(attrs)} attributes:")
            for a in attrs:
                print(f"  {a.get('Name')}: {a.get('Value')}")
except Exception as e:
    print("Error:", e)
