# Stage 8.19G — Stage 8.20 Acquisition Safety Re-Audit and Wording Resolution

**Date:** 2026-10-03  
**Auditor / Reviewer Role:** Software Safety Auditor, Remote-Sensing Systems Engineer & Geospatial Validation Engineer  
**Workspace:** `d:/DATA PREPROCESSING`  
**Target Script:** `scripts/stage8_20_pilot_acquisition.py`  
**Script Hash (SHA-256):** `1352f568fce72f411209587adaff8d286441edbd83e4749475a04929c87450a1`  
**Safety Status:** **VERIFIED_SAFE_NO_REGRESSION**

---

## 1. Executive Summary

This report delivers a rigorous, adversarial re-audit of the safety controls in `scripts/stage8_20_pilot_acquisition.py`. It specifically resolves the ambiguous phrasing identified in Stage 8.19F ("weakened zero safety checks"), conducts a line-by-line inspection of all changes introduced during Stage 8.19E, verifies dry-run behavior, audits credential isolation, and checks for subtle security or operational regressions.

**Key Findings:**
1. **Critical Wording Clarification:** The ambiguous phrase "weakened zero safety checks" was a clumsy grammatical construction intended to assert that *zero safety checks were weakened*. Code audit confirms that **no safety controls were weakened or bypassed**.
2. **Pilot Restriction Intact:** Execution is hardcoded strictly to the 8 pilot chips (`PILOT_CHIP_IDS`). There is no code path for bulk or candidate-wide execution.
3. **Confirmation Gate Intact:** Raster acquisition strictly requires `--confirm-acquisition`. Default execution operates in dry-run mode, downloading **0 bytes** and writing **0 files**.
4. **Credential Isolation Intact:** Environment credentials are inspected for existence; only boolean status is printed. Secrets and tokens are never printed, written, or exported.
5. **No Regressions Found:** Zero safety regressions exist in the script.

---

## 2. Line-by-Line Script Modification Audit (Section 13)

A code comparison of `scripts/stage8_20_pilot_acquisition.py` between its initial Stage 8.19B state and the current repository state was performed:

### 2.1 Manifest Path Definition
* **Lines 28–29:**
  ```python
  MANIFEST_V4_PATH = PROJECT_ROOT / "data" / "reference" / "ds08" / "manifests" / "stage8_19e" / "ds08_expansion_candidates_v4.json"
  MANIFEST_V3_PATH = PROJECT_ROOT / "data" / "reference" / "ds08" / "manifests" / "stage8_19b" / "ds08_expansion_candidates_v3.json"
  ```
* **Previous Behavior:** In Stage 8.19B, the script referenced only `MANIFEST_V3_PATH`.
* **Current Behavior:** Defines both V4 and V3 paths.
* **Reason:** To allow the acquisition pipeline to read the reconciled Manifest v4 while retaining fallback to v3.
* **Safety Impact:** **NEUTRAL**. Both manifests contain the 8 pilot records.

### 2.2 Manifest Resolution Logic
* **Line 86:**
  ```python
  target_manifest = manifest_path or (MANIFEST_V4_PATH if MANIFEST_V4_PATH.exists() else MANIFEST_V3_PATH)
  ```
* **Previous Behavior:** Loaded `MANIFEST_V3_PATH` directly.
* **Current Behavior:** Selects `manifest_path` (if provided via argument) or defaults to `MANIFEST_V4_PATH` if present, falling back to `MANIFEST_V3_PATH`.
* **Reason:** Ensures that reconciled CDSE product identifiers in Manifest v4 are utilized for pilot acquisition.
* **Safety Impact:** **POSITIVE**. Directs the pipeline to verified, downloadable CDSE products rather than unresolved placeholder strings.

---

## 3. Critical Wording Resolution (Section 14)

### 3.1 The Ambiguous Phrase
In Stage 8.19F documentation, the phrase appeared:
> *"Inspection confirms that the only change in Stage 8.19E was the addition of MANIFEST_V4_PATH fallback logic. Weakened zero safety checks."*

This phrasing is awkward and grammatically ambiguous:
* It could be misinterpreted colloquially as "weakened down to zero safety checks" (an alarming false implication that checks were destroyed).
* Or it was intended as a literal translation of "number of safety checks weakened = 0".

### 3.2 Evaluation Against Code Truth
To resolve this rigorously, the three hypotheses defined in Section 14 were tested:
* **Hypothesis A (Checks were genuinely weakened):** **DISPROVEN**. Inspection of the codebase reveals that:
  - The confirmation flag check `if not confirm_acquisition:` is present on line 109 and returns early before any download code.
  - The pilot filter `pilot_records = [manifest_map[cid] for cid in PILOT_CHIP_IDS if cid in manifest_map]` and its assertion `assert len(pilot_records) == 8` are active on lines 93–95.
  - The default argument for `--confirm-acquisition` remains `default=False` on line 69.
  - Output directory creation `PILOT_OUTPUT_DIR.mkdir(...)` remains gated behind line 130.
* **Hypothesis B (Safety checks were not weakened; phrasing was an awkward grammatical construction):** **PROVEN**. Every safety control present in Stage 8.19B remains fully intact in Stage 8.19E/F/G.
* **Hypothesis C (Insufficient evidence):** **DISPROVEN**. The full script source code is on disk, readable, executable, and fully audited.

### 3.3 Formal Clarification
The phrase is officially amended and clarified as:
> **"Zero safety checks were weakened; all pre-existing safeguards and confirmation gates remain strictly active and unaltered."**

---

## 4. Systematic Verification of Safety Requirements (Section 15)

### 4.1 Pilot Restriction Audit
* **Code Implementation (lines 33–42):**
  ```python
  PILOT_CHIP_IDS = [
      "DS08_EXP_S1_003",
      "DS08_EXP_S1_002",
      "DS08_EXP_S1_004",
      "DS08_EXP_S2_001",
      "DS08_EXP_S3_001",
      "DS08_EXP_S4_001",
      "DS08_EXP_S5_001",
      "DS08_EXP_S6_001",
  ]
  ```
* **Filter & Length Assertion (lines 93–95):**
  ```python
  manifest_map = {r["chip_id"]: r for r in manifest_data["records"]}
  pilot_records = [manifest_map[cid] for cid in PILOT_CHIP_IDS if cid in manifest_map]
  assert len(pilot_records) == 8, f"Expected 8 pilot records, found {len(pilot_records)}"
  ```
* **Verification:** Execution is hardcoded to these 8 chips. There is **zero code path** that iterates over `manifest_data["records"]` or processes the other 227 candidate records.

### 4.2 Confirmation Gate Audit
* **Code Implementation (lines 66–71 & 109–122):**
  ```python
  parser.add_argument(
      "--confirm-acquisition",
      action="store_true",
      default=False,
      help="Explicit confirmation flag required to initiate raster downloads. Without this flag, script runs in dry-run mode."
  )
  ...
  if not confirm_acquisition:
      print("\nSAFEGUARD ACTIVE: --confirm-acquisition flag was NOT provided.")
      print("Operating in READ-ONLY / DRY-RUN inspection mode.")
      print("Zero bytes of imagery downloaded.")
      return {
          "mode": "DRY_RUN",
          "pilot_chips_evaluated": len(pilot_records),
          "status": "READY_FOR_OWNER_AUTHORIZATION",
          "downloaded_bytes": 0
      }
  ```
* **Verification:** Without `--confirm-acquisition`, the script prints the safeguard warning and returns immediately. No raster download logic can be reached.

### 4.3 Dry-Run Execution Evidence
* **Command:** `python scripts/stage8_20_pilot_acquisition.py`
* **Captured Output:**
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
* **Disk Check:** Directory `data/interim/ds08_stage8_20_pilot` **does not exist** (`os.path.exists == False`). Exactly **0 bytes** downloaded and **0 files** written.

### 4.4 Credential Safety Audit
* `load_credentials_from_env()` reads from `os.environ` or `.env` without printing or logging secrets.
* Line 106 prints only:
  ```python
  has_creds = bool(client_id and client_secret)
  print(f"\nCredential Inspection: CDSE Credentials configured in environment: {has_creds}")
  ```
* No client ID, secret, token, or signed URL is printed to terminal or saved to logs.

---

## 5. Comprehensive Regression Scan (Section 16)

A systematic search for subtle safety regressions was performed:

| Vulnerability Check | Audit Finding | Result |
| :--- | :--- | :---: |
| **Removed confirmation checks** | Guard check on line 109 is present and returns before any network logic | **NONE** |
| **Changed default to acquisition** | `--confirm-acquisition` default is strictly `False` | **NONE** |
| **Broadened manifest selection** | Execution remains strictly filtered to `PILOT_CHIP_IDS` (8 chips) | **NONE** |
| **Removed pilot hardcoding** | `PILOT_CHIP_IDS` is explicitly defined on line 33 | **NONE** |
| **Output-path modifications** | Output path remains `data/interim/ds08_stage8_20_pilot` | **NONE** |
| **Accidental disk writes** | `mkdir` is located on line 130, after the confirmation return | **NONE** |
| **Automatic download on metadata** | Dry run performs only JSON manifest lookup; zero network calls made | **NONE** |
| **Credential/Token leakage** | Only boolean presence check printed; no secret strings logged | **NONE** |
| **HTTP download before confirmation** | No HTTP GET/POST calls exist prior to the confirmation return | **NONE** |

**Verdict:** **NO_SAFETY_REGRESSION_FOUND**

---

## 6. Audit Conclusion

The Stage 8.20 acquisition script `scripts/stage8_20_pilot_acquisition.py` is **100% VERIFIED SAFE**:
* Pilot cohort is rigidly constrained to 8 chips.
* Confirmation gate is impenetrable in dry-run mode.
* No credentials leaked.
* The script is fully ready for controlled human authorization.
