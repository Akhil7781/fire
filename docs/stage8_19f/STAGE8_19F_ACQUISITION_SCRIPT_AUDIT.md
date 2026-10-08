# Stage 8.19F — Stage 8.20 Acquisition Script Audit Report

**Date:** 2026-10-03  
**Auditor:** Senior Remote-Sensing Researcher, Geospatial Validation Engineer & Software Safety Reviewer  
**Target Script:** `scripts/stage8_20_pilot_acquisition.py`  
**Target Script Hash (SHA-256):** `1352f568fce72f411209587adaff8d286441edbd83e4749475a04929c87450a1`  
**Status:** **AUDITED_AND_VERIFIED_SAFE**

---

## 1. Executive Summary

A comprehensive, static and dynamic code-safety audit of `scripts/stage8_20_pilot_acquisition.py` was conducted in accordance with Stage 8.19F requirements. The audit confirms that the acquisition script is strictly bounded to the 8-chip pilot batch, enforces an uncompromising human-authorization gate (`--confirm-acquisition`), downloads exactly 0 bytes in dry-run mode, creates no directories or partial assets without authorization, and has preserved all data integrity safeguards during the Stage 8.19E update.

---

## 2. Pilot Cohort Restriction Audit (Section 11.1)

### 2.1 Explicit Cohort Definition
In `scripts/stage8_20_pilot_acquisition.py`, the pilot batch is explicitly hardcoded in `PILOT_CHIP_IDS` (lines 33–42):
```python
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
```

### 2.2 Absence of Unbounded Execution Paths
The execution function `run_acquisition_pilot` filters the manifest exclusively by this explicit list:
```python
manifest_map = {r["chip_id"]: r for r in manifest_data["records"]}
pilot_records = [manifest_map[cid] for cid in PILOT_CHIP_IDS if cid in manifest_map]
assert len(pilot_records) == 8, f"Expected 8 pilot records, found {len(pilot_records)}"
```
* **No Iteration over Full Dataset:** There is zero code path iterating over `manifest_data["records"]` for download.
* **No Fold-Level Traversal:** Folds 1–5 are not iterated.
* **No Benchmark Ingestion:** The 15 held-out benchmark pilot chips (`STR-7`) cannot be touched.
* **Size Assertion:** If the filtered record count is not exactly 8, execution aborts immediately via assertion.

---

## 3. Explicit Confirmation Gate Audit (Section 11.2)

### 3.1 Confirmation Flag Mechanism
The script uses `argparse` with a strict default `False` boolean flag:
```python
parser.add_argument(
    "--confirm-acquisition",
    action="store_true",
    default=False,
    help="Explicit confirmation flag required to initiate raster downloads. Without this flag, script runs in dry-run mode."
)
```

### 3.2 Guard Execution Logic
In lines 108–122:
```python
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
```
* **Early Return:** If `--confirm-acquisition` is absent, the function prints the safeguard warning and returns immediately.
* **Directory Creation Blocked:** Output directory creation (`PILOT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)`) is situated *after* the guard check (line 130). In dry-run mode, no directories are created.
* **Network Requests Blocked:** No download HTTP GET requests or raster retrieval endpoints are invoked without the flag.

---

## 4. Dry-Run Verification (Section 11.3)

### 4.1 Invocation Command
```powershell
python scripts/stage8_20_pilot_acquisition.py
```

### 4.2 Exact Captured Output
```text
===========================================================================
STAGE 8.20: CONTROLLED ACQUISITION PILOT
===========================================================================
Using manifest: ds08_expansion_candidates_v4.json

Target Pilot Batch Size: 8 chips
  P-01: DS08_EXP_S1_003 | Stratum: STR-1 | Scene Cloud: 0.0%
        Product: S2B_MSIL2A_20250413T052649_N0511_R105_T43RFN_20250413T074009.SAFE
  P-02: DS08_EXP_S1_002 | Stratum: STR-1 | Scene Cloud: 14.74% [DEC-U5 EXCEPTION]
        Product: S2B_MSIL2A_20250325T045659_N0511_R119_T44QQE_20250325T074633.SAFE
  P-03: DS08_EXP_S1_004 | Stratum: STR-1 | Scene Cloud: 19.32% [DEC-U5 EXCEPTION]
        Product: S2C_MSIL2A_20251028T053951_N0511_R005_T42QZH_20251028T084920.SAFE
  P-04: DS08_EXP_S2_001 | Stratum: STR-2 | Scene Cloud: 0.0%
        Product: S2B_MSIL2A_20250608T054639_N0511_R048_T43SBS_20250608T074909.SAFE
  P-05: DS08_EXP_S3_001 | Stratum: STR-3 | Scene Cloud: 0.24%
        Product: S2B_MSIL2A_20250516T053639_N0511_R005_T43RDP_20250516T074822.SAFE
  P-06: DS08_EXP_S4_001 | Stratum: STR-4 | Scene Cloud: 0.08%
        Product: S2A_MSIL2A_20241023T053901_N0511_R005_T43RFP_20241023T090052.SAFE
  P-07: DS08_EXP_S5_001 | Stratum: STR-5 | Scene Cloud: 0.0%
        Product: S2C_MSIL2A_20250128T053131_N0511_R105_T43RGM_20250128T084454.SAFE
  P-08: DS08_EXP_S6_001 | Stratum: STR-6 | Scene Cloud: 0.0%
        Product: S2B_MSIL2A_20250212T052839_N0511_R105_T44RKS_20250212T073606.SAFE

Credential Inspection: CDSE Credentials configured in environment: True

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
SAFEGUARD ACTIVE: --confirm-acquisition flag was NOT provided.
Operating in READ-ONLY / DRY-RUN inspection mode.
Zero bytes of imagery downloaded.
To execute pilot acquisition after human authorization, run:
  python scripts/stage8_20_pilot_acquisition.py --confirm-acquisition
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
```

### 4.3 Filesystem Verification
* Output directory `data/interim/ds08_stage8_20_pilot`: **Does NOT exist** (`os.path.exists == False`).
* Raster bytes downloaded: **0 bytes**.
* SAFE archives downloaded: **0**.
* JP2 files downloaded: **0**.

---

## 5. Script Modifications Audit (Section 11.4)

### 5.1 Nature of Changes in Stage 8.19E
In Stage 8.19E, the script was updated to resolve Manifest pathing:
* **Added Path Definition:**
  ```python
  MANIFEST_V4_PATH = PROJECT_ROOT / "data" / "reference" / "ds08" / "manifests" / "stage8_19e" / "ds08_expansion_candidates_v4.json"
  ```
* **Dynamic Fallback Selection:**
  ```python
  target_manifest = manifest_path or (MANIFEST_V4_PATH if MANIFEST_V4_PATH.exists() else MANIFEST_V3_PATH)
  ```
* **No Weakening of Safeguards:**
  * The `--confirm-acquisition` requirement was unaltered.
  * `PILOT_CHIP_IDS` remained strictly restricted to the 8 pilot chips.
  * Dry-run logic remained unchanged.
  * Credential loading from `.env` without printing or logging secrets was preserved.

---

## 6. Audit Verdict

| Safety Check | Requirement | Audit Result | Status |
| :--- | :--- | :--- | :---: |
| Pilot Batch Restriction | Exactly 8 pilot chips; no bulk iteration | Hardcoded list; length assertion = 8 | **PASS** |
| Confirmation Guard | `--confirm-acquisition` required | Returns early with warning if flag omitted | **PASS** |
| Dry Run Bytes Downloaded | Exactly 0 bytes | 0 bytes downloaded | **PASS** |
| Filesystem Modification | No directory created before confirmation | `data/interim/ds08_stage8_20_pilot` not created | **PASS** |
| Safeguard Integrity | No weakened controls in 8.19E updates | Path selector added; safeguards untouched | **PASS** |

**Conclusion:** The acquisition script is **PROVEN_SAFE** and complies fully with all project safeguards.
