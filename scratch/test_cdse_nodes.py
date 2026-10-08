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

# Check product OData details
url = f'https://catalogue.dataspace.copernicus.eu/odata/v1/Products({prod_uuid})'
r = requests.get(url, headers=headers).json()
print('Product Name:', r.get('Name'))

# Check if Nodes navigation exists
url_nodes = f'https://catalogue.dataspace.copernicus.eu/odata/v1/Products({prod_uuid})/Nodes'
r_nodes = requests.get(url_nodes, headers=headers)
print('Nodes status:', r_nodes.status_code, r_nodes.text[:200])
