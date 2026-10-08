import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import requests
from src.utils.config import get_firms_map_key

root=Path(__file__).resolve().parents[1]
m=json.loads((root/'artifacts/stage8_45/fullyear_acquisition_manifest.json').read_text())
failed=next(x for x in m['requests'] if x['http_result'] != 200)
key=get_firms_map_key()
bbox=','.join(f'{v:.5f}' for v in failed['aoi_bbox_wsen'])
days=(__import__('datetime').date.fromisoformat(failed['date_end'])-__import__('datetime').date.fromisoformat(failed['date_start'])).days+1
url=f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{key}/VIIRS_NOAA20_SP/{bbox}/{days}/{failed['date_start']}"
r=requests.get(url,timeout=45)
body=r.text.replace(key,'[REDACTED]')[:800]
print(json.dumps({'sample_candidate':failed['candidate_id'],'sample_start':failed['date_start'],'sample_end':failed['date_end'],'http':r.status_code,'body':body},indent=2))
