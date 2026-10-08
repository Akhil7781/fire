"""
CDSE Sentinel Hub OAuth Credentials Test Script.

Tests whether Copernicus Data Space Ecosystem (CDSE) Sentinel Hub OAuth2
credentials (client_id / client_secret) are valid and have access to the
Sentinel Hub Catalog API (https://sh.dataspace.copernicus.eu/catalog/v1/).

SECURITY NOTE:
Do NOT print secrets or tokens in stdout.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import requests

# Load environment variables from root-level .env
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# Read credentials from environment
effective_client_id = os.environ.get("CDSE_CLIENT_ID", "").strip()
effective_client_secret = os.environ.get("CDSE_CLIENT_SECRET", "").strip()

# Sentinel Hub client IDs typically start with 'sh-'. If swapped, auto-detect:
if effective_client_secret.startswith("sh-") and not effective_client_id.startswith("sh-"):
    print("[INFO] Detected swapped Client ID and Client Secret; auto-adjusting order.")
    effective_client_id, effective_client_secret = effective_client_secret, effective_client_id

TOKEN_URL = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
CATALOG_URL = "https://sh.dataspace.copernicus.eu/catalog/v1/"
TIMEOUT_SECONDS = 30


def test_cdse_authentication() -> int:
    print("=" * 60)
    print("COPERNICUS DATA SPACE (CDSE) SENTINEL HUB AUTHENTICATION TEST")
    print("=" * 60)

    if not effective_client_id or not effective_client_secret:
        print("\n[ERROR] CDSE credentials not found or empty in environment / .env file.")
        print("Please configure CDSE_CLIENT_ID and CDSE_CLIENT_SECRET in the root .env file.\n")
        print("OAuth authentication: FAILED")
        return 1

    print(f"Token Endpoint: {TOKEN_URL}")
    print("Sending OAuth token request (grant_type=client_credentials)...")

    token_payload = {
        "grant_type": "client_credentials",
        "client_id": effective_client_id,
        "client_secret": effective_client_secret,
    }

    try:
        token_resp = requests.post(
            TOKEN_URL,
            data=token_payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=TIMEOUT_SECONDS,
        )
    except requests.exceptions.Timeout:
        print(f"[ERROR] Token request timed out after {TIMEOUT_SECONDS} seconds.")
        return 1
    except requests.exceptions.ConnectionError as e:
        print(f"[ERROR] Connection failed: {e}")
        return 1
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Request failed with exception: {e}")
        return 1

    print(f"OAuth Token HTTP Status: {token_resp.status_code}")

    if token_resp.status_code != 200:
        print("\nOAuth authentication: FAILED")
        try:
            err_data = token_resp.json()
            err_msg = (
                err_data.get("error_description")
                or err_data.get("error")
                or str(err_data)
            )
            print(f"Error Details: {err_msg}")
        except Exception:
            print(f"Response Body: {token_resp.text}")
        return 1

    try:
        token_json = token_resp.json()
        access_token = token_json.get("access_token")
    except Exception as e:
        print(f"[ERROR] Failed to parse JSON response: {e}")
        return 1

    if not access_token:
        print("\nOAuth authentication: FAILED (No access_token field in response)")
        return 1

    print("OAuth authentication: SUCCESS")

    # Step 2: Test Sentinel Hub Catalog API access
    print(f"\nCatalog API Endpoint: {CATALOG_URL}")
    print("Sending authenticated GET request to Catalog API...")

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
    }

    try:
        catalog_resp = requests.get(
            CATALOG_URL,
            headers=headers,
            timeout=TIMEOUT_SECONDS,
        )
    except requests.exceptions.Timeout:
        print(f"[ERROR] Catalog API request timed out after {TIMEOUT_SECONDS} seconds.")
        return 1
    except requests.exceptions.ConnectionError as e:
        print(f"[ERROR] Catalog API connection failed: {e}")
        return 1
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Catalog API request failed with exception: {e}")
        return 1

    print(f"Catalog API HTTP Status: {catalog_resp.status_code}")

    if catalog_resp.status_code == 200:
        print("Sentinel Hub API access: SUCCESS")
        return 0
    else:
        print("\nSentinel Hub API access: FAILED")
        try:
            err_data = catalog_resp.json()
            print(f"Error Details: {err_data}")
        except Exception:
            print(f"Response Body: {catalog_resp.text}")
        return 1


if __name__ == "__main__":
    sys.exit(test_cdse_authentication())
