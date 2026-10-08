import requests
from pathlib import Path

env_file = Path('.env')
client_id = None
client_secret = None
if env_file.exists():
    with open(env_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line.startswith('CDSE_CLIENT_ID='):
                client_id = line.split('=', 1)[1].strip().strip('"').strip("'")
            elif line.startswith('CDSE_CLIENT_SECRET='):
                client_secret = line.split('=', 1)[1].strip().strip('"').strip("'")

token_url = 'https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token'
resp = requests.post(token_url, data={
    'client_id': client_id,
    'client_secret': client_secret,
    'grant_type': 'client_credentials'
}, timeout=15)
token = resp.json()['access_token']

prod_uuid = '34ce33d0-75a0-4c86-b3c8-d7904711640b'
headers = {'Authorization': f'Bearer {token}'}

safe_name = 'S2B_MSIL2A_20250413T052649_N0511_R105_T43RFN_20250413T074009.SAFE'
url_sub = f"https://download.dataspace.copernicus.eu/odata/v1/Products({prod_uuid})/Nodes('{safe_name}')/Nodes"
r_sub = requests.get(url_sub, headers=headers)
print('Sub-nodes status:', r_sub.status_code)
if r_sub.status_code == 200:
    items = r_sub.json().get('result', [])
    print('Sub-nodes:', [it.get('Name') for it in items])
    # Let's check GRANULE
    granule_node = next((it for it in items if it.get('Name') == 'GRANULE'), None)
    if granule_node:
        print('Found GRANULE node:', granule_node)
        url_granule = f"https://download.dataspace.copernicus.eu/odata/v1/Products({prod_uuid})/Nodes('{safe_name}')/Nodes('GRANULE')/Nodes"
        r_g = requests.get(url_granule, headers=headers).json()
        g_name = r_g.get('result', [])[0].get('Name')
        print('Granule name:', g_name)
        url_img = f"https://download.dataspace.copernicus.eu/odata/v1/Products({prod_uuid})/Nodes('{safe_name}')/Nodes('GRANULE')/Nodes('{g_name}')/Nodes('IMG_DATA')/Nodes"
        r_img = requests.get(url_img, headers=headers).json()
        print('IMG_DATA sub-nodes:', [x.get('Name') for x in r_img.get('result', [])])
