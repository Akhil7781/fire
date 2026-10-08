# STAGE 8.10B — DS08 PILOT ADJUDICATION & PROTOCOL VALIDATION SUMMARY

**Adjudication Timestamp:** 2026-09-29T16:08:22.906879+00:00  
**Adjudication Panel:** SENIOR_EXPERT_PANEL  
**Adjudicated Chips:** 3 (`PILOT_01_NORTH`, `PILOT_13_EAST`, `PILOT_17_WEST`)  
**Protocol Status:** **`NO_PROTOCOL_CHANGE_REQUIRED`** (Guidelines retained at **`v1.0`**)  

---

## 1. Separation of Pre-Adjudication Agreement vs Post-Adjudication Final Labels

> [!IMPORTANT]
> **Strict Provenance Separation:** Pre-adjudication inter-annotator metrics measure independent human agreement across the draft annotations. Post-adjudication final labels represent the consensus ground truth settled by expert review. Adjudication does **NOT** retroactively alter the initial double-blind agreement rate.

| Metric Type | Metric Name | Value | Context |
| :--- | :--- | :---: | :--- |
| **Pre-Adjudication** | Raw Class Agreement | **60.0%** (3/5) | Independent double-blind Pass 1 vs Pass 2. |
| **Pre-Adjudication** | Cohen's Kappa ($\kappa$) | **0.4737** | Moderate agreement across 4 categories ($n=5$). |
| **Pre-Adjudication** | Mean Matched IoU | **0.7141** | High spatial boundary consistency for matched boxes. |
| **Post-Adjudication** | Final Adjudicated Chips | **3 chips** | Disputed chips resolved by senior panel. |
| **Post-Adjudication** | Final Concordant Chips | **2 chips** | `PILOT_05_CENTRAL` (NO_TARGET) & `PILOT_09_SOUTH` (Forest Fire). |
| **Post-Adjudication** | Final Pilot Labels Generated | **3 in `final/`** | Strictly zero final files created for unadjudicated chips. |

---

## 2. Adjudication Decisions for Disputed Chips

### A. `PILOT_01_NORTH`
- **Dispute:** Annotator 1 assigned `Agricultural Fire` to an off-center burn plot (`[445, 320, 495, 365]`); Annotator 2 assigned `NO_VISIBLE_TARGET` at center.
- **Investigation:** The southeastern burn plot is physically real ($B12 = 1.019$), but located **2,308.2 meters (2.31 km)** from the FIRMS detection coordinate `[256, 256]` across multiple distinct field plots and road networks. The candidate detection reported FRP = 0.6 MW (low intensity), which cannot be associated with a physical fire 2.31 km away. The central 500m radius is clear fallow cropland with zero fire evidence.
- **Final Decision:** **`NO_VISIBLE_TARGET`** (`annotations = []`).
- **FIRMS Relationship:** `OUTSIDE_VISIBLE_OBJECT` (relative to the distant southeastern plot).
- **Adjudication Reasoning:** Low-intensity thermal anomalies cannot be associated with independent physical burning over 2 km away. The chip correctly represents a clear observation where no target corresponds to the candidate detection.

### B. `PILOT_13_EAST`
- **Dispute:** Annotator 1 assigned `Forest Fire` to a dark canopy patch (`[230, 230, 285, 285]`); Annotator 2 assigned `UNRESOLVED` (`[225, 225, 290, 290]`).
- **Investigation:** The terrain is steep montane relief in Manipur hills. The localized dark canopy patch lacks elevated SWIR reflectance (chip-wide B12 max is only 0.4484) and visible smoke. Single-date 10m Level-2A imagery cannot unequivocally differentiate deep aspect-driven terrain shadow / ravine canopy from a cold vegetative burn scar without multi-temporal baseline imagery.
- **Final Decision:** **`UNRESOLVED`** (`class_id: 0`, box `[225, 225, 290, 290]`, geometry confidence `LOW`, source confidence `LOW`).
- **FIRMS Relationship:** `INSIDE_OBJECT`.
- **Adjudication Reasoning:** Under Rule 5 and Section 6 of Guidelines v1.0, ambiguous observations must never be forced into a fire class. Assigning UNRESOLVED prevents terrain shadow false positives.

### C. `PILOT_17_WEST`
- **Dispute:** Class and box were already concordant (`Agricultural Fire`, IoU = 0.7042). Minor discrepancy in secondary evidence tags (`BURN_SCAR_VISIBLE` included by A1, omitted by A2).
- **Investigation:** Clear active crop residue burning plot in furrowed agricultural plain; peak B12 reflectance reaches 1.4082, accompanied by visible smoke and a fresh charred field-stubble pattern.
- **Final Decision:** **`Agricultural Fire`** (`class_id: 3`, harmonized consensus box `[166, 243, 199, 269]`, geometry confidence `HIGH`, source confidence `HIGH`).
- **Visual Evidence:** `["DIRECT_FIRE_VISIBLE", "CROPLAND_CONTEXT_VISIBLE", "BURN_SCAR_VISIBLE"]`.
- **FIRMS Relationship:** `NEAR_OBJECT` ($775\text{ m}$ west of FIRMS coordinate `[256, 256]`).
- **Adjudication Reasoning:** High-confidence agricultural fire; consensus bounding box and comprehensive multi-label evidence tags harmonized.

---

## 3. Protocol Proposals Validation

### Proposal A: 750 m Maximum FIRMS Association Radius
- **Evaluation:** **`DEFER`**
- **Policy Code:** **`ASSOCIATION_RADIUS_POLICY = NOT_YET_FROZEN`**
- **Scientific Rationale:** A universal rigid 750m threshold is an ungrounded heuristic. Spatial uncertainty varies with satellite scan angle (VIIRS 375m expands to ~800m at scan edge; MODIS 1km expands to 2km), geolocation parallax, and wind-driven smoke/burn propagation. Spatial association must be supported by observable visual target continuity and contextual relationship; no universal radius is frozen until validated on a larger statistical sample.

### Proposal B: Mandatory Montane B12 > 0.5 Threshold
- **Evaluation:** **`REJECT`** (as a mandatory threshold)
- **Policy Code:** **`MONTANE_B12_THRESHOLD_POLICY = REJECTED_AS_MANDATORY_CRITERION`**
- **Scientific Rationale:** A hard radiometric threshold ($B12 > 0.5$) is physically unsound. Real smoldering fires, cold post-fire scars, and canopy-occluded burns frequently exhibit $B12 \le 0.50$. In `PILOT_13_EAST`, the target was adjudicated as `UNRESOLVED` because of single-date optical ambiguity between montane terrain shadow and vegetative disturbance, which is natively handled by the existing `UNRESOLVED` rule without introducing an unphysical radiometric cutoff.

### Protocol Versioning Outcome
- **Status:** **`NO_PROTOCOL_CHANGE_REQUIRED`**
- **Active Version:** **`v1.0`** (retained without modification; formal Draft-07 schema and guidelines v1.0 remain fully authoritative).

---

## 4. Final Adjudicated Files Created

The following three files were validated and placed into `data/reference/ds08/annotations/final/`:
1. `PILOT_01_NORTH_adjudicated_v1.json` (`NO_VISIBLE_TARGET`)
2. `PILOT_13_EAST_adjudicated_v1.json` (`UNRESOLVED`)
3. `PILOT_17_WEST_adjudicated_v1.json` (`Agricultural Fire`)

> [!IMPORTANT]
> Exactly 3 files exist in `data/reference/ds08/annotations/final/`. Zero final files were created for unadjudicated chips.