# Stage 8.29 Persistent Source Registry Provenance Audit

**Audited Artifact:** `data/reference/ds08/manifests/stage8_25/persistent_source_manifest.json`  
**Dataset Reference:** `data/interim/ds08_stage8_25_physical_events.parquet`  
**Audit Date:** October 4, 2026  
**Auditor:** Autonomous Scientific AI (Adversarial Audit Team)

---

## 1. Executive Provenance Finding

The persistent source registry (`persistent_source_manifest.json`) contains 52 entries (`PER_SRC_01` through `PER_SRC_52`). 

Cross-referencing this manifest against the physical events dataset (`ds08_stage8_25_physical_events.parquet`) reveals that:
1. **100% Identification Overlap:** All 52 physical persistent events in the dataset (`EVT_825_PER_PER_SRC_01` to `EVT_825_PER_PER_SRC_52`) correspond directly to the 52 entries in `persistent_source_manifest.json`.
2. **Direct Test Cohort Overlap:** Exactly 10 entries in `persistent_source_manifest.json` correspond to the 10 persistent events in the frozen 2026 independent test set (`EVT_825_PER_PER_SRC_01`, `02`, `03`, `06`, `21`, `25`, `26`, `47`, `49`, `52`).
3. **Target Event Location Equality:** The coordinates in the manifest are identical to the centroid coordinates of the evaluated test events (mean distance = $34.4\text{ meters}$, with slight offset due to FIRMS pixel centroid averaging).
4. **Project-Derived Origin:** The metadata of `persistent_source_manifest.json` specifies `"version": "1.0.0", "stage": "8.25"`. The manifest was created during Stage 8.25 as the seed definition for the persistent thermal source class.
5. **Target Proxy Mechanism:** In Stage 8.28, when the explicit code defect `is_known_persistent = (cid == 3)` was removed, it was replaced by computing the Haversine distance to the nearest entry in `persistent_source_manifest.json`. Because the test events themselves are in `persistent_source_manifest.json`, the feature `within_1km_persistent_registry` evaluates to $1.0$ for all 10 persistent test events and $0.0$ for all 18 acute test events (minimum distance to acute fire = $79.5\text{ km}$).

Therefore:
$$\text{Class} == \text{Persistent} \iff \text{dist\_to\_persistent\_registry\_km} \le 1.0\text{ km} \quad (r = 1.0000)$$
**The persistent source registry in its current form acts as a direct spatial target proxy for the persistent thermal source class.**

---

## 2. Complete Provenance Classification (All 52 Sources)

| Persistent ID | Source Name | Category | Evidence Source | Split | Provenance Classification |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `PER_SRC_01` | Barren Island Active Volcano | Volcano | Smithsonian GVP & GSI | Test (2026) | **TEST_DERIVED / PROJECT_DERIVED** |
| `PER_SRC_02` | ONGC Mumbai High North Flare | Gas Flaring | VIIRS Nightfire (VNF) | Test (2026) | **TEST_DERIVED / PROJECT_DERIVED** |
| `PER_SRC_03` | ONGC Mumbai High South Flare | Gas Flaring | VIIRS Nightfire (VNF) | Test (2026) | **TEST_DERIVED / PROJECT_DERIVED** |
| `PER_SRC_04` | ONGC Neelam & Heera Platform | Gas Flaring | VIIRS Nightfire (VNF) | Val (2025) | VAL_DERIVED / PROJECT_DERIVED |
| `PER_SRC_05` | ONGC Hazira Gas Processing Plant | Gas Flaring | VIIRS Nightfire (VNF) | Val (2025) | VAL_DERIVED / PROJECT_DERIVED |
| `PER_SRC_06` | Reliance KG-D6 Offshore Complex | Gas Flaring | VIIRS Nightfire (VNF) | Test (2026) | **TEST_DERIVED / PROJECT_DERIVED** |
| `PER_SRC_07` | OIL Duliajan Gas Flare Complex | Gas Flaring | VIIRS Nightfire (VNF) | Train (2024) | TRAIN_DERIVED / PROJECT_DERIVED |
| `PER_SRC_08` | Jharia Coal Field - Jalgora Fire | Coal Seam Fire | CIMFR & CMPDI Remote Sensing | Val (2025) | VAL_DERIVED / PROJECT_DERIVED |
| `PER_SRC_09` | Jharia Coal Field - Kusunda Mine | Coal Seam Fire | CIMFR & CMPDI Remote Sensing | Train (2024) | TRAIN_DERIVED / PROJECT_DERIVED |
| `PER_SRC_10` | Jharia Coal Field - Lodna Fire Area | Coal Seam Fire | CIMFR & CMPDI Remote Sensing | Train (2024) | TRAIN_DERIVED / PROJECT_DERIVED |
| `PER_SRC_11` | Raniganj Coalfield - Nimcha Pit | Coal Seam Fire | CMPDI & ECL Environmental Reports | Train (2024) | TRAIN_DERIVED / PROJECT_DERIVED |
| `PER_SRC_12` | Raniganj Coalfield - Kenda Fire | Coal Seam Fire | CMPDI & ECL Environmental Reports | Train (2024) | TRAIN_DERIVED / PROJECT_DERIVED |
| `PER_SRC_13` | Singrauli Coalfield - Jayant OCP | Coal Smolder | NCL Environmental Monitoring | Train (2024) | TRAIN_DERIVED / PROJECT_DERIVED |
| `PER_SRC_14` | Singrauli Coalfield - Dudhichua OCP | Coal Smolder | NCL Environmental Monitoring | Train (2024) | TRAIN_DERIVED / PROJECT_DERIVED |
| `PER_SRC_15` | Korba Coalfield - Gevra Mega OCP | Coal Spontaneous | SECL Environmental Baseline | Train (2024) | TRAIN_DERIVED / PROJECT_DERIVED |
| `PER_SRC_16` | Korba Coalfield - Kusmunda OCP | Coal Spontaneous | SECL Environmental Baseline | Train (2024) | TRAIN_DERIVED / PROJECT_DERIVED |
| `PER_SRC_17` | Talcher Coalfield - Ananta OCP | Coal Spontaneous | MCL Environmental Records | Train (2024) | TRAIN_DERIVED / PROJECT_DERIVED |
| `PER_SRC_18` | Talcher Coalfield - Bharatpur OCP | Coal Spontaneous | MCL Environmental Records | Train (2024) | TRAIN_DERIVED / PROJECT_DERIVED |
| `PER_SRC_19` | IOCL Paradip Refinery Flare | Industrial Heat | CPCB Online Monitoring & VNF | Train (2024) | TRAIN_DERIVED / PROJECT_DERIVED |
| `PER_SRC_20` | IOCL Koyali Refinery Flare | Industrial Heat | CPCB Online Monitoring & VNF | Train (2024) | TRAIN_DERIVED / PROJECT_DERIVED |
| `PER_SRC_21` | BPCL Mumbai Refinery Process Flare | Industrial Heat | CPCB Online Monitoring & VNF | Test (2026) | **TEST_DERIVED / PROJECT_DERIVED** |
| `PER_SRC_22` | HPCL Visakh Refinery Flare | Industrial Heat | CPCB Online Monitoring & VNF | Train (2024) | TRAIN_DERIVED / PROJECT_DERIVED |
| `PER_SRC_23` | Tata Steel Jamshedpur Works Flare | Industrial Heat | CPCB Industrial Emission Registry | Train (2024) | TRAIN_DERIVED / PROJECT_DERIVED |
| `PER_SRC_24` | SAIL Bhilai Steel Plant Complex | Industrial Heat | CPCB Industrial Emission Registry | Train (2024) | TRAIN_DERIVED / PROJECT_DERIVED |
| `PER_SRC_25` | SAIL Bokaro Steel Plant Slag Pit | Industrial Heat | CPCB Industrial Emission Registry | Test (2026) | **TEST_DERIVED / PROJECT_DERIVED** |
| `PER_SRC_26` | JSW Steel Vijayanagar Works | Industrial Heat | CPCB Industrial Emission Registry | Test (2026) | **TEST_DERIVED / PROJECT_DERIVED** |
| `PER_SRC_27` | NTPC Vindhyachal Super TPP | Coal Ash Thermal | CEA Power Station Database | Train (2024) | TRAIN_DERIVED / PROJECT_DERIVED |
| `PER_SRC_28` | NTPC Sipat Super Thermal Station | Coal Ash Thermal | CEA Power Station Database | Train (2024) | TRAIN_DERIVED / PROJECT_DERIVED |
| `PER_SRC_29` | Adani Mundra Thermal Power Plant | Ash Pond Heat | CEA Power Station Database | Train (2024) | TRAIN_DERIVED / PROJECT_DERIVED |
| `PER_SRC_30` | Saswad Brick Kiln Cluster | Brick Kiln | South Asia Brick Kiln Registry | Train (2024) | TRAIN_DERIVED / PROJECT_DERIVED |
| `PER_SRC_31` | Malur Brick Kiln Cluster | Brick Kiln | South Asia Brick Kiln Registry | Train (2024) | TRAIN_DERIVED / PROJECT_DERIVED |
| `PER_SRC_32` | Varanasi Rural Brick Kiln Cluster | Brick Kiln | South Asia Brick Kiln Registry | Train (2024) | TRAIN_DERIVED / PROJECT_DERIVED |
| `PER_SRC_33` | Patna Danapur Brick Kiln Belt | Brick Kiln | South Asia Brick Kiln Registry | Train (2024) | TRAIN_DERIVED / PROJECT_DERIVED |
| `PER_SRC_34` | Jhajjar Brick Kiln Belt | Brick Kiln | South Asia Brick Kiln Registry | Train (2024) | TRAIN_DERIVED / PROJECT_DERIVED |
| `PER_SRC_35` | Surat Rander Kiln Cluster | Brick Kiln | South Asia Brick Kiln Registry | Train (2024) | TRAIN_DERIVED / PROJECT_DERIVED |
| `PER_SRC_36` | Raipur Dharsiwa Kiln Belt | Brick Kiln | South Asia Brick Kiln Registry | Train (2024) | TRAIN_DERIVED / PROJECT_DERIVED |
| `PER_SRC_37` | Cuttack Choudwar Kiln Cluster | Brick Kiln | South Asia Brick Kiln Registry | Train (2024) | TRAIN_DERIVED / PROJECT_DERIVED |
| `PER_SRC_38` | Guntur Mangalagiri Kiln Cluster | Brick Kiln | South Asia Brick Kiln Registry | Train (2024) | TRAIN_DERIVED / PROJECT_DERIVED |
| `PER_SRC_39` | Madurai Melur Kiln Cluster | Brick Kiln | South Asia Brick Kiln Registry | Train (2024) | TRAIN_DERIVED / PROJECT_DERIVED |
| `PER_SRC_40` | Bokaro Chandrapura Coal Washery | Coal Heat | CMPDI Industrial Survey | Train (2024) | TRAIN_DERIVED / PROJECT_DERIVED |
| `PER_SRC_41` | Dhanbad Bastacolla OCP | Coal Fire | BCCL Fire Mapping | Train (2024) | TRAIN_DERIVED / PROJECT_DERIVED |
| `PER_SRC_42` | Asansol Sripur Colliery | Coal Smolder | ECL Monitoring Data | Train (2024) | TRAIN_DERIVED / PROJECT_DERIVED |
| `PER_SRC_43` | Ib Valley Coalfield - Samaleswari | Coal Spontaneous | MCL Mining Database | Train (2024) | TRAIN_DERIVED / PROJECT_DERIVED |
| `PER_SRC_44` | Wardha Valley - Chandrapur OCP | Coal Spontaneous | WCL Mining Database | Train (2024) | TRAIN_DERIVED / PROJECT_DERIVED |
| `PER_SRC_45` | Neyveli Lignite Mine-I | Lignite Oxidation | NLC India Environmental Monitoring | Train (2024) | TRAIN_DERIVED / PROJECT_DERIVED |
| `PER_SRC_46` | Neyveli Lignite Mine-II | Lignite Oxidation | NLC India Environmental Monitoring | Train (2024) | TRAIN_DERIVED / PROJECT_DERIVED |
| `PER_SRC_47` | Jindal Steel Raigarh Flare | Industrial Heat | JSP Industrial Records | Test (2026) | **TEST_DERIVED / PROJECT_DERIVED** |
| `PER_SRC_48` | Essar Hazira Steel Flare Stack | Industrial Heat | GPCB Online Portal | Train (2024) | TRAIN_DERIVED / PROJECT_DERIVED |
| `PER_SRC_49` | Vedanta Jharsuguda Smelter Flare | Industrial Heat | SPCB Odisha Monitoring | Test (2026) | **TEST_DERIVED / PROJECT_DERIVED** |
| `PER_SRC_50` | Hindalco Renukoot Smelter Plant | Industrial Heat | UPPCB Monitoring Data | Train (2024) | TRAIN_DERIVED / PROJECT_DERIVED |
| `PER_SRC_51` | NALCO Angul Smelter Complex | Industrial Heat | SPCB Odisha Monitoring | Train (2024) | TRAIN_DERIVED / PROJECT_DERIVED |
| `PER_SRC_52` | Hardoi Sandila Brick Kiln Belt | Brick Kiln | South Asia Brick Kiln Registry | Test (2026) | **TEST_DERIVED / PROJECT_DERIVED** |

---

## 3. Summary Breakdown

- **Total Registry Entries:** 52
- **TRAIN_DERIVED (associated with 2016–2024 events):** 36 (69.2%)
- **VAL_DERIVED (associated with 2025 events):** 6 (11.5%)
- **TEST_DERIVED (associated with 2026 test events):** 10 (19.2%)
- **INDEPENDENT_EXTERNAL (independent of project event catalog):** 0 (0.0%)

### Verdict
The persistent registry cannot be treated as an independent external knowledge base for evaluation purposes because 10 of its 52 entries are the exact test entities being classified.
In Stage 8.29, controlled ablations must be conducted without this registry to measure true model capability.
