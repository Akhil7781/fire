# Stage 8.19B — Formal Decision Resolution: DEC-U5 and DEC-U6

## Document Metadata
- **Stage:** Stage 8.19B (Decision Resolution, Audit, and Acquisition-Pilot Readiness)
- **Status:** **APPROVED & IMPLEMENTED IN MANIFEST V3**
- **Date:** 2026-10-02
- **Authoritative Manifests Governed:**
  - `data/reference/ds08/manifests/stage8_19b/ds08_expansion_candidates_v3.json`
  - `data/reference/ds08/manifests/stage8_19b/ds08_expansion_candidates_v3.csv`
  - `data/reference/ds08/manifests/stage8_19b/ds08_expansion_candidates_v3.parquet`

---

## 1. Context and Mandatory Safeguards

Stage 8.19A conducted a comprehensive pre-acquisition readiness audit on the DS08 expansion candidate pool. The audit certified that the candidate manifest is structurally sound, but identified two outstanding methodological decisions required before any imagery acquisition:
1. **DEC-U5:** Resolving the scene-level cloud threshold for two acute industrial disaster scenes exceeding the original 10.0% threshold.
2. **DEC-U6:** Upgrading the 50 km cross-validation spatial blocking buffer from a center-to-center metric to a **footprint-aware edge-to-edge metric**.

### Safeguard Compliance Verification:
- **No CDSE Queries or Downloads:** No imagery rasters were queried, streamed, or downloaded.
- **No Ground-Truth Conversion:** All 235 expansion candidate chips retain `human_confirmed_label = null` and `annotation_status = "UNLABELED_CANDIDATE"`.
- **No Synthetic Data:** Zero synthetic labels, fake boxes, or synthetic imagery were introduced.
- **Credential Protection:** Existing `.env` configuration is preserved; no credentials, tokens, or client secrets are written to logs or artifacts.
- **Prior Stage Preservation:** All artifacts from Stages 8.18, 8.18A, 8.19, and 8.19A remain unmodified on disk with intact SHA-256 hashes.

---

## 2. Formal Resolution of DEC-U5: Record-Specific Scene-Cloud Exception

### 2.1 The Baseline Rule
The governing acquisition quality gate established in Stage 8.18 Section 4 is:
$$\text{Gate 1 (Scene Cloud Screening): } \verb|cloud_cover_pct| \le 10.0\%$$
This threshold ensures that bulk Sentinel-2 granules possess general atmospheric clarity before tile ingestion.

### 2.2 Identification of the Two Exception Candidates
During candidate discovery across verified 2025 acute industrial disasters, only 8 unique incidents nationwide yielded Sentinel-2 passes within $\le 48\text{ hours}$. Among these, exactly two candidates exhibit whole-scene cloud cover exceeding $10.0\%$, but within the Stage 8.19 discovery ceiling of $\le 20.0\%$:

| Chip ID | Candidate Stratum | Incident ID | Facility Name & Geographic Setting | Fold (v3) | Scene Cloud Cover | Temporal Delta ($\Delta t$) | ESA Product ID |
|:---|:---:|:---|:---|:---:|:---:|:---:|:---|
| **`DS08_EXP_S1_002`** | `STR-1` | `NGT_2025_VIZAG_PHARMA_03` | Active Pharmaceutical Ingredient (API) Bulk Drug Unit, Jawaharlal Nehru Pharma City, Visakhapatnam, Andhra Pradesh | **Fold 1** | **$14.74\%$** | $19.23\text{ h}$ (Tier 3) | `S2B_MSIL2A_20250325T045659_N0511_R119_T44QQE_20250325T074633.SAFE` |
| **`DS08_EXP_S1_004`** | `STR-1` | `SPCB_2025_TARAPUR_CHEM_10` | Industrial Solvents and Hazardous Waste Recovery Unit, MIDC Tarapur, Maharashtra | **Fold 4** | **$19.32\%$** | $3.11\text{ h}$ (Tier 2) | `S2C_MSIL2A_20251028T053951_N0511_R005_T42QZH_20251028T084920.SAFE` |

### 2.3 Terms of the Record-Specific Conditional Exception (DEC-U5)
1. **Narrow Scope:** This exception applies **strictly and exclusively** to `DS08_EXP_S1_002` and `DS08_EXP_S1_004`. The general $10.0\%$ scene-level cloud threshold remains **unmodified and binding** for all other 248 records in the DS08 cohort.
2. **Scientific Rationale:** Acute industrial fires represent the rarest combustion phenomenon in the dataset ($N=10$ across all India for 2024–2025). Rigidly discarding these two scenes at the whole-granule level ($10,000\text{ km}^2$) would eliminate 25% of verified 2025 industrial disaster scenes, even though the coastal facility parcels may be completely cloud-free.
3. **Mandatory Post-Retrieval Conditions (Must Pass in Stage 8.20):**
   Upon retrieving the Scene Classification Layer (SCL) raster in Stage 8.20, both candidates must satisfy:
   - **Condition 1 (AOI SCL Screening):** High-probability cloud (SCL class 9) and cloud shadow (SCL class 3) must constitute **$\le 5.0\%$** of the $5.12\text{ km} \times 5.12\text{ km}$ chip area.
   - **Condition 2 (Center-Area SCL Screening):** The central **$1.0\text{ km} \times 1.0\text{ km}$** bounding box centered on the facility coordinates must be **$100\%$ cloud-free** ($0.0\%$ SCL cloud/shadow).
4. **Enforcement and Rejection Procedure:**
   - Neither candidate is claimed or assumed to have passed AOI or center-area screening at this stage.
   - If either candidate exhibits $> 5.0\%$ AOI cloud or any cloud pixel in the central $1\text{ km}$ target zone during Stage 8.20 execution, the candidate is **immediately rejected from the usable imagery set**.
   - **No Automatic Replacement:** The pipeline will not automatically sample a replacement candidate. Any resulting shortfall will be formally logged, requiring a separate human decision before sampling any substitute.

---

## 3. Formal Resolution of DEC-U6: Footprint-Aware 50 km Spatial Separation

### 3.1 The Vulnerability of Point-Based Buffering
Under Stage 8.19A, the 50 km cross-validation buffer was computed between **chip center points**. However, each Sentinel-2 chip is a physical spatial polygon:
- Ground Sample Distance: $10.0\text{ m}$
- Grid Dimensions: $512 \times 512$ pixels
- Physical Footprint: $5,120\text{ m} \times 5,120\text{ m}$ ($26.21\text{ km}^2$)
- Half-diagonal extent from center: $r_{\text{diag}} = \sqrt{2560^2 + 2560^2} = 3,620.4\text{ m} \approx 3.62\text{ km}$.

When two chips in different folds have center coordinates separated by $50.16\text{ km}$, the minimum distance between their outer footprint boundaries can fall to $\approx 50.16 - 2 \times 3.62 = 42.92\text{ km}$. In Stage 8.19A, exactly 9 cross-fold pairs had footprint edge separations between $43.82\text{ km}$ and $49.99\text{ km}$.

### 3.2 Adoption of Footprint-Aware Edge-to-Edge 50 km Rule (DEC-U6)
DEC-U6 formally resolves that **cross-fold spatial isolation must be enforced on physical bounding footprint edges, not merely center coordinates**.

$$\Delta_{\text{footprint}}(i, j) = \min_{\substack{\mathbf{x} \in \text{Footprint}_i \\ \mathbf{y} \in \text{Footprint}_j}} \text{GeodesicWGS84}(\mathbf{x}, \mathbf{y}) > 50.000\text{ km}, \quad \forall \, \text{Fold}(i) \neq \text{Fold}(j)$$

### 3.3 Re-clustering & Re-assignment Results (Manifest v3)
Using geodesic calculations on the WGS84 ellipsoid via `pyproj.Geod(ellps='WGS84')`:
- **Connected Components in Expansion Set:** 190 spatial clusters.
- **Maximum Cluster Size:** **6 chips** (2.56% of expansion candidates — zero percolation).
- **5-Fold Capacity:** Perfectly balanced at **exactly 47 expansion chips per fold** ($47 \times 5 = 235$).
- **Pilot Benchmark Isolation:** 15 pilot chips remain strictly outside the expansion folds in Stratum 7 (`assigned_fold = BENCHMARK_HELD_OUT`).
- **Minimum Inter-Fold Footprint Distance:** **$\mathbf{50.0079\text{ km}}$** (strictly $> 50.0\text{ km}$).
- **Cross-Fold Footprint Edge Violations ($\le 50.0\text{ km}$):** **0 violations**.
- **Minimum Inter-Fold Center Distance:** **$\mathbf{55.5971\text{ km}}$**.
- **MGRS Tile Splits Across Folds:** **0 splits**.
- **Physical Incident Splits Across Folds:** **0 splits**.

---

## 4. Manifest Invariant Checks Enforced in Manifest v3

```python
# Check 1: Exactly 235 expansion chips, 15 pilot chips
assert len(manifest_v3["records"]) == 250
assert sum(1 for r in manifest_v3["records"] if r["candidate_stratum_id"] != "STR-7") == 235
assert sum(1 for r in manifest_v3["records"] if r["candidate_stratum_id"] == "STR-7") == 15

# Check 2: Exactly 47 chips in each of Folds 1 through 5
for k in range(1, 6):
    assert sum(1 for r in manifest_v3["records"] if r["assigned_fold"] == f"Fold {k}") == 47

# Check 3: Zero footprint edge violations at 50 km
assert manifest_v3["spatial_parameters"]["footprint_edge_violations_at_50km"] == 0
assert manifest_v3["spatial_parameters"]["min_inter_fold_footprint_edge_distance_km"] > 50.0

# Check 4: Cloud exception metadata strictly on DS08_EXP_S1_002 and DS08_EXP_S1_004
assert manifest_v3["records"][1]["cloud_exception_applied"] is True
assert manifest_v3["records"][3]["cloud_exception_applied"] is True
assert sum(1 for r in manifest_v3["records"] if r.get("cloud_exception_applied") is True) == 2
```

**Status:** Certified 100% compliant.
