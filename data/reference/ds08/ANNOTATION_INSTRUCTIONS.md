# DS_08 Human Annotation Instructions
## Indian-Domain Sentinel-2 Optical Adaptation Dataset

**Version:** 1.0 | **Date:** 2026-09-25 | **Status:** ANNOTATION TASK OPEN  
**Project:** Satellite Thermal Anomaly Classification (VIIRS NOAA-20, India 2025)  
**Annotation Schema:** `data/reference/ds08/annotation_schema.json`  
**Tool:** CVAT / Label Studio / Roboflow (any YOLO-export-compatible tool)

---

## Critical Rules (Read Before Annotating)

> [!CAUTION]
> 1. **Only annotate what you can see.** If an object is not clearly visible in the optical chip, do NOT create a bounding box for it, even if you know it exists at that location.
> 2. **FIRMS proximity is not evidence.** Do not annotate a "fire" because VIIRS or FIRMS reported a thermal anomaly nearby. Annotate only what you observe optically.
> 3. **Mark uncertain objects as UNCERTAIN.** Never convert uncertainty into a positive label to increase dataset size.
> 4. **Do not copy coordinates from any other dataset.** All boxes must originate from your own visual inspection.
> 5. **Infrastructure ≠ Industrial fire.** You are annotating object classes (tank, chimney, shed, flame, smoke). You are NOT labeling whether a fire is "industrial" or "agricultural." That attribution is resolved downstream.

---

## PART A — YOLOv8n-Infra Branch (Industrial Scenes Only)

Apply to chips with `domain_type = INDUSTRIAL`  
**Annotation directory:** `data/reference/ds08/annotations_infra/`

### Class 0: Storage_Tank

**What to look for:**
- Circular or cylindrical structures at refinery/industrial sites
- Bright metallic rooftops or shadow halos (sun-side bright, opposite-side shadow arc)
- Typically clustered in tank farm groups
- At 10m/pixel: small circles 2–15 pixels in diameter
- May appear as a regular grid of circular features

**Confirmed positive label when:**
- Shape is clearly circular or elliptical
- Located within an industrial estate or refinery perimeter
- Metallic reflectance or characteristic shadow pattern visible

**Do NOT annotate:**
- Agricultural irrigation tanks or ponds
- Water reservoirs / check dams
- Circular road features
- Bus shelters or round-roof buildings
- Any feature outside an industrial context

**Box guidance:**
- Draw box tightly around the cylindrical tank footprint
- Include the shadow halo if the tank body is ambiguous
- One box per tank; do NOT group adjacent tanks into one box

---

### Class 1: Chimney_Stack

**What to look for:**
- Very narrow vertical structure with a long directional shadow
- Shadow extends from a point/small-area base in the sun's direction
- Often co-located with power plants, boiler houses, cement factories
- At 10m/pixel: appears as 1–3 pixel bright spot with elongated shadow

**Confirmed positive label when:**
- Shadow direction consistent with solar azimuth for acquisition time
- Shadow length consistent with a tall structure (>20m)
- Located within an industrial area with process units nearby

**Do NOT annotate:**
- Radio/TV towers (very thin aspect, no thermal purpose)
- Electric transmission towers (characteristic shape, not co-located with process units)
- Any structure without confirmed industrial exhaust purpose

**Box guidance:**
- Box must enclose the stack base and the visible stack top if resolvable
- Include a small portion of shadow to help locate the base
- Minimum box: 4×4 pixels

---

### Class 2: Industrial_Shed

**What to look for:**
- Large rectangular building footprint with uniform roof surface
- At 10m/pixel: rectangle of 5–30 pixels length, 2–10 pixels width
- Often has a slightly brighter ridgeline or central shadow line
- Located within industrial estates; NOT isolated or in agricultural context

**Confirmed positive label when:**
- Clearly rectangular footprint
- Located inside an industrial zone (adjacent to other industrial infrastructure)
- Roof texture is uniform (sheet metal or concrete, not tiled residential)

**Do NOT annotate:**
- Commercial warehouses outside industrial zones
- Residential apartment blocks or school buildings
- Agricultural storage sheds in farming areas
- Any structure in non-industrial land use

**Box guidance:**
- Box should enclose the full roof footprint
- Do NOT include adjacent parking areas or yards
- Group only if physically connected (one building = one box)

---

## PART B — YOLOv8n-Fire/Smoke Branch (Agricultural and Forest Scenes)

Apply to chips with `domain_type = AGRICULTURAL` or `FOREST`  
**Annotation directory:** `data/reference/ds08/annotations_fire_smoke/`  
**Chips use false-color SWIR composite (bands B12-B11-B04):** Active fires appear bright red/orange in B12 channel.

### Class 0: Flame_Front

**What to look for in SWIR composite:**
- Bright saturated red/orange/white pixels at the fire location (B12 > 0.5)
- Sharp boundary on one side (active burning front), ash/char on the other
- In true-color (B04-B03-B02): May be dark (charred area) with bright edge
- Located at vegetation zone boundaries (field edges, forest margins)

**Confirmed positive label when:**
- B12 band clearly saturated (bright red in false-color) at the feature location
- Feature is at a vegetation/cropland area (not desert or urban)
- B11 also elevated (thermal consistency)
- Pattern consistent with a propagating fire front (not point source)

**Do NOT annotate:**
- Bare agricultural soil with natural high B12 response
- Urban heat islands
- Industrial thermal plumes (these are Infra-branch features, covered separately)
- Any bright SWIR feature in a non-vegetated context
- Historical burn scars (dark B04, not bright B12)

**Box guidance:**
- Draw box tightly around the actively burning pixels (bright B12 zone)
- Do NOT extend box into the smoke plume area above the fire
- One box per contiguous fire front segment; separate disjoint fires as separate boxes

---

### Class 1: Smoke_Plume

**What to look for in true-color or SWIR:**
- Grayish-white semi-opaque layer extending from a fire source
- Origin point anchored at or near a confirmed burn/fire location
- Extends downwind in a characteristic fan or ribbon shape
- Brownish tint from aerosol loading (distinguishes from white clouds)
- Reduces surface reflectance beneath it (can see ground through thin plume)

**Confirmed positive label when:**
- Clear spatial continuity from a fire/burn area
- Plume direction consistent with prevailing wind at time of acquisition
- Gradual opacity reduction from source to distal end
- Brownish or grayish tint (not pure white as clouds)

**Do NOT annotate:**
- White cirrus or cumulus clouds (sharp defined edges, no ground source anchor)
- Low fog or mist (uniform layer, no point-source origin)
- Industrial steam from cooling towers (unless co-located with fire evidence)
- Haze blanketing the entire scene without identifiable source

**Box guidance:**
- Box should enclose the visible plume extent
- Include the near-source dense zone and the thinner distal extension if visible
- One box per distinct plume; separate parallel plumes as separate boxes
- If plume extends beyond chip boundary, draw box up to the chip edge

---

## Annotation Record Fields

For every box you create, record:

| Field | Required | Description |
|---|:---:|---|
| `image_id` | ✅ | Chip filename without extension |
| `scene_id` | ✅ | Parent scene ID from acquisition plan |
| `annotation_id` | ✅ | Unique UUID (auto-generated by tool) |
| `branch` | ✅ | `YOLOv8n-Infra` or `YOLOv8n-Fire_Smoke` |
| `class_id` | ✅ | Integer class ID per branch mapping |
| `class_name` | ✅ | `Storage_Tank`, `Chimney_Stack`, etc. |
| `x_center_norm` | ✅ | Normalized [0, 1] |
| `y_center_norm` | ✅ | Normalized [0, 1] |
| `width_norm` | ✅ | Normalized [0, 1], positive |
| `height_norm` | ✅ | Normalized [0, 1], positive |
| `class_confidence` | ✅ | `CONFIRMED` / `UNCERTAIN` / `REJECTED` |
| `annotator_id` | ✅ | Your annotator identifier |
| `annotation_timestamp_utc` | ✅ | ISO 8601 timestamp |
| `reviewer_id` | Recommended | QC reviewer's ID (must differ from annotator) |
| `review_decision` | Recommended | `APPROVED` / `REVISED` / `REJECTED` |
| `visual_evidence_notes` | ✅ | Brief description of what you observed |
| `tool_used` | ✅ | Annotation tool name + version |

---

## Quality Control Protocol

1. **Self-review:** After annotating a chip, re-examine each box you drew and confirm it satisfies the visual evidence criteria above.
2. **Second-review:** A second annotator (or the same annotator after ≥24h break) should review each chip and mark each box as APPROVED, REVISED, or REJECTED.
3. **UNCERTAIN boxes:** These must NOT enter the training set. Keep them in the annotation files but flag them for optional human re-review in a future pass.
4. **Minimum box size:** 4×4 pixels. Any smaller box is ambiguous at 10m GSD.
5. **IOU overlap:** If two boxes for the same class overlap by >50%, merge them or reject the smaller one.

---

## Annotation Tools Recommended

- **CVAT** (https://cvat.org/) — open source, supports YOLO export
- **Label Studio** (https://labelstud.io/) — open source, flexible
- **Roboflow** (https://roboflow.com/) — web-based, direct YOLO training integration
- **VGG Image Annotator (VIA)** — simple browser-based, CSV export

Export format: **YOLO TXT** (one `.txt` file per image, same stem as image filename).

---

## Chips Requiring Annotation

Chips are listed in:  
`data/reference/ds08/chips_pending_annotation/annotation_task_manifest.json`

This file lists every chip requiring annotation, its parent scene, domain type, annotation branch, and split assignment.

**STOP:** Do not begin annotation until real Sentinel-2 images have been downloaded and chips extracted. See `data/reference/ds08/ds08_acquisition_plan.json` for download instructions.
