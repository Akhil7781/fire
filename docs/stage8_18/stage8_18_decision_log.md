# STAGE 8.18 — DS08 DATASET EXPANSION: DECISION LOG & OPEN ITEMS
**Authoritative Architectural Decisions, Scientific Assumptions, and Sign-Off Requirements**

- **Document Version:** 1.0.0
- **Stage:** Stage 8.18 — DS08 Dataset Expansion Planning
- **Status:** **PENDING HUMAN REVIEW & ARCHITECTURAL SIGN-OFF**

---

## 1. Locked Decisions (Stage 8.18 Protocol)

The following architectural and scientific decisions have been locked in the Stage 8.18 planning framework:

| Decision ID | Area | Decision Summary | Rationale & Scientific Basis |
| :---: | :--- | :--- | :--- |
| **DEC-01** | **Pilot Isolation** | The 15 audited pilot chips (`ds08_pilot_v1`) are permanently designated as the **Frozen Benchmark / Calibration Set**. | With $n = 15$ (6 positive, 9 negative), splitting this cohort into train/val/test splits would cause acute sampling bias. It must remain a held-out benchmark. |
| **DEC-02** | **Class Scarcity Acknowledgment** | Rejected the previous naive 100/100/50 allocation in `ds08_sentinel2_manifest.parquet`. Adopted a 7-stratum allocation reflecting real-world scarcity. | Only 12–14 verified acute industrial fires occurred in India in 2025. Forcing 100 industrial fires would result in severe label noise and mislabeling. |
| **DEC-03** | **7-Stratum Allocation** | Stratified $N = 250$ across: 15 Acute Industrial, 30 Persistent Thermal, 55 Forest, 55 Agricultural, 40 Industrial Negatives, 40 Contextual Negatives, 15 Pilot Benchmark. | Balances positive fire diversity, rare industrial cases, and essential negative controls for false-alarm suppression. |
| **DEC-04** | **Stratified Temporal Matching** | Replaced the flat $\le 48\text{ h}$ gap with 4 temporal matching tiers (Tier 1 $\le 2\text{ h}$, Tier 2 $\le 6\text{ h}$, Tier 3 $\le 24\text{ h}$, Tier 4 $\le 48\text{ h}$). | Captures physical differences between active flaming combustion fronts, emerging smoke, and post-fire ground burn scars. |
| **DEC-05** | **Mutual Exclusion Rule** | Bounding boxes cannot simultaneously contain `NO_CLEAR_VISUAL_EVIDENCE` and positive combustion tags (`DIRECT_FIRE_VISIBLE` or `BURN_SCAR_VISIBLE`). | Permanently eliminates the logical contradiction detected during Stage 8.15 human annotation. |
| **DEC-06** | **Spatial Block Grouping** | Prohibited random uniform train/val/test splits. Enforced MGRS Tile ID blocking and $> 150\text{ km}$ spatial buffering. | Eliminates spatial autocorrelation leakage between training and evaluation partitions. |
| **DEC-07** | **Zero Synthetic Data** | Absolute ban on synthetic image generation, generative diffusion blending, or algorithmic label auto-population. | Maintains strict physical integrity for scientific publication and mission-critical deployment. |

---

## 2. Key Scientific Assumptions

1. **Sentinel-2 L2A BOA Reflectance Stability:** Assumes Copernicus Data Space Ecosystem (CDSE) Sen2Cor atmospheric correction provides consistent surface reflectance across diverse Indian atmospheres.
2. **FIRMS Centroid Positional Precision:** Assumes VIIRS 375m detection centroids are accurate within $\pm 200\text{ m}$, ensuring target features fall comfortably within the $5.12 \times 5.12\text{ km}$ chip.
3. **10m Optical Resolvability:** Assumes industrial storage tank fires and open agricultural stubble burns have physical extents $\ge 40\text{ m} \times 40\text{ m}$ ($4 \times 4$ pixels), making them visually identifiable in Sentinel-2 bands.

---

## 3. Open Questions Requiring Human Guidance

1. **Q1: CDSE API Request Budget:**
   - Downloading 235 5-band FLOAT32 GeoTIFF chips ($512 \times 512$) requires $\approx 235 \times 5.25\text{ MB} \approx 1.25\text{ GB}$ of data transfer. Does the project CDSE Copernicus account have sufficient processing units (PU) allocated for bulk extraction, or should downloads be throttled in batches of 50 chips?
2. **Q2: Double-Pass Human Labor Allocation:**
   - Double-pass manual annotation of 235 chips requires 470 individual chip reviews plus $\approx 50$ senior adjudication reviews. What is the anticipated annotator staffing schedule?
3. **Q3: Target Year Expansion (2024–2025):**
   - If clear 2025 Sentinel-2 passes over the 12 verified industrial incident sites yield fewer than 10 cloud-free scenes, is the project willing to expand the temporal window to include verified 2024 industrial disasters (e.g. Surat, Dahej, Dombivli chemical fires) to augment Stratum 1?

---

## 4. Specific Items Requiring Human Approval Before Phase 8.19

Before initiating candidate scene queries or chip downloads:
- [ ] **Approval of Stratified Allocation Table ($N = 250$):** Sign off on the 7-stratum distribution.
- [ ] **Approval of Contingency Shortfall Reallocation:** Authorize reallocating any acute industrial fire shortfall to Stratum 2 (`Other Thermal Source`).
- [ ] **Approval of Spatial 5-Fold Cross-Validation Strategy:** Confirm adoption of spatial blocking over static random splitting.
- [ ] **Authorization for Candidate Discovery:** Permit running read-only STAC queries to build `expansion_candidate_manifest.json` without downloading imagery rasters.
