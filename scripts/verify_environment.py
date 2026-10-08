"""
Verification script for research project environment and configuration.

Verifies:
1. Python environment (version, architecture, executable).
2. Input data directory presence and CSV count (strictly non-modifying, no heavy reads).
3. NASA FIRMS MAP_KEY presence in .env/environment WITHOUT printing or logging its value.
4. Dependency availability against requirements.txt (inspection only, non-fatal if not installed).
"""

from __future__ import annotations

import importlib.util
import os
import platform
import re
import sys
from pathlib import Path

# Add project root to sys.path so src modules can be resolved
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.utils.config import get_config, is_firms_map_key_set


def check_python_environment() -> bool:
    """Verifies Python version and platform architecture."""
    print("=" * 70)
    print("1. Python Environment Check")
    print("=" * 70)
    py_version = sys.version_info
    print(f"  Python Version:      {py_version.major}.{py_version.minor}.{py_version.micro}")
    print(f"  Platform:            {platform.platform()} ({platform.architecture()[0]})")
    print(f"  Executable:          {sys.executable}")

    if py_version.major == 3 and py_version.minor >= 10:
        print("  [PASS] Python version >= 3.10 is compatible with research stack.")
        return True
    else:
        print(f"  [WARN] Python 3.10+ recommended (found {py_version.major}.{py_version.minor}).")
        return False


def check_data_directory() -> bool:
    """
    Checks the existence of the raw data directory and counts CSV files.
    Strictly read-only; does not open or process CSV records.
    """
    print("\n" + "=" * 70)
    print("2. Input Data Directory Check")
    print("=" * 70)
    config = get_config()
    data_dir = config.raw_data_dir

    print(f"  Configured Directory: {data_dir}")

    if not data_dir.exists():
        print(f"  [INFO] Directory '{data_dir}' does not exist yet.")
        print("         Expected location for 73 NASA FIRMS VIIRS NOAA-20 CSV files.")
        return False

    # Check direct or subdirectory (e.g. data/raw/2025)
    csv_files = sorted(list(data_dir.glob("*.csv")) + list(data_dir.glob("*/*.csv")))
    # Deduplicate in case of duplicate paths
    csv_files = sorted(list(set(csv_files)))
    csv_count = len(csv_files)
    print(f"  Found 2025 CSV Files: {csv_count} / 73 expected")

    if csv_count == 73:
        print("  [PASS] Exactly 73 CSV files detected for 2025 India corpus.")
    elif csv_count == 0:
        print("  [INFO] Primary 2025 raw data directory is currently empty.")
        print("         Expected: 73 NOAA-20 VIIRS CSV files (1,024,996 India detections).")
    else:
        print(f"  [NOTICE] Found {csv_count} CSV files (73 expected for 2025 India corpus).")

    # Context Burn-in Directory Check
    context_dir = config.raw_context_dir
    print(f"\n  Context Directory:    {context_dir}")
    if context_dir.exists():
        context_files = sorted(list(set(list(context_dir.glob("*.csv")) + list(context_dir.glob("*/*.csv")))))
        print(f"  Found Context Files:  {len(context_files)} / 19 expected (Q4 2024 India burn-in)")
        if len(context_files) == 19:
            print("  [PASS] Exactly 19 context CSV files detected.")
    else:
        print(f"  [INFO] Context directory '{context_dir}' not found.")

    return csv_count == 73 and len(context_files) == 19


def check_firms_credentials() -> bool:
    """
    Checks if FIRMS_MAP_KEY is present and configured.
    CRITICAL: Never reveals, prints, or logs the value of the key.
    """
    print("\n" + "=" * 70)
    print("3. NASA FIRMS MAP_KEY Configuration Check")
    print("=" * 70)

    is_set = is_firms_map_key_set()

    if is_set:
        print("  [PASS] FIRMS_MAP_KEY is configured in environment/.env.")
        print("         Security Check: Value is masked and unexposed.")
        return True
    else:
        print("  [INFO] FIRMS_MAP_KEY is not set or contains the default placeholder.")
        print("         To configure: set FIRMS_MAP_KEY in .env (see .env.example).")
        print("         Security Check: Key is absent, nothing exposed.")
        return False


def check_required_packages() -> None:
    """
    Inspects installed vs pending packages from requirements.txt without crashing.
    """
    print("\n" + "=" * 70)
    print("4. Dependencies Status Check (requirements.txt)")
    print("=" * 70)

    req_file = PROJECT_ROOT / "requirements.txt"
    if not req_file.exists():
        print("  [WARN] requirements.txt not found.")
        return

    packages: list[str] = []
    with open(req_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # Extract package name before operators like >=, ==, <
            pkg_name = re.split(r"[><=~]", line)[0].strip()
            if pkg_name:
                packages.append(pkg_name)

    # Standard mappings for import names that differ from package names
    module_name_map = {
        "pyyaml": "yaml",
        "python-dotenv": "dotenv",
        "scikit-learn": "sklearn",
    }

    installed = []
    missing = []

    for pkg in packages:
        module_name = module_name_map.get(pkg.lower(), pkg.replace("-", "_"))
        spec = importlib.util.find_spec(module_name)
        if spec is not None:
            installed.append(pkg)
        else:
            missing.append(pkg)

    print(f"  Total packages listed: {len(packages)}")
    print(f"  Currently installed:   {len(installed)}")
    print(f"  Pending installation:  {len(missing)}")

    if installed:
        print(f"  Installed: {', '.join(installed)}")
    if missing:
        print(f"  Pending:   {', '.join(missing)}")
        print("  (Note: Installation should occur only when user authorizes.)")


def main() -> int:
    print("\n" + "#" * 70)
    print("# SATELLITE THERMAL ANOMALY CLASSIFICATION: SETUP VERIFICATION")
    print("#" * 70 + "\n")

    check_python_environment()
    check_data_directory()
    check_firms_credentials()
    check_required_packages()

    print("\n" + "=" * 70)
    print("Verification completed successfully. No data modified or exposed.")
    print("=" * 70 + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
