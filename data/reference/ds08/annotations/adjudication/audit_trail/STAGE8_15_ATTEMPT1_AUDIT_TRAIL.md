# STAGE 8.15 — ADJUDICATION AUDIT TRAIL RECORD (ATTEMPT 1)
**Immutable Snapshot of Initial Stage 8.15 Adjudication Submissions**

- **Snapshot Timestamp (UTC):** `2026-10-02T05:37:00Z`
- **Snapshot Directory:** [`data/reference/ds08/annotations/adjudication/audit_trail/stage8_15_attempt1/`](file:///d:/DATA%20PREPROCESSING/data/reference/ds08/annotations/adjudication/audit_trail/stage8_15_attempt1/)
- **Protocol:** [`DS08_ANNOTATION_GUIDELINES_v1.md`](file:///d:/DATA%20PREPROCESSING/data/reference/ds08/annotations/guidelines/DS08_ANNOTATION_GUIDELINES_v1.md)
- **Status:** **PRESERVED AS IMMUTABLE AUDIT TRAIL (READ-ONLY BASELINE)**

---

## 1. Audit Trail Purpose & Integrity Guarantee

In accordance with scientific provenance requirements, the initial six human adjudication submissions from Stage 8.15 have been preserved bit-for-bit. These files record the initial human review state prior to controlled human correction of visual evidence contradictions and resolution of `PILOT_08_CENTRAL`.

> [!NOTE]
> These files are retained permanently in this directory for auditability and must **NEVER** be overwritten, modified, or removed.

---

## 2. Preserved Files Inventory & SHA-256 Hashes

| Chip ID | Filename | Size | Original Submission UTC | SHA-256 Hash | Issue Requiring Correction |
| :--- | :--- | :---: | :---: | :--- | :--- |
| **`PILOT_03_NORTH`** | `PILOT_03_NORTH_adjudicated_v1.json` | 9,226 B | 2026-10-02T05:13:57Z | `dd1d1b427796a1bda6903d71a2d17841c215d2b6978463fb0560900b049aafaa` | Evidence contradiction (`DIRECT_FIRE_VISIBLE` + `NO_CLEAR_VISUAL_EVIDENCE`) |
| **`PILOT_06_CENTRAL`** | `PILOT_06_CENTRAL_adjudicated_v1.json` | 11,367 B | 2026-10-02T05:15:40Z | `7b0cbb8eac28d2387c6f197e175f39f4653148d0e41006637864280138a949c9` | Evidence contradiction (`DIRECT_FIRE_VISIBLE` + `NO_CLEAR_VISUAL_EVIDENCE`) |
| **`PILOT_08_CENTRAL`** | `PILOT_08_CENTRAL_adjudicated_v1.json` | 4,537 B | 2026-10-02T05:17:24Z | `3ad0384f37a4121950f1523ca711ca030f2028c20091934e7495d99b97a214d7` | Non-definitive status (`observation_status: UNRESOLVED`) |
| **`PILOT_15_EAST`** | `PILOT_15_EAST_adjudicated_v1.json` | 13,014 B | 2026-10-02T05:18:55Z | `1d4ba7f5ee6e16402533a58d6910503af13abffeca51de83e44015cda60abe3c` | Evidence contradiction (`DIRECT_FIRE_VISIBLE` + `NO_CLEAR_VISUAL_EVIDENCE`) |
| **`PILOT_16_EAST`** | `PILOT_16_EAST_adjudicated_v1.json` | 15,805 B | 2026-10-02T05:21:15Z | `5986b43675904a91d53184e3b57b67d8e759e2d6f8b7be3af483b3400af02264` | Evidence contradiction (`DIRECT_FIRE_VISIBLE` + `NO_CLEAR_VISUAL_EVIDENCE`) |
| **`PILOT_18_WEST`** | `PILOT_18_WEST_adjudicated_v1.json` | 7,720 B | 2026-10-02T05:23:30Z | `a88d245b12e0e6eddc833926d4928927b8835ee3b25ccbbb963fc9e844f51674` | Evidence contradiction (`DIRECT_FIRE_VISIBLE` + `NO_CLEAR_VISUAL_EVIDENCE`) |

---

## 3. Preservation Invariants

- **A1/A2 Workspace Invariance:** Source workspaces `data/reference/ds08/annotations/manual/annotator_1/` and `annotator_2/` remain 100% untouched.
- **Quarantine Invariance:** Quarantined placeholder files in `data/reference/ds08/annotations/quarantine/stage8_15_invalid/` remain segregated.
- **Model Invariance:** Zero model training, fine-tuning, or embedding generation was performed.
