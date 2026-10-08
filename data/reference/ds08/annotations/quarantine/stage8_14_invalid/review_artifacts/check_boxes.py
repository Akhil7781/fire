import json
from pathlib import Path

def box_iou(b1, b2):
    xi1 = max(b1['x_min'], b2['x_min'])
    yi1 = max(b1['y_min'], b2['y_min'])
    xi2 = min(b1['x_max'], b2['x_max'])
    yi2 = min(b1['y_max'], b2['y_max'])
    inter = max(0, xi2 - xi1) * max(0, yi2 - yi1)
    a1 = (b1['x_max'] - b1['x_min']) * (b1['y_max'] - b1['y_min'])
    a2 = (b2['x_max'] - b2['x_min']) * (b2['y_max'] - b2['y_min'])
    u = a1 + a2 - inter
    return inter / u if u > 0 else 0.0

a1_dir = Path("data/reference/ds08/annotations/manual/annotator_1")
a2_dir = Path("data/reference/ds08/annotations/manual/annotator_2")

for cid in ['PILOT_03_NORTH', 'PILOT_06_CENTRAL', 'PILOT_07_CENTRAL', 'PILOT_08_CENTRAL', 'PILOT_11_SOUTH', 'PILOT_14_EAST', 'PILOT_15_EAST', 'PILOT_16_EAST', 'PILOT_18_WEST', 'PILOT_19_WEST']:
    d1 = json.load(open(a1_dir / f"{cid}_annotator1.json", encoding="utf-8"))
    d2 = json.load(open(a2_dir / f"{cid}_annotator2.json", encoding="utf-8"))
    print("===" , cid, "===")
    print("A1 boxes:", len(d1['annotations']), "A2 boxes:", len(d2['annotations']))
    for i, a in enumerate(d1['annotations']):
        c1 = a['class_name']
        bb1 = a['bbox']
        for j, b in enumerate(d2['annotations']):
            c2 = b['class_name']
            bb2 = b['bbox']
            iou = box_iou(bb1, bb2)
            print(f"  IoU(A1#{i+1}:{c1}, A2#{j+1}:{c2}) = {iou:.4f} b1={bb1} b2={bb2}")
