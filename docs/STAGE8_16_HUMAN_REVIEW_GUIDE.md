# DS08 Stage 8.16 Human Review & Correction Guide

**Document Version:** 1.0.0  
**Stage:** Stage 8.16 — Controlled Human Adjudication Correction  
**Target User:** Senior Human Adjudicator / Reviewer  
**UI Server:** `http://localhost:8093`  

---

## 1. Objectives of This Review

During the Stage 8.15 audit, 6 disputed pilot chips were flagged for specific validation defects:
- **5 chips** contain **contradictory visual evidence flags** on one or more bounding boxes (simultaneously selecting positive fire evidence and `NO_CLEAR_VISUAL_EVIDENCE`).
- **1 chip (`PILOT_08_CENTRAL`)** was left with status **`UNRESOLVED`**, which cannot be accepted as a final dataset label.

As the human adjudicator, your role is to inspect the high-resolution Sentinel-2 imagery (RGB and SWIR) and make authoritative consensus decisions without automated interference.

---

## 2. The 6 Disputed Chips & Specific Action Required

| # | Chip ID | Location / Context | Audit Finding | Required Adjudication Action |
|---|---|---|---|---|
| 1 | **PILOT_03_NORTH** | Northern forest region | Box 1 has contradictory visual evidence | Uncheck `NO_CLEAR_VISUAL_EVIDENCE` if fire/smoke is visible, OR uncheck positive fire tags if no target is visible. |
| 2 | **PILOT_06_CENTRAL** | Central agricultural/forest boundary | Box 1 and Box 2 have contradictory visual evidence | Review each box independently. Reconcile evidence flags so positive fire tags and `NO_CLEAR_VISUAL_EVIDENCE` are not mutually checked. |
| 3 | **PILOT_08_CENTRAL** | Central agricultural tract | Status marked as `UNRESOLVED` | Make a definitive consensus decision: select either `HAS_ANNOTATIONS` (with boxes) or `NO_VISIBLE_TARGET` (zero boxes). |
| 4 | **PILOT_15_EAST** | Eastern agricultural cluster | Box 1 and Box 2 have contradictory visual evidence | Review both boxes against SWIR reflectance and smoke plume visibility. Remove contradictory evidence flags. |
| 5 | **PILOT_16_EAST** | Eastern agricultural cluster | Box 1, Box 2, and Box 3 have contradictory visual evidence | Reconcile evidence flags across all 3 boxes independently. |
| 6 | **PILOT_18_WEST** | Western scrub/forest region | Box 1 has contradictory visual evidence | Reconcile evidence flags for Box 1. |

---

## 3. Step-by-Step UI Instructions

### Step 1: Open the Correction Interface
1. Ensure the Stage 8.16 tool server is active on port `8093`.
2. Open your web browser and navigate to:
   ```
   http://localhost:8093
   ```
3. You will see the **DS08 Stage 8.16 Correction Workspace** header, an overview status bar showing completed chips (0/6 to start), and a sidebar listing the 6 chips.

---

### Step 2: Select and Inspect a Chip
1. Click on a chip from the left sidebar (e.g. `PILOT_03_NORTH`).
2. An **Audit Notice** banner will explain the specific issue detected during Stage 8.15.
3. Examine the two synchronized viewers:
   - **True Color (RGB):** Sentinel-2 Bands 4-3-2 (red, green, blue). Look for visible smoke plumes, active flames, and vegetation contrast.
   - **Short-Wave Infrared (SWIR):** Sentinel-2 Bands 12-8A-4 (SWIR-2, NIR, Red). Look for intense orange/red thermal hotspots and dark charcoal burn scars.
   - **FIRMS Detection Marker:** The red crosshair shows the VIIRS/MODIS thermal anomaly centroid. (Note: FIRMS is contextual guidance; satellite pixel geometry must be grounded in Sentinel-2 imagery).

---

### Step 3: Resolve Bounding Box Visual Evidence (Chips 1, 2, 4, 5, 6)
For each bounding box card:
1. Examine the **Visual Evidence Flags** checkboxes:
   - `DIRECT_FIRE_VISIBLE`
   - `SMOKE_PLUME`
   - `BURN_SCAR_VISIBLE`
   - `SWIR_HOTSPOT`
   - `NO_CLEAR_VISUAL_EVIDENCE`
2. **Eliminate Contradictions:**
   - If you can clearly observe fire activity (SWIR hotspot, smoke plume, or flame front), ensure `NO_CLEAR_VISUAL_EVIDENCE` is **unchecked**.
   - If there is no discernible visual manifestation in the Sentinel-2 bands, uncheck all positive fire tags and check `NO_CLEAR_VISUAL_EVIDENCE`.
3. If necessary, adjust the class (`FOREST_FIRE`, `AGRICULTURAL_FIRE`, `INDUSTRIAL_FIRE`, `OTHER_THERMAL`), visibility, or confidence ratings.

---

### Step 4: Resolve PILOT_08_CENTRAL Definitive Status
For `PILOT_08_CENTRAL`:
1. Under **Observation Status**, choose one of the two allowed options:
   - **`HAS_ANNOTATIONS`**: Target is discernible. Provide bounding box coordinates and attributes.
   - **`NO_VISIBLE_TARGET`**: No valid fire or thermal activity is visible in the chip imagery. All bounding boxes will be removed.
2. Note: The status `UNRESOLVED` is blocked by the UI and the backend validator.

---

### Step 5: Enter Substantive Rationale
In the **Correction Rationale** text area:
- Describe the specific visual features justifying your decision (e.g., *"Distinct B12 SWIR reflectance anomaly located at pixel [154, 210] with dispersing smoke plume to the northeast; unselected NO_CLEAR_VISUAL_EVIDENCE to resolve contradiction."*).
- **Prohibited:** Short or generic statements like *"saw the fire"*, *"agreed with a1"*, *"fixed"*, or *"dummy"*. The system requires at least 15 characters of observable detail.

---

### Step 6: Preview Diff & Confirm
1. Click **"Preview Diff"** to review the exact field-by-field modifications before saving.
2. Check the mandatory confirmation checkbox:
   > ☑ *I confirm that I have reviewed the Sentinel-2 imagery and explicitly approve these corrections.*
3. Click **"Save Correction Record"**.
4. A success toast with the unique record SHA-256 fingerprint will appear, and the chip in the sidebar will be marked with a green checkmark (`CORRECTED`).

---

### Step 7: Repeat for All 6 Chips
Continue until the status bar displays **6 / 6 Chips Corrected**.

---

## 4. Storage & Audit Trail Integrity

- **Original Records Protected:** Original Stage 8.15 adjudication files in `data/reference/ds08/annotations/adjudication/review/` remain **byte-for-byte identical**.
- **Correction Files:** Output records are written to:
  `data/reference/ds08/annotations/adjudication/corrections/{chip_id}_corrected_v2.json`.
- **Append-Only Audit Log:** Every action is recorded in:
  `data/reference/ds08/annotations/adjudication/corrections/stage8_16_audit_log.jsonl`.

---

## 5. Next Steps

Once you have completed all 6 corrections:
1. Notify the assistant in the chat that all 6 chips have been reviewed and corrected.
2. The assistant will verify the saved files, audit log, and immutability hashes.
3. The pipeline will then proceed to read-only persistence audit and dataset freezing.
