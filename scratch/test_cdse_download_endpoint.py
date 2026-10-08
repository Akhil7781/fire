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

token_url = 'https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token'
data = urllib.parse.urlencode({
    'client_id': client_id,
    'client_secret': client_secret,
    'grant_type': 'client_credentials'
}).encode('utf-8')

req = urllib.request.Request(token_url, data=data, method='POST')
with urllib.request.urlopen(req, timeout=15) as resp:
    token = json.loads(resp.read().decode('utf-8'))['access_token']

prod_uuid = '34ce33d0-75a0-4c86-b3c8-d7904711640b'

# Check Nodes
nodes_url = f'https://catalogue.dataspace.copernicus.eu/odata/v1/Products({prod_uuid})/Nodes'
req_nodes = urllib.request.Request(nodes_url, headers={'Authorization': f'Bearer {token}'})
try:
    with urllib.request.urlopen(req_nodes, timeout=15) as resp:
        nodes = json.loads(resp.read().decode('utf-8'))
        print('Nodes returned:', [n.get('Name') for n in nodes.get('value', [])])
except Exception as e:
    print('Nodes query error:', e)

# Test HEAD or range on $value
val_url = f'https://catalogue.dataspace.copernicus.eu/odata/v1/Products({prod_uuid})/$value'
class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        print(f'Redirected to: {newurl[:50]}... code: {code}')
        return None

opener = urllib.request.build_opener(NoRedirectHandler)
req_val = urllib.request.Request(val_url, headers={'Authorization': f'Bearer {token}'})
try:
    with opener.open(req_val, timeout=15) as resp:
        print('Val status:', resp.status, 'Headers:', dict(resp.headers))
except Exception as e:
    print('Val request (expected redirect or response):', e)
