# DS08 Stage 8.16 Correction Storage Schema Specification

**Document Version:** 1.0.0  
**Stage:** Stage 8.16 — Controlled Human Adjudication Correction UI for DS08  
**Status:** ACTIVE  
**Last Updated:** 2026-10-02  

---

## 1. Overview and Design Principles

Stage 8.16 establishes an isolated, immutable correction workflow for the 6 disputed DS08 pilot chips flagged during Stage 8.15. 

To maintain strict scientific auditability and dataset integrity:
1. **Source Immutability:** Original Stage 8.15 adjudication files located in `data/reference/ds08/annotations/adjudication/review/` are **strictly read-only**. They are never modified, overwritten, or renamed.
2. **Dedicated Storage Target:** Corrected consensus records are saved into an isolated directory:
   `data/reference/ds08/annotations/adjudication/corrections/{chip_id}_corrected_v2.json`.
3. **Traceability:** Every correction record embeds the exact SHA-256 hash of its source record, an explicit human confirmation, a substantive rationale, a field-level diff summary, and an internal SHA-256 fingerprint.
4. **Append-Only Audit Log:** All validation operations, save attempts, and rejections are logged to `stage8_16_audit_log.jsonl`.

---

## 2. Source Manifest Schema (`stage8_16_source_manifest.json`)

The source manifest cryptographically locks the 6 original Stage 8.15 adjudication records prior to any correction actions.

**Path:** `data/reference/ds08/annotations/adjudication/stage8_16_source_manifest.json`

```json
{
  "manifest_version": "1.0",
  "created_at_utc": "2026-10-02T05:54:34.908861+00:00",
  "purpose": "Immutable baseline tracking for Stage 8.15 adjudication files before Stage 8.16 corrections",
  "files": {
    "PILOT_03_NORTH": {
      "filename": "PILOT_03_NORTH_adjudicated_v1.json",
      "path": "data/reference/ds08/annotations/adjudication/review/PILOT_03_NORTH_adjudicated_v1.json",
      "sha256": "dd1d1b427796a1bda6903d71a2d17841c215d2b6978463fb0560900b049aafaa"
    },
    "PILOT_06_CENTRAL": {
      "filename": "PILOT_06_CENTRAL_adjudicated_v1.json",
      "path": "data/reference/ds08/annotations/adjudication/review/PILOT_06_CENTRAL_adjudicated_v1.json",
      "sha256": "7b0cbb8eac28d2387c6f197e175f39f4653148d0e41006637864280138a949c9"
    },
    "PILOT_08_CENTRAL": {
      "filename": "PILOT_08_CENTRAL_adjudicated_v1.json",
      "path": "data/reference/ds08/annotations/adjudication/review/PILOT_08_CENTRAL_adjudicated_v1.json",
      "sha256": "3ad0384f37a4121950f1523ca711ca030f2028c20091934e7495d99b97a214d7"
    },
    "PILOT_15_EAST": {
      "filename": "PILOT_15_EAST_adjudicated_v1.json",
      "path": "data/reference/ds08/annotations/adjudication/review/PILOT_15_EAST_adjudicated_v1.json",
      "sha256": "1d4ba7f5ee6e16402533a58d6910503af13abffeca51de83e44015cda60abe3c"
    },
    "PILOT_16_EAST": {
      "filename": "PILOT_16_EAST_adjudicated_v1.json",
      "path": "data/reference/ds08/annotations/adjudication/review/PILOT_16_EAST_adjudicated_v1.json",
      "sha256": "5986b43675904a91d53184e3b57b67d8e759e2d6f8b7be3af483b3400af02264"
    },
    "PILOT_18_WEST": {
      "filename": "PILOT_18_WEST_adjudicated_v1.json",
      "path": "data/reference/ds08/annotations/adjudication/review/PILOT_18_WEST_adjudicated_v1.json",
      "sha256": "a88d245b12e0e6eddc833926d4928927b8835ee3b25ccbbb963fc9e844f51674"
    }
  }
}
```

---

## 3. Corrected Record Schema (`{chip_id}_corrected_v2.json`)

Each corrected file conforms to the JSON schema below.

### 3.1 Field Definitions

| Field | Type | Description | Mandatory |
|---|---|---|---|
| `chip_id` | string | Unique chip identifier (e.g. `PILOT_03_NORTH`) | Yes |
| `correction_version` | string | Fixed as `"v2.0"` | Yes |
| `stage` | string | Fixed as `"STAGE_8_16"` | Yes |
| `correction_status` | string | Fixed as `"COMPLETED_HUMAN_CORRECTION"` | Yes |
| `original_record_path` | string | Path to the immutable Stage 8.15 source record | Yes |
| `original_record_sha256` | string | SHA-256 hex digest of the source record | Yes |
| `corrected_consensus` | object | Consensus payload conforming to DS08 payload schema | Yes |
| `changed_fields` | list[string] | Array of field keys altered relative to source consensus | Yes |
| `diff_summary` | list[string] | Human-readable explanation lines of differences | Yes |
| `correction_rationale` | string | Substantive visual rationale (> 15 chars, non-generic) | Yes |
| `human_confirmation` | object | Confirmation object containing approval status | Yes |
| `correction_timestamp` | string | ISO 8601 UTC timestamp of correction | Yes |
| `record_sha256` | string | SHA-256 fingerprint computed over canonical JSON record | Yes |

### 3.2 `human_confirmation` Schema

```json
{
  "confirmed": true,
  "method": "HUMAN_CHECKBOX_CONFIRMATION",
  "statement": "I confirm that I have reviewed the Sentinel-2 imagery and explicitly approve these corrections."
}
```
*Note: Under no circumstances should this field claim biometric, hardware token, or cryptographic identity validation.*

### 3.3 `corrected_consensus` Schema

Complies with standard DS08 consensus annotation format:
- `chip_id`: string
- `annotation_version`: `"v2.0"`
- `chip_annotation_status`: `"HAS_ANNOTATIONS"` or `"NO_VISIBLE_TARGET"` (`UNRESOLVED` is strictly prohibited)
- `annotations`: array of bounding box objects (must be empty `[]` if status is `NO_VISIBLE_TARGET`, non-empty if `HAS_ANNOTATIONS`)
- `source_classes`: list of unique class names present
- `visual_evidence`: combined list of all unique evidence tags across boxes (defaults to `["NO_CLEAR_VISUAL_EVIDENCE"]` if empty)
- `visibility_status`: `"CLEAR"` | `"HAZY"` | `"OCCLUDED"` | `"PARTIALLY_OCCLUDED"`
- `geometry_confidence`: `"HIGH"` | `"MEDIUM"` | `"LOW"`
- `source_class_confidence`: `"HIGH"` | `"MEDIUM"` | `"LOW"`
- `context_metadata`: original chip contextual metadata dictionary

### 3.4 Bounding Box Object Specification

Each element in `annotations`:
```json
{
  "annotation_id": "PILOT_03_NORTH_CORR_01",
  "annotator_id": "HUMAN_ADJUDICATOR_CORRECTION",
  "review_status": "CORRECTED_V2",
  "class_name": "FOREST_FIRE",
  "class_id": 1,
  "bbox": {
    "x_min": 142,
    "y_min": 198,
    "x_max": 188,
    "y_max": 240
  },
  "geometry_confidence": "HIGH",
  "source_class_confidence": "HIGH",
  "visibility_status": "CLEAR",
  "firms_relationship": "INSIDE_OBJECT",
  "visual_evidence": [
    "DIRECT_FIRE_VISIBLE",
    "SWIR_HOTSPOT",
    "SMOKE_PLUME"
  ]
}
```

#### Geometry Validation Rules:
- $0 \le x_{min} < x_{max} \le 512$
- $0 \le y_{min} < y_{max} \le 512$
- $x_{max} - x_{min} \ge 4$
- $y_{max} - y_{min} \ge 4$
- Coordinates must NOT match forbidden default placeholder $[200, 200, 300, 300]$.

#### Visual Evidence Consistency Rules:
- A box CANNOT simultaneously contain `NO_CLEAR_VISUAL_EVIDENCE` and positive fire/burn tags (`DIRECT_FIRE_VISIBLE`, `BURN_SCAR_VISIBLE`).

---

## 4. Audit Log Schema (`stage8_16_audit_log.jsonl`)

Every API action (successful save, validation error, hash failure) is written as a JSON object on a single line in:
`data/reference/ds08/annotations/adjudication/corrections/stage8_16_audit_log.jsonl`

### Schema Definition:
```json
{
  "timestamp_utc": "2026-10-02T06:05:12.123456+00:00",
  "event_type": "SAVE_SUCCESS",
  "chip_id": "PILOT_03_NORTH",
  "success": true,
  "errors": [],
  "payload_summary": {
    "status": "HAS_ANNOTATIONS",
    "num_boxes": 1,
    "source_sha256": "dd1d1b427796a1bda6903d71a2d17841c215d2b6978463fb0560900b049aafaa"
  },
  "diff_summary": {
    "changed_fields": ["annotations[0].visual_evidence"],
    "summary": ["Box #1 Evidence: removed ['NO_CLEAR_VISUAL_EVIDENCE']"]
  }
}
```

### Event Types:
- `SAVE_SUCCESS`: Validated and successfully written to disk.
- `SAVE_REJECTED`: Validation failed (e.g. contradictory tags, missing checkbox, empty rationale, out-of-bounds coordinates).
- `INTEGRITY_ALERT`: Source record or baseline manifest tampering detected.
