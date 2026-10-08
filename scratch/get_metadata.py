import urllib.request
import re

url = 'https://catalogue.dataspace.copernicus.eu/odata/v1/$metadata'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req, timeout=15) as resp:
    meta = resp.read().decode('utf-8')
    match = re.search(r'<EntityType Name="Product".*?</EntityType>', meta, re.DOTALL)
    if match:
        print(match.group(0)[:2000])
