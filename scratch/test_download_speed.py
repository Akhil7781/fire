import requests
import time
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

class CustomSession(requests.Session):
    def rebuild_auth(self, prepared_request, response):
        headers = prepared_request.headers
        headers['Authorization'] = f'Bearer {token}'

csession = CustomSession()
val_url = f'https://download.dataspace.copernicus.eu/odata/v1/Products({prod_uuid})/$value'

t0 = time.time()
r = csession.get(val_url, headers={'Authorization': f'Bearer {token}'}, stream=True, timeout=15)
bytes_read = 0
target = 5 * 1024 * 1024  # 5 MB
for chunk in r.iter_content(chunk_size=1024*1024):
    bytes_read += len(chunk)
    if bytes_read >= target:
        break
t1 = time.time()
r.close()
speed_mb = (bytes_read / (1024*1024)) / (t1 - t0)
print(f'Read {bytes_read / (1024*1024):.1f} MB in {t1 - t0:.2f} s ({speed_mb:.2f} MB/s)')
