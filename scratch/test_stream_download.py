import requests
import json
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

session = requests.Session()

# Custom redirect handling to preserve auth header across dataspace.copernicus.eu subdomains
class CustomSession(requests.Session):
    def rebuild_auth(self, prepared_request, response):
        headers = prepared_request.headers
        headers['Authorization'] = f'Bearer {token}'

csession = CustomSession()
val_url = f'https://download.dataspace.copernicus.eu/odata/v1/Products({prod_uuid})/$value'
r = csession.get(val_url, headers={'Authorization': f'Bearer {token}'}, stream=True, timeout=15)
print('Status code:', r.status_code)
print('Content-Type:', r.headers.get('Content-Type'))
print('Content-Length:', r.headers.get('Content-Length'))
# Read first 100 bytes to check zip magic bytes PK\x03\x04
chunk = next(r.iter_content(chunk_size=100))
print('First 10 bytes:', chunk[:10], 'Zip magic match:', chunk[:4] == b'PK\x03\x04')
r.close()
