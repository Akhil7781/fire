# DS08 Sentinel-2 Optical Pilot Dataset Package (v1.0.0)

**Dataset ID:** `ds08_pilot_v1`  
**Packaging Stage:** Stage 8.17  
**Creation Timestamp:** `2026-10-02T06:47:44.781291+00:00`  
**Total Chips:** 15 Level-2A Sentinel-2 chips ($512 \times 512$ pixels, 10m GSD)  

## 1. Cohort Composition
- **Total Chips:** 15
- **Positive Chips (`HAS_ANNOTATIONS`):** 6 (6 chips, 10 bounding boxes)
- **Negative Chips (`NO_VISIBLE_TARGET`):** 9 (9 chips, 0 bounding boxes)
- **Class Breakdown:**
  - `Forest Fire`: 9 boxes (across 5 chips)
  - `Agricultural Fire`: 1 box (across 1 chip)
  - `Industrial Fire`: 0 boxes
  - `Other Thermal Source`: 0 boxes

## 2. Provenance & Adjudication Traceability
- **9 Unanimous Chips (Stage 8.14):** Independently annotated by Annotator 1 and Annotator 2 with 100% agreement (`NO_VISIBLE_TARGET`).
- **6 Adjudicated Chips (Stage 8.16):** Human consensus adjudicated with explicit human confirmation and non-generic rationale.
- **5 Excluded Chips:** Reserved for single-annotation screening (`PILOT_01_NORTH`, `PILOT_05_CENTRAL`, `PILOT_09_SOUTH`, `PILOT_13_EAST`, `PILOT_17_WEST`).

## 3. Directory Layout
- `manifest.json`: Cryptographic manifest containing file paths, hashes, and provenance for all 15 chips.
- `manifest.csv`: Tabular metadata and file hash index.
- `annotations/`: JSON files adhering to `ds08_annotation_schema.json`.
- `chips/`: 5-band L2A Sentinel-2 GeoTIFF rasters (B02, B03, B04, B11, B12).
- `previews/`: RGB and SWIR PNG previews.
- `metadata/`: Scene acquisition, UTM coordinates, and FIRMS context metadata.
