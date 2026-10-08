# Stage 8.19A — Taxonomy Decoupling: Candidate Stratum, Expected Class, and Human-Confirmed Label

## Executive Summary

A critical scientific vulnerability in machine learning datasets derived from remote sensing alerts (e.g., FIRMS active fires, land-cover maps) is **label conflation**: treating a candidate discovery stratum or prior alert as ground truth visual labels. 

To prevent circular evaluation and label poisoning, **Stage 8.19A establishes strict field decoupling** in the DS08 expansion candidate manifest:
1. **Candidate Stratum (`candidate_stratum_id` / `name`):** Represents the sampling source and discovery criteria.
2. **Expected Target Class (`expected_target_class` / `id`):** Represents the *prior hypothesis* of what visual phenomenon may be present in the Sentinel-2 chip based on auxiliary data.
3. **Human-Confirmed Annotation Label (`human_confirmed_label`):** The authoritative, audited visual ground truth, populated **only** after double-blind human annotation and consensus adjudication.

**Status in `ds08_expansion_candidates_v2.json`:**
- All 235 expansion candidates have `human_confirmed_label = null` and `annotation_status = "UNLABELED_CANDIDATE"`.
- Bounding boxes are initialized as empty lists (`[]`).
- Only the 15 held-out pilot benchmark chips have populated `human_confirmed_label` and `confirmed_bounding_boxes`, originating from the Stage 8.16 adjudication audit.

---

## 1. Tripartite Schema Definition

```
+----------------------------------------------------------------------------------------------------+
|                                    DS08 RECORD TAXONOMY ARCHITECTURE                               |
+----------------------------------------------------------------------------------------------------+
| 1. SAMPLING STRATUM (Discovery Basis)                                                              |
|    - candidate_stratum_id   : e.g. "STR-1"                                                         |
|    - candidate_stratum_name : e.g. "Confirmed Acute Industrial Fires"                             |
|    - primary_sampling_unit  : e.g. "Unique Physical Ground Incident (incident_id)"                 |
|                                                                                                    |
| 2. PRIOR HYPOTHESIS (Unconfirmed Expectation)                                                      |
|    - expected_target_class  : e.g. "Industrial Fire"                                               |
|    - expected_class_id      : e.g. 1                                                               |
|    - temporal_phase         : e.g. "ACTIVE_COMBUSTION"                                             |
|                                                                                                    |
| 3. AUTHORITATIVE GROUND TRUTH (Post-Human Adjudication Only)                                       |
|    - human_confirmed_label   : null (EXPANSION) | "Forest Fire" / "NO_VISIBLE_TARGET" (PILOT)      |
|    - confirmed_bounding_boxes: []   (EXPANSION) | [{"box_id": ..., "ymin": ...}]      (PILOT)      |
|    - annotation_status       : "UNLABELED_CANDIDATE" (EXPANSION) | "COMPLETED_ADJUDICATED" (PILOT) |
+----------------------------------------------------------------------------------------------------+
```

### Detailed Field Specifications

| Manifest Field Name | Type | Allowed Values / Examples | Scientific Rationale |
|:---|:---|:---|:---|
| `candidate_stratum_id` | `string` | `STR-1`, `STR-2`, `STR-3`, `STR-4`, `STR-5`, `STR-6`, `STR-7` | Identifies the sampling cohort and target balance criteria. |
| `candidate_stratum_name` | `string` | e.g. `Confirmed Acute Industrial Fires` | Human-readable stratum descriptor. |
| `expected_target_class` | `string` | `Industrial Fire`, `Other Thermal Source`, `Forest Fire`, `Agricultural Fire`, `NO_VISIBLE_TARGET` | The prior expectation based on external alert data. **Must never be used as a training target.** |
| `expected_class_id` | `integer` | `1`, `4`, `2`, `3`, `0`, `-1` | Numeric code corresponding to project ontology. |
| `human_confirmed_label` | `string \| null` | `null` for expansion; class name for pilot | Authoritative visual target confirmed by two independent annotators and consensus adjudication. |
| `annotation_status` | `string` | `UNLABELED_CANDIDATE` (235 chips) \| `COMPLETED_ADJUDICATED` (15 chips) | Controls data routing in the annotation and modeling pipelines. |
| `confirmed_bounding_boxes` | `list` | `[]` (235 chips) \| `[{"box_id": ..., ...}]` (15 chips) | Normalized bounding box coordinates $[y_{\text{min}}, x_{\text{min}}, y_{\text{max}}, x_{\text{max}}]$. |

---

## 2. Why Candidate Associations Must Never Be Treated as Confirmed Labels

In remote sensing and computer vision, alert metadata frequently disagrees with visual optical evidence:

1. **Thermal Blindness & Timing Discrepancies:**
   - A VIIRS FRP alert at 08:30 UTC indicates active thermal emission. However, by the Sentinel-2 overpass at 10:45 UTC, the fire may have been extinguished, leaving only an unburnt roof or a diffuse post-combustion scar.
   - If `expected_target_class = "Industrial Fire"` were treated as the label, the model would be trained to detect an intact building as an active fire (label noise).
2. **Sub-Pixel Flaring vs. Ground Fires:**
   - A gas flare at an oil refinery generates high VIIRS FRP (Stratum 2), but visual inspection of Sentinel-2 SWIR/RGB bands may reveal no smoke, no flame boundary, or a saturated point reflection that is categorized as `Other Thermal Source` rather than `Industrial Fire`.
3. **Cloud & Shadow Occlusion:**
   - Even with $< 5\%$ scene-wide cloud cover, localized cloud or cloud shadow may obscure the exact facility coordinates. The human annotator must flag this as unresolvable or negative rather than blindly accepting the alert.
4. **False Alarm Rejection:**
   - Negative controls (Stratum 5 and 6) are selected from industrial complexes and farmlands. Occasionally, an unexpected local burn is visually evident in a "negative" tile. Only a human annotator can correctly box the fire, overriding the stratum expectation.

---

## 3. Manifest Invariant Checks Enforced in Manifest v2

The following automated integrity constraints were executed across all 250 records:

```python
# Invariant 1: All 235 expansion candidate chips must have null human label
assert all(r["human_confirmed_label"] is None for r in expansion_records)

# Invariant 2: All 235 expansion candidate chips must be marked UNLABELED_CANDIDATE
assert all(r["annotation_status"] == "UNLABELED_CANDIDATE" for r in expansion_records)

# Invariant 3: All 235 expansion candidate chips must have empty bounding boxes
assert all(len(r["confirmed_bounding_boxes"]) == 0 for r in expansion_records)

# Invariant 4: All 15 pilot benchmark chips must have non-null human label and COMPLETED_ADJUDICATED status
assert all(r["human_confirmed_label"] is not None for r in pilot_records)
assert all(r["annotation_status"] == "COMPLETED_ADJUDICATED" for r in pilot_records)
```

**Audit Result:** 100% Passed. Zero premature or synthetic labels exist in the expansion candidate manifest.
