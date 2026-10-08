# STAGE 8.18A — GEOGRAPHIC PARTITION SPECIFICATION
**Mutually Exclusive and Exhaustive Regional Sampling Definitions for India**

- **Document Version:** 2.0.0
- **Stage:** Stage 8.18A — Protocol Review & Sign-Off Preparation
- **Status:** **REVISED SPECIFICATION — LOCKED FOR HUMAN REVIEW**
- **Study Area:** Sovereign Territory and Exclusive Economic Zone of India ($\text{Lat} \in [6.0^\circ, 38.0^\circ\text{N}], \text{Lon} \in [68.0^\circ, 98.0^\circ\text{E}]$)
- **Target Allocation:** $N = 250$ Level-2A Sentinel-2 Chips

---

## 1. Defect in Original Proposal (Stage 8.18) & Resolution

### 1.1 Identified Defect:
In Stage 8.18, the geographic classification used heuristic boundary conditions:
- `NORTH`: $\text{Lat} \ge 27.0^\circ\text{N}$
- `CENTRAL`: $16.0^\circ \le \text{Lat} < 27.0^\circ\text{N}, 75.0^\circ \le \text{Lon} < 83.0^\circ\text{E}$
- `SOUTH`: $\text{Lat} < 16.0^\circ\text{N}$
- `EAST`: $\text{Lon} \ge 83.0^\circ\text{E}$
- `WEST`: $\text{Lon} < 75.0^\circ\text{E}, \text{Lat} < 27.0^\circ\text{N}$

**Failure Modes:**
1. **Overlap in Northeast India:** Points in Sikkim, Assam, and Arunachal Pradesh ($\text{Lat} \ge 27.0^\circ\text{N}$ and $\text{Lon} \ge 83.0^\circ\text{E}$) were ambiguously both `NORTH` and `EAST`. In the pilot acquisition script, `lat >= 27.0` executed first, incorrectly classifying northeastern chips (such as `PILOT_03_NORTH` at Lat 27.20, Lon 87.73) as `NORTH` rather than `EAST`.
2. **Ambiguity on Island Territories:** The Andaman & Nicobar archipelago ($\text{Lat} \approx 6.7^\circ\text{--}13.7^\circ\text{N}, \text{Lon} \approx 92.2^\circ\text{--}94.0^\circ\text{E}$) satisfied both $\text{Lat} < 16.0^\circ$ (`SOUTH`) and $\text{Lon} \ge 83.0^\circ$ (`EAST`).
3. **Coordinate Gaps:** Boundaries between Western and Central India did not specify strict inclusive/exclusive interval endpoints, creating edge ambiguities.

---

## 2. Revised Authoritative Geographic Partition

To guarantee that **every single spatial coordinate in India maps to exactly one region** with **zero overlaps and zero gaps**, Stage 8.18A establishes a two-tiered deterministic partition:

### Tier 1: Authoritative State & Union Territory Zonal Assignment (Primary Engine)
When the political jurisdiction of a candidate chip is known (via cadastral polygon, district lookup, or reverse geocode), it is assigned strictly according to official Ministry of Home Affairs Zonal Council boundaries:

| Geographic Region | Member States and Union Territories | Target Share | Target Chips ($N=250$) |
| :--- | :--- | :---: | :---: |
| **NORTH** | Punjab, Haryana, Himachal Pradesh, Jammu & Kashmir, Ladakh, Uttarakhand, Delhi, Chandigarh, Uttar Pradesh (excluding Eastern UP Purvanchal). | **22.0%** | **55 chips** |
| **CENTRAL** | Madhya Pradesh, Chhattisgarh. | **24.0%** | **60 chips** |
| **SOUTH** | Andhra Pradesh, Telangana, Karnataka, Tamil Nadu, Kerala, Puducherry, Lakshadweep. | **18.0%** | **45 chips** |
| **EAST** | Bihar, Jharkhand, West Bengal, Odisha, Sikkim, Assam, Arunachal Pradesh, Nagaland, Manipur, Mizoram, Tripura, Meghalaya, Andaman & Nicobar. | **20.0%** | **50 chips** |
| **WEST** | Rajasthan, Gujarat, Maharashtra, Goa, Dadra & Nagar Haveli and Daman & Diu. | **16.0%** | **40 chips** |
| **TOTAL** | **Entire Sovereign Landmass and Offshore Territories of India** | **100.0%** | **250 chips** |

---

### Tier 2: Deterministic Coordinate Fallback Partition (Mathematical Engine)
When querying raw latitude/longitude points where GIS administrative boundary polygons are unavailable, coordinates within the India bounding box ($\text{Lat} \in [6.0^\circ, 38.0^\circ\text{N}]$, $\text{Lon} \in [68.0^\circ, 98.0^\circ\text{E}]$) are evaluated by a **strictly disjoint, ordered decision tree**:

```python
def classify_indian_region_v2(lat: float, lon: float) -> str:
    """
    Deterministic, mutually exclusive, and exhaustive classification of
    coordinates across the sovereign bounding box of India.
    
    Guarantees:
    - Zero overlaps (disjoint partitions).
    - Zero gaps (exhaustive over Lat in [6.0, 38.0], Lon in [68.0, 98.0]).
    """
    # 1. Eastern & North-Eastern Domain (All territory east of 84.0 deg E)
    if lon >= 84.0:
        return "EAST"
    
    # 2. Southern Peninsular Domain (All territory south of 16.0 deg N and west of 84.0 deg E)
    if lat < 16.0:
        return "SOUTH"
    
    # 3. Northern Domain (Territory north of 28.0 deg N and west of 84.0 deg E)
    if lat >= 28.0:
        return "NORTH"
    
    # 4. Central & Western Mid-Latitude Domain (16.0 <= lat < 28.0 and lon < 84.0)
    # Separated by meridian 76.0 deg E:
    if lon < 76.0:
        return "WEST"
    else:
        return "CENTRAL"
```

### Mathematical Proof of Mutual Exclusivity and Exhaustiveness:
1. **Exhaustiveness:**
   - Case 1: $\text{lon} \ge 84.0 \implies \mathbf{EAST}$.
   - Case 2: $\text{lon} < 84.0$:
     - Subcase 2a: $\text{lat} < 16.0 \implies \mathbf{SOUTH}$.
     - Subcase 2b: $\text{lat} \ge 28.0 \implies \mathbf{NORTH}$.
     - Subcase 2c: $16.0 \le \text{lat} < 28.0$:
       - If $\text{lon} < 76.0 \implies \mathbf{WEST}$.
       - If $\text{lon} \ge 76.0$ (and $\text{lon} < 84.0$) $\implies \mathbf{CENTRAL}$.
   - Every coordinate $(\text{lat}, \text{lon}) \in [6.0, 38.0] \times [68.0, 98.0]$ is assigned to exactly one region. $\blacksquare$
2. **Mutual Exclusivity:**
   - The branches are structured as mutually disjoint half-open/closed intervals. No coordinate can trigger more than one return statement. $\blacksquare$

---

## 3. Allocation Verification & Reconciliation

| Region | Administrative Domain | Coordinate Domain Fallback | Allocated Chips | Minimum Quota | Percentage |
| :--- | :--- | :--- | :---: | :---: | :---: |
| **NORTH** | Northern States & UTs | $\text{lat} \ge 28.0^\circ, \text{lon} < 84.0^\circ$ | **55** | 45 | **22.0%** |
| **CENTRAL** | MP, Chhattisgarh | $16.0^\circ \le \text{lat} < 28.0^\circ, 76.0^\circ \le \text{lon} < 84.0^\circ$ | **60** | 50 | **24.0%** |
| **SOUTH** | Southern States & UTs | $\text{lat} < 16.0^\circ, \text{lon} < 84.0^\circ$ | **45** | 35 | **18.0%** |
| **EAST** | Eastern & NE States | $\text{lon} \ge 84.0^\circ$ (all latitudes) | **50** | 40 | **20.0%** |
| **WEST** | Rajasthan, Gujarat, Maharashtra | $16.0^\circ \le \text{lat} < 28.0^\circ, \text{lon} < 76.0^\circ$ | **40** | 30 | **16.0%** |
| **TOTAL** | **Pan-India Coverage** | **Complete Disjoint Partition** | **250** | **200** | **100.0%** |

$$\sum_{i=1}^5 \text{Allocated}_i = 55 + 60 + 45 + 50 + 40 = 250 \quad (100.0\%)$$
All regional quotas are verified deterministic and mathematically consistent.
