# STAGE 8.18 — DS08 DATASET EXPANSION: QUALITY ASSURANCE & GOVERNANCE
**Comprehensive Data Governance, Cryptographic Integrity, and Quality Control Specification**

- **Document Version:** 1.0.0
- **Stage:** Stage 8.18 — DS08 Dataset Expansion Planning
- **Status:** **DRAFT SPECIFICATION — LOCKED FOR HUMAN REVIEW**
- **Governance Target:** DS08 Production Cohort ($N \approx 250$ chips)

---

## 1. Quality Control Architecture: Automated vs Human Review

Dataset quality assurance operates on two non-interchangeable tiers:
1. **Automated Verification Gates:** Enforces structural integrity, coordinate mathematics, radiometric bounds, cryptographic hashes, and logical mutual exclusions.
2. **Human Scientific Auditing:** Validates that visual interpretations reflect physical combustion reality rather than automated artifacts or annotator bias.

> [!WARNING]
> **Validation $\ne$ Scientific Ground Truth:**  
> Passing automated JSON schema validation or achieving high inter-annotator agreement does **not** prove that a label is physically true. It merely proves structural compliance and consistency. Ground truth requires rigorous human grounding in optical and multi-source evidence.

---

## 2. Quantitative Inter-Annotator Agreement Benchmarks

Across the double-pass manual annotation phase ($N \approx 250$ chips), the automated discrepancy engine computes the following statistical metrics:

| Metric | Target Threshold | Formula / Definition | Operational Action if Below Threshold |
| :--- | :---: | :--- | :--- |
| **Cohen’s Kappa ($\kappa$)** | **$\ge 0.80$** | $\kappa = \frac{P_o - P_e}{1 - P_e}$ across primary classes | Retrain annotators on ambiguous boundary cases; audit class definitions. |
| **Observation Concordance** | **$\ge 90.0\%$** | Agreement on `HAS_ANNOTATIONS` vs `NO_VISIBLE_TARGET` | Mandatory senior adjudication on all discordant chips. |
| **Mean Bounding Box IoU** | **$\ge 0.60$** | $\frac{\text{Area}(B_1 \cap B_2)}{\text{Area}(B_1 \cup B_2)}$ on matched pairs | Review boundary guidelines for diffuse smoke and burn scar edges. |
| **Evidence Jaccard Index** | **$\ge 0.75$** | $J(E_1, E_2) = \frac{\|E_1 \cap E_2\|}{\|E_1 \cup E_2\|}$ | Eliminate ambiguous multi-tag combinations. |
| **Adjudication Escalation Rate** | **$\le 25.0\%$** | Percentage of chips requiring senior human resolution | If $> 25\%$, pause annotation to clarify confusing imagery conditions. |

---

## 3. Automated Integrity & Consistency Checks

The automated validation suite (`scripts/validate_ds08_pilot_package.py`, expanded for $N=250$) executes **10 mandatory checks** before any package release:

```text
========================================================================================
                          AUTOMATED QUALITY GATES (10 CHECKS)
========================================================================================
Gate 1:  COHORT_MEMBERSHIP            Exact expected chip count; zero duplicate chip IDs.
Gate 2:  MEDIA_COMPLETENESS          Every chip has GeoTIFF, RGB, SWIR, metadata (>0 bytes).
Gate 3:  SCHEMA_COMPLIANCE           Strict conformance to ds08_annotation_schema.json.
Gate 4:  GEOMETRIC_VALIDITY          0 <= xmin < xmax <= 512, 0 <= ymin < ymax <= 512, w,h >= 4.
Gate 5:  PLACEHOLDER_PROHIBITION     Zero uniform placeholder coordinates ([200,200,300,300]).
Gate 6:  EVIDENCE_MUTUAL_EXCLUSION   NO_CLEAR_VISUAL_EVIDENCE cannot co-occur with fire/scar tags.
Gate 7:  STATUS_DEFINITIVENESS       Only HAS_ANNOTATIONS or NO_VISIBLE_TARGET (UNRESOLVED blocked).
Gate 8:  EMPTY_ANNOTATION_INTEGRITY  NO_VISIBLE_TARGET <=> annotations == [].
Gate 9:  CRYPTOGRAPHIC_HASHES        Every file matches manifest SHA-256 bit-for-bit.
Gate 10: QUARANTINE_ISOLATION        Zero hash collisions with historical quarantined records.
========================================================================================
```

---

## 4. Duplicate & Near-Duplicate Scene Detection

To prevent subtle scene duplication or redundant orbit sampling:
1. **Exact Product ID Check:** No two chips in the package may share the same Sentinel-2 `product_id`.
2. **Spatial Overlap Buffer Check:**
   - Geodesic bounding boxes in projected UTM coordinates are intersected.
   - Any two chips with spatial intersection area $> 20\%$ of chip area ($> 5.24\text{ km}^2$) must be flagged as near-duplicates. Only the scene with superior atmospheric clarity ($\le \text{cloud}$) is retained; the other is discarded.

---

## 5. Cryptographic Provenance & Versioning Rules

1. **Immutable Source Hashes:**
   - Every raw GeoTIFF, preview PNG, metadata JSON, draft annotation, and final consensus record receives a SHA-256 fingerprint upon creation.
   - Initial source hashes are permanently stored in an immutable source manifest (e.g. `stage8_18_source_manifest.json`).
2. **Pre-Save & Post-Save Integrity Verification:**
   - Any script writing annotations or packaging data must verify that original source records are bit-for-bit identical before and after execution.
3. **Append-Only Audit Logs:**
   - All human annotation interactions (canvas draw, box creation, save events, adjudication rationales) are written to immutable JSONL audit logs with UTC timestamps.

---

## 6. Quarantine Procedures & Boundary Enforcement

When an annotation or acquisition batch is identified as defective, non-human, or contradictory:
1. **Quarantine Directory:** Files are moved into `data/reference/ds08/annotations/quarantine/{stage_id}_invalid/`.
2. **Prohibition on Deletion:** Quarantined files must **never be deleted**. They form a permanent forensic audit trail.
3. **Boundary Isolation:** Automated validators must verify that no quarantined SHA-256 hash appears in any active annotation or release package.
4. **Documentation:** A dedicated `QUARANTINE_AUDIT.md` document must record the exact reason, affected hashes, and remediation path.

---

## 7. Package Reproducibility

Every dataset release package (e.g., `ds08_v1_0`) must contain:
1. `manifest.json`: Full machine-readable inventory of all included chips, file paths, SHA-256 digests, and source provenance.
2. `manifest.csv`: Tabular index of coordinates, acquisition dates, MGRS tiles, and class labels.
3. `README.md`: Data dictionary, band descriptions, and usage terms.
4. `validation_report.json`: Machine-readable output of the 10-point automated validation audit.
5. Exact CLI reproduction commands to regenerate the package from raw source rasters.
