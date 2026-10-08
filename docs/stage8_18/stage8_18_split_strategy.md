# STAGE 8.18 — DS08 DATASET EXPANSION: SPLIT STRATEGY
**Spatial Grouping, Leakage Prevention, and Evaluation Partitioning for the Expanded DS08 Dataset**

- **Document Version:** 1.0.0
- **Stage:** Stage 8.18 — DS08 Dataset Expansion Planning
- **Status:** **DRAFT SPECIFICATION — LOCKED FOR HUMAN REVIEW**
- **Target Size:** $N = 250$ Level-2A Sentinel-2 Chips

---

## 1. Spatial & Temporal Leakage Risks in Satellite Deep Learning

A pervasive source of inflated performance and scientific failure in remote sensing models is **spatial autocorrelation leakage**.

### Mechanisms of Leakage:
1. **Spatial Proximity Leakage:** Two chips extracted from adjacent areas within the same $100 \times 100\text{ km}$ Sentinel-2 tile share near-identical soil backgrounds, vegetation canopy, atmospheric aerosols, and sun angle. If one chip is assigned to the training set and the adjacent chip to the test set, the model memorizes local background texture rather than learning generalizable fire combustion features.
2. **Temporal Overpass Leakage:** Two chips acquired along the same Sentinel-2 orbital swath on the exact same date and minute share identical radiometric calibration and atmospheric conditions.
3. **Facility / Asset Memorization:** If an industrial facility (e.g. Jamnagar Refinery) appears in both the training set and test set, the model memorizes specific building layouts rather than general industrial fire characteristics.

---

## 2. Pilot Cohort Policy: Non-Splitting Invariant

> [!CRITICAL]
> **DO NOT PARTITION THE 15-CHIP PILOT COHORT.**  
> - The 15 audited pilot chips (`ds08_pilot_v1`) must **NOT** be partitioned into train, validation, or test splits.
> - **Scientific Rationale:** With only 15 chips (6 positive, 9 negative) and exactly 1 instance of agricultural fire, splitting this pilot into standard 70/15/15 partitions would yield validation or test sets with zero positive fire examples or zero agricultural examples.
> - **Permanent Role:** The 15 pilot chips are designated as the **Frozen DS08 Calibration & Benchmark Evaluation Set**. They are held out completely from training.

---

## 3. Evaluation of the 250-Chip Expanded Cohort

### Is $N = 250$ Sufficient for a Standard Train / Validation / Test Split?

When expanding to $N = 250$ chips (15 pilot chips + 235 new expansion chips), class distribution imposes critical statistical constraints:

| Stratum / Class | Total Available (Est.) | Train Partition ($\sim 70\%$) | Val Partition ($\sim 15\%$) | Test Partition ($\sim 15\%$) | Statistical Viability Assessment |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Stratum 1 (Acute Industrial Fire)** | $\approx 15\text{ chips}$ | $\sim 11\text{ chips}$ | $\sim 2\text{ chips}$ | $\sim 2\text{ chips}$ | **Severely constrained.** 2 test chips cannot yield statistically reliable precision/recall curves. |
| **Stratum 2 (Persistent Thermal Source)**| $\approx 30\text{ chips}$ | $\sim 21\text{ chips}$ | $\sim 4\text{ chips}$ | $\sim 5\text{ chips}$ | **Marginal.** Sufficient for baseline detection, limited diversity. |
| **Stratum 3 (Forest Wildfires)** | $\approx 55\text{ chips}$ | $\sim 39\text{ chips}$ | $\sim 8\text{ chips}$ | $\sim 8\text{ chips}$ | **Adequate.** Good representation across diverse forest biomes. |
| **Stratum 4 (Agricultural Crop Burns)** | $\approx 55\text{ chips}$ | $\sim 39\text{ chips}$ | $\sim 8\text{ chips}$ | $\sim 8\text{ chips}$ | **Adequate.** Captures regional harvest burning regimes. |
| **Stratum 5 (Industrial Negatives)** | $\approx 40\text{ chips}$ | $\sim 28\text{ chips}$ | $\sim 6\text{ chips}$ | $\sim 6\text{ chips}$ | **Adequate.** Robust false-positive suppression baseline. |
| **Stratum 6 (Contextual Negatives)** | $\approx 40\text{ chips}$ | $\sim 28\text{ chips}$ | $\sim 6\text{ chips}$ | $\sim 6\text{ chips}$ | **Adequate.** Diverse natural and agrarian negative controls. |
| **Stratum 7 (Pilot Benchmark Set)** | **15 chips** | **0 chips (Held Out)**| **0 chips** | **15 chips (Benchmark)**| **Authoritative Benchmark Set.** |

### Scientific Conclusion:
A simple 3-way train/val/test split across 235 expansion chips is **statistically fragile for rare classes** (specifically acute industrial fires). Therefore, the project must adopt a **Staged Cross-Validation and Regional Holdout Strategy**.

---

## 4. Proposed Staged Partitioning Strategy

### Strategy A: Spatial Block / Tile-Level Grouping (Primary Split Engine)

All 235 expansion chips are assigned to partitions using **Grouped Spatial Blocking**:
1. **Group Key:** The primary group key is the Sentinel-2 **MGRS Tile ID** ($100 \times 100\text{ km}$).
2. **Buffer Distance:** Any two chips from different tiles that are separated by $< 150.0\text{ km}$ geodesic distance are clustered into the same spatial block.
3. **Partition Assignment:** Entire spatial blocks (containing 1 to 5 chips) are assigned to Train, Validation, or Test. Under no circumstances may chips from the same spatial block be split across training and evaluation partitions.

### Strategy B: Spatial 5-Fold Cross-Validation (Model Development Phase)
To maximize the utility of the scarce acute industrial fire chips ($n \approx 15$):
- Instead of relying on a single static test set containing only 2 industrial fire chips, the 235 chips are partitioned into **5 spatially disjoint folds** (Spatial K-Fold).
- In each fold iteration, 4 folds ($\approx 188$ chips) train the model, and 1 spatial fold ($\approx 47$ chips, containing 3 industrial fire chips) evaluates out-of-fold generalization.
- Overall performance is reported as the mean and standard error across all 5 out-of-fold evaluations.

### Strategy C: Geographic Region Holdout (Generalization Stress Test)
- One complete geographic region (e.g. **WEST: Gujarat/Rajasthan arid and coastal petrochemical corridor**, $\approx 40$ chips) is held out completely during initial model tuning.
- Models trained exclusively on North, Central, South, and East imagery are tested on the West holdout to measure out-of-domain geographic transfer without spatial leakage.

---

## 5. Mandatory Verification of Any Future Split

Before any split is finalized in Stage 9+, a read-only split verification audit must prove:
- `MAX_SPATIAL_INTERSECTION`: $0.0\text{ km}^2$ between train and test footprints.
- `MIN_INTER_SPLIT_SEPARATION`: $\ge 150.0\text{ km}$ between any training chip and any test chip.
- `TILE_DISJOINTNESS`: $\text{Tiles}(\text{Train}) \cap \text{Tiles}(\text{Test}) = \emptyset$.
- `PILOT_BENCHMARK_ISOLATION`: 15 pilot chips must have $0\%$ overlap with training chips.
