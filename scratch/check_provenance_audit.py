"""Audit manual workspace files for Stage 8.14 provenance preconditions."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
A1_DIR = ROOT / "data" / "reference" / "ds08" / "annotations" / "manual" / "annotator_1"
A2_DIR = ROOT / "data" / "reference" / "ds08" / "annotations" / "manual" / "annotator_2"

ALLOWED_STATUSES = ["HAS_ANNOTATIONS", "NO_VISIBLE_TARGET", "UNRESOLVED"]


def audit_file(p: Path):
    d = json.load(open(p, encoding="utf-8"))
    cid = d.get("chip_id", p.name)
    fails = []

    t_status = d.get("task_status")
    if t_status != "COMPLETED_HUMAN_ANNOTATION":
        fails.append(f"task_status='{t_status}' (expected 'COMPLETED_HUMAN_ANNOTATION')")

    h_ver = d.get("human_verified")
    if h_ver is not True:
        fails.append(f"human_verified={h_ver} (expected True)")

    c_status = d.get("chip_annotation_status")
    if c_status not in ALLOWED_STATUSES:
        fails.append(f"chip_annotation_status={c_status} (expected one of {ALLOWED_STATUSES})")

    audit = d.get("interaction_audit")
    if not audit:
        fails.append("interaction_audit missing")
    else:
        saves = audit.get("save_events", 0)
        if saves < 1:
            fails.append(f"save_events={saves} (expected >= 1)")

    comp_ts = d.get("annotation_completion_timestamp")
    if not comp_ts:
        fails.append("annotation_completion_timestamp missing or null")

    return cid, len(fails) == 0, fails


def main():
    print("=== A1 PROVENANCE AUDIT ===")
    a1_passes = []
    a1_fails = []
    for f in sorted(A1_DIR.glob("*.json")):
        cid, passed, reasons = audit_file(f)
        if passed:
            a1_passes.append(cid)
            print(f"PASS: {cid}")
        else:
            a1_fails.append((cid, reasons))
            print(f"FAIL: {cid} -> {', '.join(reasons)}")

    print(f"\nA1 Summary: {len(a1_passes)} / 15 passed, {len(a1_fails)} / 15 failed.")

    print("\n=== A2 PROVENANCE AUDIT ===")
    a2_passes = []
    a2_fails = []
    for f in sorted(A2_DIR.glob("*.json")):
        cid, passed, reasons = audit_file(f)
        if passed:
            a2_passes.append(cid)
            print(f"PASS: {cid}")
        else:
            a2_fails.append((cid, reasons))
            print(f"FAIL: {cid} -> {', '.join(reasons)}")

    print(f"\nA2 Summary: {len(a2_passes)} / 15 passed, {len(a2_fails)} / 15 failed.")

    total_passed = len(a1_passes) + len(a2_passes)
    print(f"\nOVERALL: {total_passed} / 30 passed precondition.")


if __name__ == "__main__":
    main()
