import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.ds08_annotation_tool import (
    validate_annotation_payload,
    validate_manual_annotation_provenance,
    AFFECTED_15_CHIPS,
)

a1_dir = Path("data/reference/ds08/annotations/manual/annotator_1")
print("=== PHASE B AUDIT: ANNOTATOR 1 COMPLETENESS & SCHEMA ===")
all_valid = True
summary = []

for cid in AFFECTED_15_CHIPS:
    fpath = a1_dir / f"{cid}_annotator1.json"
    if not fpath.exists():
        print(f"MISSING: {fpath.name}")
        all_valid = False
        continue
    with open(fpath, "r", encoding="utf-8") as f:
        data = json.load(f)

    t_status = data.get("task_status")
    h_ver = data.get("human_verified")
    c_status = data.get("chip_annotation_status")
    audit = data.get("interaction_audit", {})
    anns = data.get("annotations", [])

    valid_schema, schema_errs = validate_annotation_payload(data)
    valid_prov, prov_errs = validate_manual_annotation_provenance(data)

    status_ok = (
        t_status == "COMPLETED_HUMAN_ANNOTATION"
        and h_ver is True
        and c_status in ["HAS_ANNOTATIONS", "NO_VISIBLE_TARGET", "UNRESOLVED"]
    )
    if not (status_ok and valid_schema and valid_prov):
        all_valid = False
        print(f"FAIL {cid}: status_ok={status_ok}, schema={valid_schema} ({schema_errs}), prov={valid_prov} ({prov_errs})")

    classes = [a.get("class_name") for a in anns]
    summary.append({
        "chip_id": cid,
        "status": c_status,
        "boxes": len(anns),
        "classes": classes,
        "save_events": audit.get("save_events", 0),
        "bbox_actions": audit.get("bbox_creation_actions", 0),
    })

res_str = "PASSED (15/15 valid)" if all_valid else "FAILED"
print(f"Audit Result: {res_str}")
print(f"Total Chips Verified: {len(summary)} / 15")
print("-" * 80)
for s in summary:
    print(f"  {s['chip_id']:<28} | Status: {s['status']:<18} | Boxes: {s['boxes']:<2} | Classes: {s['classes']}")
print("-" * 80)
