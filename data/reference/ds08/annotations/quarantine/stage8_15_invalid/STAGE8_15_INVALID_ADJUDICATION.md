# STAGE 8.15 — INVALID ADJUDICATION QUARANTINE RECORD
**Quarantine Timestamp (UTC):** `2026-09-30T17:01:45Z`  
**Quarantine Destination:** `data/reference/ds08/annotations/quarantine/stage8_15_invalid/`  
**Quarantine Action:** Isolated 6 invalid Stage 8.15 adjudication files.

---

## 1. Formal Non-Consensus Statement

> [!CAUTION]
> **CRITICAL SCIENTIFIC & PROVENANCE NOTICE:**  
> The 6 annotation files stored in this quarantine directory are **STRICTLY INVALID AND DO NOT CONSTITUTE VALID HUMAN CONSENSUS LABELS**.
> 
> They were rejected during the Stage 8.15 persistence audit due to:
> 1. Use of prohibited, generic, non-substantive human rationales (`"I saw the fire on the image"` / `"i saw the fire in the image"`).
> 2. Contamination by repeated injection of the default UI placeholder bounding box coordinates `[200, 200, 300, 300]`.
> 3. Substantive misclassification in `PILOT_08_CENTRAL` (recorded as `Forest Fire` in agricultural cropland).
> 
> **THESE FILES MUST NEVER BE USED FOR MODEL TRAINING, FINE-TUNING, EMBEDDING EXTRACTION, BENCHMARKING, OR EVALUATION.**

---

## 2. Quarantined File Inventory & Audit Record

| Chip ID | Quarantined Filename | Pre-Quarantine SHA-256 | Reason for Rejection |
| :--- | :--- | :--- | :--- |
| **`PILOT_03_NORTH`** | `PILOT_03_NORTH_adjudicated_v1.json` | `19d178f719bd2388deaa3118ae3b67c5b909af5f0ee0b67ac0b10fe3f9c644d8` | Rejected: Prohibited generic rationale (`"I saw the fire on the image"`); contains 4 duplicate dummy boxes `[200, 200, 300, 300]`. |
| **`PILOT_06_CENTRAL`** | `PILOT_06_CENTRAL_adjudicated_v1.json` | `4daacbf1d4ae81e195c8cd55f6cd7ff94016e86d7ce918b0613f136ec135ac14` | Rejected: Prohibited generic rationale (`"i saw the fire in the image"`); contains dummy box `[200, 200, 300, 300]`. |
| **`PILOT_08_CENTRAL`** | `PILOT_08_CENTRAL_adjudicated_v1.json` | `0126d191fe5fdcaddd1fe949aaa03e77409ce6c11c08ec68157244a02294d6c4` | Rejected: Prohibited generic rationale (`"i saw the fire in the image"`); contains 2 duplicate dummy boxes `[200, 200, 300, 300]`; misclassified cropland as `Forest Fire`. |
| **`PILOT_15_EAST`** | `PILOT_15_EAST_adjudicated_v1.json` | `33fff598556b5c40d6735bd094a7c594f4b62d55c89c234f66dec3371d1b87df` | Rejected: Prohibited generic rationale (`"i saw the fire in the image"`); contains 4 duplicate dummy boxes `[200, 200, 300, 300]`. |
| **`PILOT_16_EAST`** | `PILOT_16_EAST_adjudicated_v1.json` | `6ea36b624fc0343289a3629741c56fe69b54576b683c4c65a2338ca44e753222` | Rejected: Prohibited generic rationale (`"i saw the fire in the image"`); contains 8 duplicate dummy boxes `[200, 200, 300, 300]`. |
| **`PILOT_18_WEST`** | `PILOT_18_WEST_adjudicated_v1.json` | `44a75d262c9a128fa7ae028c02490df71cc72c10d786413a1334f1573fc1b6fd` | Rejected: Prohibited generic rationale (`"i saw the fire in the image"`); contains 4 duplicate dummy boxes `[200, 200, 300, 300]`. |

---

## 3. Original Source Annotations Protected

All 12 original human annotations in `data/reference/ds08/annotations/manual/annotator_1/` and `data/reference/ds08/annotations/manual/annotator_2/` remain 100% bit-for-bit preserved, untouched, and authoritative.
