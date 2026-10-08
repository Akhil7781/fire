import json
import math
from pathlib import Path
from collections import Counter
import sys

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.ds08_annotation_tool import (
    validate_annotation_payload,
    validate_manual_annotation_provenance,
    AFFECTED_15_CHIPS,
)

a1_dir = Path("data/reference/ds08/annotations/manual/annotator_1")
a2_dir = Path("data/reference/ds08/annotations/manual/annotator_2")

def box_iou(b1, b2):
    # b: {x_min, y_min, x_max, y_max}
    xi1 = max(b1["x_min"], b2["x_min"])
    yi1 = max(b1["y_min"], b2["y_min"])
    xi2 = min(b1["x_max"], b2["x_max"])
    yi2 = min(b1["y_max"], b2["y_max"])
    inter_w = max(0, xi2 - xi1)
    inter_h = max(0, yi2 - yi1)
    inter_area = inter_w * inter_h
    
    b1_area = (b1["x_max"] - b1["x_min"]) * (b1["y_max"] - b1["y_min"])
    b2_area = (b2["x_max"] - b2["x_min"]) * (b2["y_max"] - b2["y_min"])
    union_area = b1_area + b2_area - inter_area
    if union_area <= 0:
        return 0.0
    return inter_area / union_area

def jaccard(set1, set2):
    s1, s2 = set(set1), set(set2)
    if not s1 and not s2:
        return 1.0
    if not s1 or not s2:
        return 0.0
    return len(s1 & s2) / len(s1 | s2)

# Inspect all chips
records = []
all_matched_ious = []
all_evidence_jaccards = []
vis_agreements = []
geom_conf_agreements = []
class_conf_agreements = []

a1_primary_classes = []
a2_primary_classes = []

for cid in AFFECTED_15_CHIPS:
    f1 = a1_dir / f"{cid}_annotator1.json"
    f2 = a2_dir / f"{cid}_annotator2.json"
    d1 = json.load(open(f1, "r", encoding="utf-8"))
    d2 = json.load(open(f2, "r", encoding="utf-8"))
    
    s1 = d1.get("chip_annotation_status")
    s2 = d2.get("chip_annotation_status")
    anns1 = d1.get("annotations", [])
    anns2 = d2.get("annotations", [])
    
    # Primary class determination:
    # If NO_VISIBLE_TARGET -> "NO_VISIBLE_TARGET"
    # If UNRESOLVED -> "UNRESOLVED"
    # If HAS_ANNOTATIONS: most common class in annotations (or unique if 1)
    c1_cls = s1 if s1 != "HAS_ANNOTATIONS" else (anns1[0]["class_name"] if len(anns1) > 0 else "UNKNOWN")
    c2_cls = s2 if s2 != "HAS_ANNOTATIONS" else (anns2[0]["class_name"] if len(anns2) > 0 else "UNKNOWN")
    
    a1_primary_classes.append(c1_cls)
    a2_primary_classes.append(c2_cls)
    
    # Bounding box matching (Greedy best-IoU)
    matched_pairs = []
    used2 = set()
    for i, b1 in enumerate(anns1):
        best_iou = -1.0
        best_j = -1
        for j, b2 in enumerate(anns2):
            if j in used2:
                continue
            iou = box_iou(b1["bbox"], b2["bbox"])
            if iou > best_iou:
                best_iou = iou
                best_j = j
        if best_j >= 0 and best_iou >= 0.1: # loose match threshold for analysis
            used2.add(best_j)
            matched_pairs.append((b1, anns2[best_j], best_iou))
            all_matched_ious.append(best_iou)
            
            # Evidence similarity
            ev_j = jaccard(b1.get("visual_evidence", []), anns2[best_j].get("visual_evidence", []))
            all_evidence_jaccards.append(ev_j)
            
            # Visibility agreement
            vis_agreements.append(1 if b1.get("visibility_status") == anns2[best_j].get("visibility_status") else 0)
            
            # Confidence agreement
            geom_conf_agreements.append(1 if b1.get("geometry_confidence") == anns2[best_j].get("geometry_confidence") else 0)
            class_conf_agreements.append(1 if b1.get("source_class_confidence") == anns2[best_j].get("source_class_confidence") else 0)
    
    # Chip-level evidence jaccard (if both NO_VISIBLE_TARGET, 1.0)
    if s1 == "NO_VISIBLE_TARGET" and s2 == "NO_VISIBLE_TARGET":
        chip_ev_j = 1.0
        all_evidence_jaccards.append(chip_ev_j)
        vis_agreements.append(1)
        geom_conf_agreements.append(1)
        class_conf_agreements.append(1)
    
    # Disagreements
    disagreements = []
    if s1 != s2:
        disagreements.append(f"STATUS_DISCREPANCY ({s1} vs {s2})")
    elif c1_cls != c2_cls:
        disagreements.append(f"CLASS_MISMATCH ({c1_cls} vs {c2_cls})")
    
    if len(anns1) != len(anns2):
        disagreements.append(f"BOX_COUNT_MISMATCH ({len(anns1)} vs {len(anns2)})")
        
    for p1, p2, iou in matched_pairs:
        if p1.get("class_name") != p2.get("class_name"):
            disagreements.append(f"BOX_CLASS_MISMATCH ({p1.get('class_name')} vs {p2.get('class_name')})")
        if jaccard(p1.get("visual_evidence", []), p2.get("visual_evidence", [])) < 1.0:
            disagreements.append("EVIDENCE_DIVERGENCE")
        if p1.get("visibility_status") != p2.get("visibility_status"):
            disagreements.append("VISIBILITY_MISMATCH")
            
    if s1 == "UNRESOLVED" or s2 == "UNRESOLVED":
        disagreements.append("UNRESOLVED_CHIP")
        
    req_adj = bool(disagreements and (s1 != s2 or c1_cls != c2_cls or len(anns1) != len(anns2) or s1 == "UNRESOLVED" or s2 == "UNRESOLVED"))
    
    mean_iou_chip = (sum(p[2] for p in matched_pairs) / len(matched_pairs)) if matched_pairs else None
    
    records.append({
        "chip_id": cid,
        "a1_status": s1,
        "a2_status": s2,
        "a1_primary_class": c1_cls,
        "a2_primary_class": c2_cls,
        "a1_box_count": len(anns1),
        "a2_box_count": len(anns2),
        "matched_boxes": len(matched_pairs),
        "mean_chip_iou": mean_iou_chip,
        "disagreements": sorted(list(set(disagreements))),
        "requires_adjudication": req_adj,
        "a1_details": d1,
        "a2_details": d2
    })

# Compute Cohen's Kappa over primary classes across all 15 chips
categories = sorted(list(set(a1_primary_classes + a2_primary_classes)))
cat_idx = {c: i for i, c in enumerate(categories)}
n = len(AFFECTED_15_CHIPS)
conf_matrix = [[0]*len(categories) for _ in range(len(categories))]
agree_count = 0
for c1, c2 in zip(a1_primary_classes, a2_primary_classes):
    conf_matrix[cat_idx[c1]][cat_idx[c2]] += 1
    if c1 == c2:
        agree_count += 1

po = agree_count / n
pe = sum(sum(conf_matrix[i][j] for j in range(len(categories))) * sum(conf_matrix[k][i] for k in range(len(categories))) for i in range(len(categories))) / (n * n)
kappa = (po - pe) / (1 - pe) if (1 - pe) > 0 else 1.0

mean_iou = (sum(all_matched_ious) / len(all_matched_ious)) if all_matched_ious else 0.0
sorted_ious = sorted(all_matched_ious)
median_iou = sorted_ious[len(sorted_ious)//2] if sorted_ious else 0.0
min_iou = min(sorted_ious) if sorted_ious else 0.0
max_iou = max(sorted_ious) if sorted_ious else 0.0

mean_ev_jaccard = (sum(all_evidence_jaccards) / len(all_evidence_jaccards)) if all_evidence_jaccards else 0.0
vis_agree_pct = (sum(vis_agreements) / len(vis_agreements) * 100.0) if vis_agreements else 100.0
geom_conf_pct = (sum(geom_conf_agreements) / len(geom_conf_agreements) * 100.0) if geom_conf_agreements else 100.0
class_conf_pct = (sum(class_conf_agreements) / len(class_conf_agreements) * 100.0) if class_conf_agreements else 100.0

adj_count = sum(1 for r in records if r["requires_adjudication"])
adj_chips = [r["chip_id"] for r in records if r["requires_adjudication"]]

print(f"=== STAGE 8.14 AGREEMENT ANALYSIS SUMMARY ===")
print(f"Total Chips Evaluated: {n}")
print(f"Primary Class Agreement: {agree_count}/{n} ({po*100:.1f}%)")
print(f"Cohen's Kappa: {kappa:.4f} (Po={po:.4f}, Pe={pe:.4f})")
print(f"Matched BBoxes Count: {len(all_matched_ious)}")
print(f"Mean Matched IoU: {mean_iou:.4f}")
print(f"Median Matched IoU: {median_iou:.4f} (Min: {min_iou:.4f}, Max: {max_iou:.4f})")
print(f"Mean Evidence Jaccard: {mean_ev_jaccard:.4f}")
print(f"Visibility Agreement: {vis_agree_pct:.1f}%")
print(f"Confidence Agreement (Geometry): {geom_conf_pct:.1f}%")
print(f"Confidence Agreement (Class): {class_conf_pct:.1f}%")
print(f"Chips Requiring Adjudication: {adj_count} / {n}")
print(f"Adjudication List: {adj_chips}")
print("-" * 80)
for r in records:
    iou_str = f"{r['mean_chip_iou']:.3f}" if r['mean_chip_iou'] is not None else "N/A"
    dis_str = ", ".join(r['disagreements']) if r['disagreements'] else "NONE (Full concordance)"
    print(f"{r['chip_id']:<28} | A1: {r['a1_primary_class']:<18} ({r['a1_box_count']}b) | A2: {r['a2_primary_class']:<18} ({r['a2_box_count']}b) | IoU: {iou_str} | Adj: {'YES' if r['requires_adjudication'] else 'NO'} | {dis_str}")
