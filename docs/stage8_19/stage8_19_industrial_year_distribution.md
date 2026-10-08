# STAGE 8.19 — ACUTE INDUSTRIAL FIRE YEAR DISTRIBUTION & DEC-U1 AUDIT REPORT
**Empirical S2 Overpass Scarcity, 2024 Expansion Activation, and Physical Ground Truth Provenance**

- **Document Version:** 1.0.0
- **Stage:** Stage 8.19 — Read-only Candidate Discovery & STAC Manifest Building
- **Decision Reference:** **DEC-U1** (Approved by User Directive)
- **Status:** **COMPLETE — LOCKED FOR HUMAN REVIEW**
- **Stratum Evaluated:** Stratum 1 (Confirmed Acute Industrial Fires, Target: $N = 10\text{--}15$ Primary Chips)

---

## 1. Executive Summary & DEC-U1 Directive

Per user instruction for **DEC-U1**:
> *"Approve expansion to verified 2024 industrial-fire incidents only if 2025 produces fewer than 20 viable candidate scenes for Stratum 1. Keep event year and Sentinel-2 acquisition year as separate fields. Document the year distribution and do not weaken incident verification criteria to meet the quota."*

### Empirical Assessment of 2025 Industrial Incidents:
- All 14 verified 2025 acute industrial fire incidents documented in the repository (`data/reference/ds05/industrial_incidents.json` and `india_industrial_incidents_2025_normalized.parquet`) were systematically queried against the Copernicus Data Space Ecosystem (CDSE) Sentinel-2 L2A STAC catalog.
- Query parameters: bounding box centered on verified facility coordinates, $|\Delta t| \le 48.0\text{ hours}$ from event start, scene cloud cover $\le 20.0\%$, and required 5 spectral bands (B02, B03, B04, B11, B12).
- **Result:** Across all 14 incidents, exactly **13 viable candidate scenes** were discovered across only **8 unique physical incidents**.
- Because $13 < 20$ viable scenes, **the condition for DEC-U1 expansion was strictly satisfied**.

---

## 2. Authorized 2024 Industrial Fire Expansion

To fulfill the minimum stratum threshold ($N \ge 10$ primary chips) without weakening incident verification criteria, 12 major verified 2024 industrial disaster events were queried against CDSE STAC with identical strict physical criteria.

- Two verified 2024 incidents yielded clear Sentinel-2 Level-2A overpasses with $\le 4.6\text{h}$ and $\le 24\text{h}$ temporal delta and $0.0\%$ cloud cover:
  1. `NDMA_2024_HARDA_FIRECRACKERS` (Bairagarh Explosives Disaster, Harda, MP, 2024-02-06, $\Delta t = 23.95\text{h}$, cloud cover $0.0\%$).
  2. `SEBI_2024_DAHEJ_BHARAT_RASAYAN` (Dahej GIDC Agrochem Fire, Bharuch, Gujarat, 2024-03-12, $\Delta t = 4.61\text{h}$, cloud cover $0.0\%$).

Combined with the 8 viable 2025 incidents, exactly **10 verified unique physical incidents** were selected as canonical primary chips for Stratum 1.

---

## 3. Authoritative Stratum 1 Manifest Inventory ($N = 10$)

| Chip ID | Incident ID | Facility Name | District / State | Region | Event Year | S2 Acq Year | S2 Scene ID | Cloud % | $\Delta t$ (h) | Temporal Phase | Corroboration Authority |
| :--- | :--- | :--- | :--- | :---: | :---: | :---: | :--- | :---: | :---: | :--- | :--- |
| `DS08_EXP_S1_001` | `SPCB_2025_MPCB_DOMBIVLI_02` | Chemical Synthesis Plant, MIDC Phase II | Thane, Maharashtra | WEST | **2025** | **2025** | `S2C_..._T43QBB_...` | 6.65% | 45.65 | `POST_COMBUSTION_SCAR` | MPCB Section 31A Order / DISH Form 24 |
| `DS08_EXP_S1_002` | `NGT_2025_VIZAG_PHARMA_03` | API Bulk Drug Unit, Jawaharlal Nehru SEZ | Anakapalli, AP | CENTRAL | **2025** | **2025** | `S2B_..._T44QQE_...` | 14.74% | 19.23 | `POST_COMBUSTION_SCAR` | NGT Principal Bench OA 112/2025 |
| `DS08_EXP_S1_003` | `SEBI_2025_PANIPAT_POLYMER_04` | Polymer & Synthetic Yarn Warehouse | Panipat, Haryana | NORTH | **2025** | **2025** | `S2B_..._T43RFN_...` | 8.12% | 15.11 | `POST_COMBUSTION_SCAR` | SEBI Reg 30 Disclosure / Fire Tender Log |
| `DS08_EXP_S1_004` | `SPCB_2025_TARAPUR_CHEM_10` | Solvents Recovery Unit, MIDC Tarapur | Palghar, Maharashtra | WEST | **2025** | **2025** | `S2C_..._T42QZH_...` | 3.41% | 20.66 | `POST_COMBUSTION_SCAR` | MPCB Emergency Closure Direction |
| `DS08_EXP_S1_005` | `NEWS_2025_BADDI_PHARMA_11` | Pharmaceutical Packaging Foil Unit | Solan, HP | NORTH | **2025** | **2025** | `S2C_..._T43RFQ_...` | 2.15% | 3.52 | `ACTIVE_COMBUSTION` | HP State Fire Dept Log / Press Verification |
| `DS08_EXP_S1_006` | `SEBI_2025_HALOL_AUTO_PARTS_12` | Automotive Paint Shop Complex | Panchmahal, Gujarat | WEST | **2025** | **2025** | `S2C_..._T43QCE_...` | 1.88% | 40.71 | `POST_COMBUSTION_SCAR` | SEBI Reg 30 Filing / DISH Incident Docket |
| `DS08_EXP_S1_007` | `SEBI_2025_HEUBACH_ROHA_13` | Specialty Pigments Plant, MIDC Roha | Raigad, Maharashtra | WEST | **2025** | **2025** | `S2B_..._T43QBA_...` | 0.45% | 32.74 | `POST_COMBUSTION_SCAR` | SEBI LODR Filing / MPCB Notice |
| `DS08_EXP_S1_008` | `MOD_2025_BHANDARA_ORDNANCE_14` | Ordnance Factory Explosives Estate | Bhandara, Maharashtra | CENTRAL | **2025** | **2025** | `S2C_..._T44QLJ_...` | 5.22% | 48.00 | `POST_COMBUSTION_SCAR` | Ministry of Defence / District Inquiry |
| `DS08_EXP_S1_009` | `NDMA_2024_HARDA_FIRECRACKERS` | Bairagarh Fireworks Factory & Store | Harda, MP | CENTRAL | **2024** | **2024** | `S2B_..._T43QFE_...` | 0.00% | 23.95 | `POST_COMBUSTION_SCAR` | MP SDMA / Ministry of Home Affairs Report |
| `DS08_EXP_S1_010` | `SEBI_2024_DAHEJ_BHARAT_RASAYAN` | Agro-Chemicals Technical Plant | Bharuch, Gujarat | WEST | **2024** | **2024** | `S2B_..._T42QZJ_...` | 0.00% | 4.61 | `ACTIVE_COMBUSTION` | SEBI Reg 30 Filing / GPCB Section 31A Order |

---

## 4. Year Distribution & Contingency Reallocation Analysis

```text
========================================================================================
                     STRATUM 1 YEAR & SAMPLING UNIT BREAKDOWN
========================================================================================
Total Primary Chips Allocated:                10 chips (100.0% unique physical incidents)
  - Calendar Year 2025 Incidents:              8 chips (80.0%)
  - Calendar Year 2024 Incidents (DEC-U1):     2 chips (20.0%)
Sentinel-2 Acquisition Year Concordance:       100.0% (Event year == Acquisition year)
----------------------------------------------------------------------------------------
Target Allocation in Stage 8.18A Plan:         15 chips (Minimum Required: 10 chips)
Achieved Primary Unique Incidents:             10 chips (Minimum threshold satisfied)
Shortfall from Target:                         5 chips
Contingency Reallocation Applied:             5 chips transferred to Stratum 2 (PST)
Revised Stratum 2 Allocation:                  35 chips (Base: 30 + Contingency: 5)
Total Cohort Preservation:                    250 chips (Exact mathematical total)
========================================================================================
```

### Verification Against Protocol Invariants:
1. **Separation of Year Fields:** In all outputs (`.json`, `.csv`, `.parquet`), `event_year` and `s2_acquisition_year` are distinct integer columns.
2. **Zero Verification Weakening:** Every 2024 and 2025 incident possesses verifiable regulatory orders (MPCB, GPCB, NGT), statutory stock exchange disclosures (SEBI LODR Reg 30), or official disaster authority inquiry reports.
3. **Pseudo-Replication Eliminated:** Exactly one primary chip per physical disaster is included (`is_primary_chip = True`). Multi-scene revisits are excluded from the quota.
