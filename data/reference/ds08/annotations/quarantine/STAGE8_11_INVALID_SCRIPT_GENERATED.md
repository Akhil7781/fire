# DS08 Stage 8.11 Annotation Quarantine Record

**Date:** 2026-09-29  
**Status:** `INVALID_SCRIPT_GENERATED`  
**Quarantine Location:** `data/reference/ds08/annotations/quarantine/stage8_11_script_generated/`  
**Audit Reference:** `STAGE 8.11 PROVENANCE AUDIT`  

---

## 1. Audit Finding and Reason for Invalidation

Following the strict Stage 8.11 provenance audit, the 15 remaining pilot chip annotation pairs (30 annotation draft files total) created during Stage 8.11 were found to have been generated programmatically:
- Substantive annotation decisions (class labels, bounding box coordinates, visual evidence tags, and confidence scores) were hardcoded in dictionary data structures (`A1_DATA` / `A2_DATA`) and generated via automated scripts rather than through genuine, independent human visual inspection.
- No independent human input was evidenced.
- Consequently, Stage 8.11 failed the provenance audit under the frozen DS08 v1.0 protocol.

---

## 2. Absolute Prohibitions on Quarantined Files

The 30 files located in `data/reference/ds08/annotations/quarantine/stage8_11_script_generated/`:
1. **Provenance & Audit Only:** Are retained strictly and exclusively for historical provenance, transparency, and audit tracking.
2. **Not Human Ground Truth:** Are **NOT** valid human annotations.
3. **No Model Training:** Must **NOT** be used for model training (TCN, Deep SAD, YOLO, or downstream architectures).
4. **No Validation / Evaluation:** Must **NOT** be used for model validation or benchmark test evaluation.
5. **No Agreement Calculations:** Must **NOT** enter inter-annotator agreement calculations (e.g., Cohen's kappa, raw agreement, box IoU, evidence Jaccard).
6. **No Adjudication:** Must **NOT** be adjudicated as if they were genuine human drafts.
7. **No Finalization:** Must **NOT** be copied or promoted to `data/reference/ds08/annotations/final/`.

The 3 genuine Stage 8.10B-C adjudicated files (`PILOT_01_NORTH`, `PILOT_13_EAST`, `PILOT_17_WEST`) and the 5 genuine Stage 8.10A agreed draft pairs in `draft/` remain completely untouched and authoritative.

---

## 3. Machine-Readable Provenance Metadata

- **`status`**: `INVALID_SCRIPT_GENERATED`
- **`reason`**: `substantive annotation decisions were generated programmatically`
- **`human_verified`**: `false`
- **`eligible_for_training`**: `false`
- **`eligible_for_validation`**: `false`
- **`eligible_for_evaluation`**: `false`
- **`eligible_for_agreement`**: `false`
- **`eligible_for_adjudication`**: `false`

Refer to `data/reference/ds08/annotations/quarantine/stage8_11_script_generated/quarantine_manifest.json` for full machine-readable metadata.

---

## 4. Quarantined Files Inventory & SHA-256 Hashes

### Annotator 1 Quarantined Files (15 files)
| Chip ID | Filename | SHA-256 Checksum |
| :--- | :--- | :--- |
| `PILOT_02_NORTH` | `PILOT_02_NORTH_annotator1.json` | `8db6c14246ca452a902bae6e2edef6de2cab8aca202829815eccf768a185eb85` |
| `PILOT_03_NORTH` | `PILOT_03_NORTH_annotator1.json` | `ea5bc5c914cad01cc016911cdf18af25b52d160e38e6d2b748b9252f5f3e50b5` |
| `PILOT_04_NORTH_REPLACEMENT` | `PILOT_04_NORTH_REPLACEMENT_annotator1.json` | `0a033246b9fabfe0dd66558a1568209c64514e3322b72c7618722290b81110c9` |
| `PILOT_06_CENTRAL` | `PILOT_06_CENTRAL_annotator1.json` | `43da024098c74d0cdf7f5377dfacd157a7e7373d0fdc950d424e20829f426be3` |
| `PILOT_07_CENTRAL` | `PILOT_07_CENTRAL_annotator1.json` | `8e14b947f8ca7d730aede742403248c050ad466870090040f754df50620aa887` |
| `PILOT_08_CENTRAL` | `PILOT_08_CENTRAL_annotator1.json` | `a81a19b05e6fa7ca8fa25c3740dab8b031fba2194f95ee9819e769ffe433ce75` |
| `PILOT_10_SOUTH` | `PILOT_10_SOUTH_annotator1.json` | `b44f75dcdbcbaf3b63fce83d9100cea5ffc001a6a4f39d8fa6b252f350de5cd7` |
| `PILOT_11_SOUTH` | `PILOT_11_SOUTH_annotator1.json` | `49eba7328164a2c084afb4017518d7930cc079aa542dd24e5cd1274704798499` |
| `PILOT_12_SOUTH` | `PILOT_12_SOUTH_annotator1.json` | `6e1935a504913809cda1677b5d637e1b344e752922445c51e785c17d87e754cd` |
| `PILOT_14_EAST` | `PILOT_14_EAST_annotator1.json` | `ed9ee9cb7374eb2ae1466964043dc7f016c19531ab78c67997133396cedf9406` |
| `PILOT_15_EAST` | `PILOT_15_EAST_annotator1.json` | `15c8e0ae133701e3e2cb5b170e5837e0544fbd9f6bd6bb7f8225fa9a88a38be2` |
| `PILOT_16_EAST` | `PILOT_16_EAST_annotator1.json` | `1097ddb09342f3442ac15b90d0546a837df4462219c1dc2f4b5706b522e60e3f` |
| `PILOT_18_WEST` | `PILOT_18_WEST_annotator1.json` | `d94be6c572171ec7312bd39e0a4670f2b7391dc2d70afa0cb3dde66900a5a0a9` |
| `PILOT_19_WEST` | `PILOT_19_WEST_annotator1.json` | `1e7de640fe63fd3a0f2e878c8a8153a04fcc2e3226acfd9ba61f7c3e1c71342f` |
| `PILOT_20_WEST` | `PILOT_20_WEST_annotator1.json` | `1180328d5629cc31df9a5c252d067bc0ac33a27dd245462e35b6b4651619dfdc` |

### Annotator 2 Quarantined Files (15 files)
| Chip ID | Filename | SHA-256 Checksum |
| :--- | :--- | :--- |
| `PILOT_02_NORTH` | `PILOT_02_NORTH_annotator2.json` | `8db6c14246ca452a902bae6e2edef6de2cab8aca202829815eccf768a185eb85` |
| `PILOT_03_NORTH` | `PILOT_03_NORTH_annotator2.json` | `1864a10e9684dec2a24b7e67e9d3c3d3c8dd6d32f1bd0bed52d22cc97b2a69d0` |
| `PILOT_04_NORTH_REPLACEMENT` | `PILOT_04_NORTH_REPLACEMENT_annotator2.json` | `0a033246b9fabfe0dd66558a1568209c64514e3322b72c7618722290b81110c9` |
| `PILOT_06_CENTRAL` | `PILOT_06_CENTRAL_annotator2.json` | `e2ae6ac445f2d537c3ee718510dfba0f70117e8d423dde29974f52e81d735964` |
| `PILOT_07_CENTRAL` | `PILOT_07_CENTRAL_annotator2.json` | `8e14b947f8ca7d730aede742403248c050ad466870090040f754df50620aa887` |
| `PILOT_08_CENTRAL` | `PILOT_08_CENTRAL_annotator2.json` | `0e212e514c8f63e679c2d60db825a2b5b31dc58dbbdbb6c84903de9bdba0b7b5` |
| `PILOT_10_SOUTH` | `PILOT_10_SOUTH_annotator2.json` | `b44f75dcdbcbaf3b63fce83d9100cea5ffc001a6a4f39d8fa6b252f350de5cd7` |
| `PILOT_11_SOUTH` | `PILOT_11_SOUTH_annotator2.json` | `49eba7328164a2c084afb4017518d7930cc079aa542dd24e5cd1274704798499` |
| `PILOT_12_SOUTH` | `PILOT_12_SOUTH_annotator2.json` | `6e1935a504913809cda1677b5d637e1b344e752922445c51e785c17d87e754cd` |
| `PILOT_14_EAST` | `PILOT_14_EAST_annotator2.json` | `52f836685666a71ee293ddbcfd0a2cccde9a49e0c38206b0779ce53f4f8ee6e6` |
| `PILOT_15_EAST` | `PILOT_15_EAST_annotator2.json` | `6f148b37175d164b5e36599870768ccf96de8c6b33ea648c46c0e4ad7f67f0bc` |
| `PILOT_16_EAST` | `PILOT_16_EAST_annotator2.json` | `5ee54acc1933af8ba433701788917c55156957cb10deeb7a8e821ab6a82f3423` |
| `PILOT_18_WEST` | `PILOT_18_WEST_annotator2.json` | `4bb7a8ce6435be6c250f05b987f93bcb336730fe435cd07113af723d1d213422` |
| `PILOT_19_WEST` | `PILOT_19_WEST_annotator2.json` | `38bcd828065112b3953227db555bc8e87c9ba87a7c8b41480e50b9c6c527a8de` |
| `PILOT_20_WEST` | `PILOT_20_WEST_annotator2.json` | `1180328d5629cc31df9a5c252d067bc0ac33a27dd245462e35b6b4651619dfdc` |
