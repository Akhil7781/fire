import requests

print("Testing CDSE Collections endpoint...")
try:
    resp = requests.get("https://catalogue.dataspace.copernicus.eu/stac/collections", timeout=10)
    print("STAC Collections status:", resp.status_code)
    colls = resp.json().get("collections", [])
    print("Collection IDs:", [c["id"] for c in colls])
except Exception as e:
    print("STAC Collections Error:", e)

print("\nTesting CDSE OData endpoint for product...")
sample_name = "S2B_MSIL2A_20250413T052649_N0511_R105_T43RFN_20250413T074009.SAFE"
try:
    url = f"https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Name eq '{sample_name}'"
    resp = requests.get(url, timeout=10)
    print("OData query status:", resp.status_code)
    val = resp.json().get("value", [])
    print("OData match count:", len(val))
    if val:
        print("Product ID:", val[0].get("Id"))
        print("Product Name:", val[0].get("Name"))
        print("ContentLength:", val[0].get("ContentLength"))
        print("OriginDate:", val[0].get("OriginDate"))
except Exception as e:
    print("OData Error:", e)
