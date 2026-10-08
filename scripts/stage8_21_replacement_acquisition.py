"""
Stage 8.21 Replacement Acquisition Pipeline
Acquires real Sentinel-2 Level-2A products from Copernicus Data Space Ecosystem (CDSE)
for the approved replacement cohort (S8_001, S8_002) replacing rejected scenes S1_002 and S1_004.
Requires explicit authorization flag: --confirm-acquisition.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import time
from typing import Any, Dict, List, Optional, Tuple
import zipfile

import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPLACEMENT_MANIFEST_PATH = PROJECT_ROOT / "data" / "reference" / "ds08" / "manifests" / "stage8_21" / "ds08_stage8_21_replacement_manifest.json"
OUTPUT_DIR = PROJECT_ROOT / "data" / "interim" / "ds08_stage8_21_replacements"

CDSE_TOKEN_URL = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
CDSE_DOWNLOAD_URL = "https://download.dataspace.copernicus.eu/odata/v1/Products"

REQUIRED_BANDS = ["B02", "B03", "B04", "B11", "B12", "SCL"]


def load_credentials_from_env() -> Tuple[Optional[str], Optional[str]]:
    """Loads CDSE credentials from existing .env file."""
    env_file = PROJECT_ROOT / ".env"
    client_id = os.environ.get("CDSE_CLIENT_ID")
    client_secret = os.environ.get("CDSE_CLIENT_SECRET")

    if not client_id or not client_secret:
        if env_file.exists():
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("CDSE_CLIENT_ID="):
                        client_id = line.split("=", 1)[1].strip().strip('"').strip("'")
                    elif line.startswith("CDSE_CLIENT_SECRET="):
                        client_secret = line.split("=", 1)[1].strip().strip('"').strip("'")

    return client_id, client_secret


class CDSESession(requests.Session):
    """Custom Session that retains Authorization header and auto-refreshes token."""

    def __init__(self, client_id: str, client_secret: str):
        super().__init__()
        self.client_id = client_id
        self.client_secret = client_secret
        self.token = ""
        self.token_expires_at = 0.0
        self.refresh_token()

    def refresh_token(self):
        resp = requests.post(
            CDSE_TOKEN_URL,
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "client_credentials",
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        self.token = data["access_token"]
        expires_in = data.get("expires_in", 1800)
        self.token_expires_at = time.time() + expires_in

    def request(self, method, url, *args, **kwargs):
        if time.time() >= self.token_expires_at - 60:
            self.refresh_token()
        headers = kwargs.get("headers", {})
        headers["Authorization"] = f"Bearer {self.token}"
        kwargs["headers"] = headers
        return super().request(method, url, *args, **kwargs)

    def rebuild_auth(self, prepared_request, response):
        if time.time() >= self.token_expires_at - 60:
            self.refresh_token()
        prepared_request.headers["Authorization"] = f"Bearer {self.token}"


def download_safe_product(
    uuid: str,
    safe_name: str,
    output_dir: Path,
    session: CDSESession,
) -> Tuple[Path, str, int]:
    """Downloads a product SAFE archive atomically, verifying bytes and SHA-256."""
    zips_dir = output_dir / "zips"
    zips_dir.mkdir(parents=True, exist_ok=True)

    zip_path = zips_dir / f"{safe_name}.zip"
    part_path = zips_dir / f"{safe_name}.zip.part"

    # If full zip already exists and is valid, reuse it
    if zip_path.exists():
        try:
            print(f"  Existing archive found: {zip_path.name}. Verifying integrity...")
            with zipfile.ZipFile(zip_path, "r") as zf:
                bad_file = zf.testzip()
                if bad_file is None:
                    hasher = hashlib.sha256()
                    size = zip_path.stat().st_size
                    with open(zip_path, "rb") as f:
                        for chunk in iter(lambda: f.read(4 * 1024 * 1024), b""):
                            hasher.update(chunk)
                    print(f"  Archive verified valid! ({size / (1024*1024):.1f} MB, SHA-256: {hasher.hexdigest()[:16]}...)")
                    return zip_path, hasher.hexdigest(), size
        except Exception as e:
            print(f"  Existing archive corrupted ({e}). Re-downloading...")
            zip_path.unlink(missing_ok=True)

    val_url = f"{CDSE_DOWNLOAD_URL}({uuid})/$value"
    headers = {"Authorization": f"Bearer {session.token}"}

    print(f"  Streaming download from CDSE: {safe_name} (UUID: {uuid})...")
    resp = session.get(val_url, headers=headers, stream=True, timeout=60)
    resp.raise_for_status()

    expected_size = int(resp.headers.get("Content-Length", 0))
    print(f"  Remote Content-Length: {expected_size / (1024*1024):.1f} MB")

    hasher = hashlib.sha256()
    bytes_downloaded = 0
    t0 = time.time()
    last_print = t0

    with open(part_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=4 * 1024 * 1024):
            if chunk:
                f.write(chunk)
                hasher.update(chunk)
                bytes_downloaded += len(chunk)
                now = time.time()
                if now - last_print > 5.0:
                    pct = (bytes_downloaded / expected_size * 100) if expected_size > 0 else 0
                    speed = (bytes_downloaded / (1024 * 1024)) / (now - t0)
                    print(f"    Downloaded: {bytes_downloaded / (1024*1024):.1f} MB ({pct:.1f}%) at {speed:.2f} MB/s...")
                    last_print = now

    t1 = time.time()
    speed_final = (bytes_downloaded / (1024 * 1024)) / max(t1 - t0, 0.001)
    print(f"  Download complete: {bytes_downloaded / (1024*1024):.1f} MB in {t1 - t0:.1f} s ({speed_final:.2f} MB/s)")

    if expected_size > 0 and bytes_downloaded != expected_size:
        part_path.unlink(missing_ok=True)
        raise IOError(f"Incomplete download: got {bytes_downloaded} bytes, expected {expected_size}")

    # Atomic rename
    part_path.rename(zip_path)
    sha256_hex = hasher.hexdigest()

    # Validate zip integrity
    with zipfile.ZipFile(zip_path, "r") as zf:
        bad_file = zf.testzip()
        if bad_file is not None:
            zip_path.unlink(missing_ok=True)
            raise IOError(f"Corrupted zip archive: first corrupted file {bad_file}")

    return zip_path, sha256_hex, bytes_downloaded


def extract_required_safe_assets(zip_path: Path, output_dir: Path) -> Dict[str, Any]:
    """Extracts required JP2 bands and metadata from SAFE zip."""
    safes_dir = output_dir / "safes"
    safes_dir.mkdir(parents=True, exist_ok=True)

    extracted_files = {}
    band_paths = {}

    with zipfile.ZipFile(zip_path, "r") as zf:
        names = zf.namelist()

        for name in names:
            name_lower = name.lower()
            if not name_lower.endswith(".jp2"):
                continue

            for b in REQUIRED_BANDS:
                if f"_{b.lower()}_" in name_lower or f"_{b.lower()}." in name_lower or f"/{b.lower()}." in name_lower:
                    if b in ["B02", "B03", "B04"] and "10m" in name_lower:
                        band_paths[b] = name
                    elif b in ["B11", "B12", "SCL"] and "20m" in name_lower:
                        band_paths[b] = name

        mtd_files = [n for n in names if n.endswith("MTD_MSIL2A.xml") or n.endswith("MTD_TL.xml")]
        files_to_extract = list(band_paths.values()) + mtd_files
        print(f"  Extracting {len(files_to_extract)} essential assets from {zip_path.name}...")
        for member in files_to_extract:
            zf.extract(member, path=safes_dir)
            extracted_files[member] = str(safes_dir / member)

    missing_bands = [b for b in REQUIRED_BANDS if b not in band_paths]
    if missing_bands:
        raise ValueError(f"Missing required bands in archive {zip_path.name}: {missing_bands}")

    return {
        "band_paths": {b: str(safes_dir / band_paths[b]) for b in REQUIRED_BANDS},
        "extracted_file_count": len(extracted_files),
        "safe_dir": str(safes_dir / names[0].split("/")[0])
    }


def run_replacement_acquisition(confirm_acquisition: bool = False, dry_run: bool = False) -> Dict[str, Any]:
    print("=" * 75)
    print("STAGE 8.21: REPLACEMENT COHORT ACQUISITION")
    print("=" * 75)

    with open(REPLACEMENT_MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest_data = json.load(f)

    replacement_records = manifest_data["replacement_records"]
    print(f"Replacement batch size: {len(replacement_records)} chips")
    for r in replacement_records:
        print(f"  {r['replacement_sample_id']} (replaces {r['replaces_sample_id']}): {r['facility_name']}")
        print(f"    Product: {r['stac_scene_id']} | UUID: {r['cdse_product_uuid']}")

    client_id, client_secret = load_credentials_from_env()
    has_creds = bool(client_id and client_secret)
    print(f"\nCredential Inspection: CDSE Credentials configured: {has_creds}")

    if not confirm_acquisition or dry_run:
        print("\n[SAFETY GATE ACTIVE] --confirm-acquisition not provided (or --dry-run set).")
        print("Dry run completed. No imagery downloaded.")
        return {
            "mode": "DRY_RUN",
            "replacement_chips_evaluated": len(replacement_records),
            "status": "READY_FOR_OWNER_AUTHORIZATION",
            "downloaded_bytes": 0
        }

    print("\n" + "=" * 75)
    print("OWNER AUTHORIZATION DETECTED: Initializing Replacement Acquisition Pipeline...")
    print("=" * 75)
    if not has_creds:
        raise ValueError("Cannot acquire imagery: CDSE credentials not found in environment or .env!")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    session = CDSESession(client_id, client_secret)

    acquisition_results = []
    total_downloaded_bytes = 0

    for idx, r in enumerate(replacement_records, start=1):
        sample_id = r["replacement_sample_id"]
        safe_name = r["stac_scene_id"]
        uuid = r["cdse_product_uuid"]

        print(f"\n[{idx}/{len(replacement_records)}] Processing {sample_id} (replaces {r['replaces_sample_id']})...")
        print(f"  Product: {safe_name}")
        print(f"  UUID:    {uuid}")

        zip_path, sha256_hex, file_size = download_safe_product(
            uuid=uuid,
            safe_name=safe_name,
            output_dir=OUTPUT_DIR,
            session=session,
        )
        total_downloaded_bytes += file_size

        extraction_info = extract_required_safe_assets(zip_path, OUTPUT_DIR)

        item = {
            "replacement_sample_id": sample_id,
            "replaces_sample_id": r["replaces_sample_id"],
            "v4_candidate_id": r["v4_candidate_id"],
            "candidate_stratum_id": r["candidate_stratum_id"],
            "expected_target_class": r["expected_target_class"],
            "facility_name": r["facility_name"],
            "cdse_product_uuid": uuid,
            "stac_scene_id": safe_name,
            "mgrs_tile": r["mgrs_tile"],
            "sensing_time_utc": r["sensing_time_utc"],
            "latitude": r["latitude"],
            "longitude": r["longitude"],
            "local_zip_path": str(zip_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "local_zip_size_bytes": file_size,
            "local_zip_sha256": sha256_hex,
            "extracted_safe_dir": extraction_info["safe_dir"],
            "extracted_bands": extraction_info["band_paths"],
            "download_status": "VERIFIED_SAFE",
            "acquisition_timestamp": datetime.now(timezone.utc).isoformat(),
        }
        acquisition_results.append(item)

    acq_manifest_path = OUTPUT_DIR / "acquisition_manifest.json"
    with open(acq_manifest_path, "w", encoding="utf-8") as f:
        json.dump(acquisition_results, f, indent=2)

    print("\nReplacement acquisition pipeline completed successfully!")
    print(f"Total downloaded bytes: {total_downloaded_bytes} ({total_downloaded_bytes / (1024*1024):.1f} MB)")
    print(f"Acquisition manifest saved to: {acq_manifest_path}")

    return {
        "mode": "CONFIRMED_ACQUISITION",
        "total_products": len(acquisition_results),
        "total_downloaded_bytes": total_downloaded_bytes,
        "products": acquisition_results,
    }


def main():
    parser = argparse.ArgumentParser(description="Stage 8.21 Replacement Acquisition")
    parser.add_argument("--confirm-acquisition", action="store_true", default=False, help="Confirm acquisition flag")
    parser.add_argument("--dry-run", action="store_true", default=False, help="Dry run flag")
    args = parser.parse_args()

    run_replacement_acquisition(confirm_acquisition=args.confirm_acquisition, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
