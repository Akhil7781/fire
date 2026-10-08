import urllib.request
import urllib.parse
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

print('Has client_id:', bool(client_id), 'Has client_secret:', bool(client_secret))

token_url = 'https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token'
data = urllib.parse.urlencode({
    'client_id': client_id,
    'client_secret': client_secret,
    'grant_type': 'client_credentials'
}).encode('utf-8')

req = urllib.request.Request(token_url, data=data, method='POST')
try:
    with urllib.request.urlopen(req, timeout=15) as resp:
        res = json.loads(resp.read().decode('utf-8'))
        print('Token request SUCCESS! Keys:', list(res.keys()), 'Expires in:', res.get('expires_in'))
except Exception as e:
    print('Token request failed:', e)
