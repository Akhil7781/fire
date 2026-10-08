# STAGE 8.18A — TEMPORAL MATCHING TIERS & PHYSICAL EVENT PHASES SPECIFICATION
**Separation of Active-Event Combustion vs. Post-Event Burn Scars**

- **Document Version:** 2.0.0
- **Stage:** Stage 8.18A — Protocol Review & Sign-Off Preparation
- **Status:** **REVISED SPECIFICATION — LOCKED FOR HUMAN REVIEW**
- **Domain:** Temporal Correlation between Satellite Overpass ($t_{\text{S2}}$) and Ground Truth Event ($t_{\text{Event}}$)

---

## 1. Problem Statement & Audit Finding

In Stage 8.18, candidate image matching established four temporal proximity tiers based solely on absolute delta time $|\Delta t| = |t_{\text{S2}} - t_{\text{Event}}|$, ranging from $\le 1\text{ hour}$ up to $48\text{ hours}$.

**Defect in Stage 8.18:**
The specification did not distinguish between **active combustion** (flaming/smoldering) and **post-combustion damage** (burn scars, ash deposits, facility destruction).
- At $\Delta t > 6\text{ hours}$, rapid industrial fires or agricultural stubble fires have frequently ended.
- An overpass taken 18 hours after a factory fire captures post-event wreckage or cooling char, not an active fire.
- Allowing annotators to label `DIRECT_FIRE_VISIBLE` on post-event imagery creates visual contradictions and corrupts training labels.
- Evaluating an active fire detection model on post-event imagery without distinction creates flawed benchmark metrics (false penalty for not detecting an extinguished fire).

---

## 2. Formal Separation of Physical Event Phases

Every candidate optical chip in DS08 must be classified into one of three mutually exclusive physical event phases:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        PHYSICAL EVENT PHASES                           │
├─────────────────────┬──────────────────────────┬───────────────────────┤
│ 1. ACTIVE_COMBUSTION│ 2. POST_COMBUSTION_SCAR  │ 3. PRE_EVENT_BASELINE │
│ Flaming / Smoldering│ Char, Ash, Burn Scar     │ Unburnt, Normal State │
│ Tiers 1 & 2         │ Tiers 3 & 4              │ Negative Control      │
└─────────────────────┴──────────────────────────┴───────────────────────┘
```

### 2.1 Phase 1: `ACTIVE_COMBUSTION`
- **Definition:** Satellite overpass captures active flaming fronts, intense smoldering combustion, or active industrial flaring/combustion.
- **Physical Characteristics:**
  - Distinct SWIR reflectance saturation (Sentinel-2 Band 12 at $2.19\,\mu\text{m}$ and Band 11 at $1.61\,\mu\text{m}$).
  - Coincident smoke plume drifting downwind from a localized point or front.
  - Active high Fire Radiative Power (FRP) on FIRMS VIIRS/MODIS.
- **Permissible Evidence Tags:**
  - `DIRECT_FIRE_VISIBLE` (Allowed if flame/hotspot visible)
  - `SMOKE_PLUME_PRESENT` (Allowed if plume visible)
  - `SWIR_ANOMALY_PRESENT` (Mandatory if SWIR saturated)
- **Temporal Window:** Typically $|\Delta t| \le 6.0\text{ hours}$ from verified ignition/hotspot report.

### 2.2 Phase 2: `POST_COMBUSTION_SCAR`
- **Definition:** Satellite overpass captures the aftermath of an extinguished or controlled fire incident.
- **Physical Characteristics:**
  - Distinct surface charring, ash deposition, darkened ground, loss of chlorophyll (sharp drop in Sentinel-2 Band 8 NIR).
  - Absence of active high-temperature thermal saturation in SWIR.
  - Absence of dynamic smoke plume originating from the site.
- **Strict Evidence Tagging Rules:**
  - `DIRECT_FIRE_VISIBLE`: **STRICTLY PROHIBITED** (unless verified active smoldering embers remain with SWIR saturation).
  - `SMOKE_PLUME_PRESENT`: **STRICTLY PROHIBITED** (cooling steam or dust must not be tagged as fire smoke plume).
  - `BURN_SCAR_PRESENT`: **MANDATORY** for forest/agricultural aftermath.
  - `DESTRUCTION_DEBRIS_VISIBLE`: Permitted for structural industrial collapse.
- **Temporal Window:** $6.0\text{ hours} < |\Delta t| \le 48.0\text{ hours}$.

### 2.3 Phase 3: `PRE_EVENT_BASELINE`
- **Definition:** Satellite overpass captured before ignition (or during normal operational state). Used as negative controls and temporal diff baseline.

---

## 3. Revised Temporal Tiers Specification

| Tier Name | Temporal Offset ($|\Delta t|$) | Primary Event Phase | Intended Sensor Correlation | Permissible Benchmark Use |
| :--- | :--- | :--- | :--- | :--- |
| **Tier 1: Coincident** | $|\Delta t| \le 1.0\text{ hour}$ | `ACTIVE_COMBUSTION` | VIIRS/MODIS overpass within 60 min of Sentinel-2 | Primary Active Fire & Smoke Detection Benchmark |
| **Tier 2: Near-Coincident** | $1.0\text{h} < |\Delta t| \le 6.0\text{ hours}$ | `ACTIVE_COMBUSTION` (or Late Smoldering) | Same diurnal cycle; active containment ongoing | Active Fire & Smoke Detection Benchmark |
| **Tier 3: Same-Day Post** | $6.0\text{h} < |\Delta t| \le 24.0\text{ hours}$ | `POST_COMBUSTION_SCAR` | Evening-to-morning overpass; fire extinguished | Burn Scar & Damage Assessment Benchmark; Negative Control for Flame Detectors |
| **Tier 4: Next-Day Post** | $24.0\text{h} < |\Delta t| \le 48.0\text{ hours}$ | `POST_COMBUSTION_SCAR` | Next orbital cycle; post-fire residual assessment | Burn Scar & Environmental Impact Benchmark; Negative Control for Flame Detectors |

---

## 4. Usage in Annotation & Model Evaluation

### 4.1 Annotation Invariants
1. The annotation interface must automatically populate `suggested_phase` based on $|\Delta t|$, but require human annotator confirmation of `temporal_phase` (`ACTIVE_COMBUSTION` vs `POST_COMBUSTION_SCAR`).
2. If `temporal_phase == "POST_COMBUSTION_SCAR"`, the UI validation engine must **disable and reject `DIRECT_FIRE_VISIBLE`**, preventing evidence contradictions.
3. If an annotator attempts to select `DIRECT_FIRE_VISIBLE` on a Tier 3 or Tier 4 chip, an explicit override justification must be recorded confirming unextinguished flaming combustion with proof of SWIR saturation.

### 4.2 Benchmark Evaluation Separation
To avoid corrupting model evaluation metrics, test sets must be split into distinct evaluation suites:

1. **Suite A — Active Fire & Smoke Detection Evaluation:**
   - Evaluated **only** on Tier 1 & Tier 2 (`ACTIVE_COMBUSTION`) chips.
   - Models: YOLOv8n-Fire/Smoke, SWIR thresholding detectors, thermal anomaly localization.
   - Targets: Bounding boxes with `DIRECT_FIRE_VISIBLE` and `SMOKE_PLUME_PRESENT`.

2. **Suite B — Burn Scar & Structural Damage Evaluation:**
   - Evaluated **only** on Tier 3 & Tier 4 (`POST_COMBUSTION_SCAR`) chips.
   - Models: Semantic segmentation (e.g., U-Net / SAM), Normalized Burn Ratio (NBR) deltas.
   - Targets: Bounding boxes or masks representing charred surface area.

3. **Cross-Evaluation Rule:**
   - When running Suite A (Active Fire Detector) across the full 250-chip dataset, Tier 3 & 4 chips must be scored under negative-class background rules. A model predicting no flame on a Tier 4 burn scar is scored as **True Negative**, not False Negative.
