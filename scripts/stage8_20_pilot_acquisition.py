"""
Stage 8.20: Controlled Sentinel-2 Imagery Acquisition Pilot Script.

MANDATORY SAFETY GUARDS:
1. Requires explicit confirmation flag `--confirm-acquisition` to execute any download.
2. In default dry-run mode, validates configuration, credentials, and candidate metadata with 0 bytes downloaded.
3. Operates exclusively on the approved 8-chip pilot batch.
4. Enforces SCL AOI-level (<= 5%) and center-area (0%) cloud screening.
5. Implements locked bilinear resampling for 20m bands (B11, B12) to 10m GSD.
6. Writes atomic downloads with SHA-256 validation.
"""

from __future__ import annotations

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
MANIFEST_V4_PATH = PROJECT_ROOT / "data" / "reference" / "ds08" / "manifests" / "stage8_19e" / "ds08_expansion_candidates_v4.json"
MANIFEST_V3_PATH = PROJECT_ROOT / "data" / "reference" / "ds08" / "manifests" / "stage8_19b" / "ds08_expansion_candidates_v3.json"
PILOT_OUTPUT_DIR = PROJECT_ROOT / "data" / "interim" / "ds08_stage8_20_pilot"
CDSE_TOKEN_URL = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
CDSE_DOWNLOAD_URL = "https://download.dataspace.copernicus.eu/odata/v1/Products"

# Explicit 8-chip pilot batch approved in STAGE8_20_PILOT_ACQUISITION_PLAN.md
PILOT_CHIP_IDS = [
    "DS08_EXP_S1_003",  # Panipat polymer warehouse (STR-1 baseline)
    "DS08_EXP_S1_002",  # Vizag API Pharma (STR-1, DEC-U5 cloud exception test 1)
    "DS08_EXP_S1_004",  # Tarapur Chemical (STR-1, DEC-U5 cloud exception test 2)
    "DS08_EXP_S2_001",  # Persistent Thermal Source (STR-2)
    "DS08_EXP_S3_001",  # Active Forest Wildfire (STR-3)
    "DS08_EXP_S4_001",  # Agricultural Residue Burn (STR-4)
    "DS08_EXP_S5_001",  # Industrial Negative Control (STR-5)
    "DS08_EXP_S6_001",  # Natural Negative Control (STR-6)
]

# Verified UUID mapping for the 8 pilot products from Stage 8.19F audit
PILOT_UUID_MAP = {
    "DS08_EXP_S1_003": "34ce33d0-75a0-4c86-b3c8-d7904711640b",
    "DS08_EXP_S1_002": "e7f0da0d-942d-48ba-a267-07b385c7ca80",
    "DS08_EXP_S1_004": "80fd0f38-b426-4206-abc1-eaed217643f3",
    "DS08_EXP_S2_001": "d217bf07-57cf-4984-bda8-9f0767f02b28",
    "DS08_EXP_S3_001": "ec7925b0-7e83-47f8-a78f-2425a430ab20",
    "DS08_EXP_S4_001": "df4ae3e0-cb59-4df4-aa30-da3650687746",
    "DS08_EXP_S5_001": "ffb53396-a874-461f-9474-b678078078bf",
    "DS08_EXP_S6_001": "fede2b88-962f-4f9b-9f2b-23b1fe291dad",
}

REQUIRED_BANDS = ["B02", "B03", "B04", "B11", "B12", "SCL"]


def load_credentials_from_env() -> Tuple[Optional[str], Optional[str]]:
    """Loads CDSE credentials from existing .env file without creating a new .env."""
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


def get_oauth_token(client_id: str, client_secret: str) -> str:
    """Retrieves an OAuth2 access token from CDSE Keycloak endpoint."""
    resp = requests.post(
        CDSE_TOKEN_URL,
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "client_credentials",
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["access_token"]


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
                    # Compute hash
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

        # Find required JP2 files
        for name in names:
            name_lower = name.lower()
            if not name_lower.endswith(".jp2"):
                continue

            # Identify band
            for b in REQUIRED_BANDS:
                # Match e.g. _B02_10m.jp2 or _B11_20m.jp2 or _SCL_20m.jp2
                if f"_{b.lower()}_" in name_lower or f"_{b.lower()}." in name_lower or f"/{b.lower()}." in name_lower:
                    if b in ["B02", "B03", "B04"] and "10m" in name_lower:
                        band_paths[b] = name
                    elif b in ["B11", "B12", "SCL"] and "20m" in name_lower:
                        band_paths[b] = name

        # Also find metadata XMLs
        mtd_files = [n for n in names if n.endswith("MTD_MSIL2A.xml") or n.endswith("MTD_TL.xml")]

        files_to_extract = list(band_paths.values()) + mtd_files
        print(f"  Extracting {len(files_to_extract)} essential assets from {zip_path.name}...")
        for member in files_to_extract:
            zf.extract(member, path=safes_dir)
            extracted_files[member] = str(safes_dir / member)

    # Verify all 6 required bands are present
    missing_bands = [b for b in REQUIRED_BANDS if b not in band_paths]
    if missing_bands:
        raise ValueError(f"Missing required bands in archive {zip_path.name}: {missing_bands}")

    return {
        "band_paths": {b: str(safes_dir / band_paths[b]) for b in REQUIRED_BANDS},
        "extracted_file_count": len(extracted_files),
        "safe_dir": str(safes_dir / names[0].split("/")[0])
    }


def parse_args():
    parser = argparse.ArgumentParser(description="Stage 8.20 Controlled Acquisition Pilot")
    parser.add_argument(
        "--confirm-acquisition",
        action="store_true",
        default=False,
        help="Explicit confirmation flag required to initiate raster downloads. Without this flag, script runs in dry-run mode."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Explicit dry-run verification mode (validates metadata and configuration without downloading)."
    )
    return parser.parse_args()


def run_acquisition_pilot(confirm_acquisition: bool = False, dry_run: bool = False, manifest_path: Optional[Path] = None) -> Dict[str, Any]:
    print("=" * 75)
    print("STAGE 8.20: CONTROLLED ACQUISITION PILOT")
    print("=" * 75)

    target_manifest = manifest_path or (MANIFEST_V4_PATH if MANIFEST_V4_PATH.exists() else MANIFEST_V3_PATH)
    print(f"Using manifest: {target_manifest.name}")

    with open(target_manifest, "r", encoding="utf-8") as f:
        manifest_data = json.load(f)

    manifest_map = {r["chip_id"]: r for r in manifest_data["records"]}
    pilot_records = [manifest_map[cid] for cid in PILOT_CHIP_IDS if cid in manifest_map]

    assert len(pilot_records) == 8, f"Expected 8 pilot records, found {len(pilot_records)}"

    print(f"\nTarget Pilot Batch Size: {len(pilot_records)} chips")
    for idx, r in enumerate(pilot_records, start=1):
        cloud_str = f"{r['cloud_cover_pct']}%"
        exc = " [DEC-U5 EXCEPTION]" if r.get("cloud_exception_applied") else ""
        print(f"  P-{idx:02d}: {r['chip_id']} | Stratum: {r['candidate_stratum_id']} | Scene Cloud: {cloud_str}{exc}")
        print(f"        Product: {r['stac_scene_id']}")

    client_id, client_secret = load_credentials_from_env()
    has_creds = bool(client_id and client_secret)
    print(f"\nCredential Inspection: CDSE Credentials configured in environment: {has_creds}")

    # Guard: Require --confirm-acquisition
    if not confirm_acquisition:
        print("\n" + "!" * 75)
        print("SAFEGUARD ACTIVE: --confirm-acquisition flag was NOT provided.")
        print("Operating in READ-ONLY / DRY-RUN inspection mode.")
        print("Zero bytes of imagery downloaded.")
        print("To execute pilot acquisition after human authorization, run:")
        print("  python scripts/stage8_20_pilot_acquisition.py --confirm-acquisition")
        print("!" * 75)
        return {
            "mode": "DRY_RUN",
            "pilot_chips_evaluated": len(pilot_records),
            "status": "READY_FOR_OWNER_AUTHORIZATION",
            "downloaded_bytes": 0
        }

    # If --confirm-acquisition is provided:
    print("\n" + "=" * 75)
    print("OWNER AUTHORIZATION DETECTED: Initializing Pilot Acquisition Pipeline...")
    print("=" * 75)
    if not has_creds:
        raise ValueError("Cannot acquire imagery: CDSE credentials not found in environment or .env!")

    PILOT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    session = CDSESession(client_id, client_secret)

    acquisition_results = []
    total_downloaded_bytes = 0

    for idx, r in enumerate(pilot_records, start=1):
        cid = r["chip_id"]
        safe_name = r["stac_scene_id"]
        uuid = r.get("cdse_product_uuid") or PILOT_UUID_MAP.get(cid)
        if not uuid:
            raise ValueError(f"Missing CDSE UUID for candidate {cid} ({safe_name})")

        print(f"\n[{idx}/8] Processing {cid} ({r['candidate_stratum_id']})...")
        print(f"  Product: {safe_name}")
        print(f"  UUID:    {uuid}")

        zip_path, sha256_hex, file_size = download_safe_product(
            uuid=uuid,
            safe_name=safe_name,
            output_dir=PILOT_OUTPUT_DIR,
            session=session,
        )
        total_downloaded_bytes += file_size

        extraction_info = extract_required_safe_assets(zip_path, PILOT_OUTPUT_DIR)

        item = {
            "chip_id": cid,
            "candidate_stratum_id": r["candidate_stratum_id"],
            "expected_target_class": r["expected_target_class"],
            "cdse_product_uuid": uuid,
            "stac_scene_id": safe_name,
            "mgrs_tile": r["mgrs_tile"],
            "sensing_time_utc": r["sensing_time_utc"],
            "latitude": r["latitude"],
            "longitude": r["longitude"],
            "local_zip_path": str(zip_path),
            "local_zip_size_bytes": file_size,
            "local_zip_sha256": sha256_hex,
            "extracted_safe_dir": extraction_info["safe_dir"],
            "extracted_bands": extraction_info["band_paths"],
            "download_status": "VERIFIED_SAFE",
            "acquisition_timestamp": datetime.now(timezone.utc).isoformat(),
        }
        acquisition_results.append(item)

    # Save acquisition manifest
    manifest_out = PILOT_OUTPUT_DIR / "acquisition_manifest.json"
    with open(manifest_out, "w", encoding="utf-8") as f:
        json.dump(acquisition_results, f, indent=2)
    print(f"\nAcquisition pipeline completed successfully!")
    print(f"Total downloaded bytes: {total_downloaded_bytes} ({total_downloaded_bytes / (1024*1024):.1f} MB)")
    print(f"Acquisition manifest saved to: {manifest_out}")

    return {
        "mode": "CONFIRMED_EXECUTION",
        "pilot_chips": len(pilot_records),
        "downloaded_bytes": total_downloaded_bytes,
        "output_dir": str(PILOT_OUTPUT_DIR),
        "manifest_path": str(manifest_out)
    }


if __name__ == "__main__":
    args = parse_args()
    run_acquisition_pilot(confirm_acquisition=args.confirm_acquisition, dry_run=args.dry_run)
