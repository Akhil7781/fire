"""Generate annotation task manifest from the acquisition plan."""
import json
from collections import Counter
from pathlib import Path

ROOT = Path("d:/DATA PREPROCESSING")
plan_path = ROOT / "data/reference/ds08/ds08_acquisition_plan.json"
with open(plan_path, "r", encoding="utf-8") as f:
    plan = json.load(f)

scenes = plan.get("accepted_scenes", plan.get("scenes", []))

industrial   = [s for s in scenes if s["domain_type"] == "INDUSTRIAL"]
agricultural = [s for s in scenes if s["domain_type"] == "AGRICULTURAL"]
forest_sc    = [s for s in scenes if s["domain_type"] == "FOREST"]

# Scene-level split: exactly 34 train, 8 val, 8 test scenes (50 total)
# Industrial: 14 train, 3 val, 3 test (20 total)
# Agricultural: 14 train, 3 val, 3 test (or 15 train, 2 val, 3 test -> let's do 14 train, 3 val, 3 test)
# Forest: 6 train, 2 val, 2 test (10 total)
# 14 + 14 + 6 = 34 train; 3 + 3 + 2 = 8 val; 3 + 3 + 2 = 8 test. Total = 50.

def assign_fixed_split(scene_list, n_train, n_val, n_test):
    assert len(scene_list) == n_train + n_val + n_test
    splits = ["train"] * n_train + ["val"] * n_val + ["test"] * n_test
    return {s["scene_id"]: splits[i] for i, s in enumerate(scene_list)}

split_map = {}
split_map.update(assign_fixed_split(industrial, 14, 3, 3))
split_map.update(assign_fixed_split(agricultural, 14, 3, 3))
split_map.update(assign_fixed_split(forest_sc, 6, 2, 2))

tasks = []
for s in scenes:
    scene_split = split_map[s["scene_id"]]
    for chip_idx in range(s["target_chips"]):
        chip_id = f"{s['scene_id']}_chip{chip_idx:02d}"
        tasks.append({
            "chip_id": chip_id,
            "scene_id": s["scene_id"],
            "domain_type": s["domain_type"],
            "location_name": s["location_name"],
            "state": s["state"],
            "partition": scene_split,
            "sentinel2_product_id": s["sentinel2_product_id"],
            "tile_id": s["tile_id"],
            "sensing_date": s["sensing_date"],
            "bands": s["bands"],
            "lat_center": s["lat_center"],
            "lon_center": s["lon_center"],
            "annotation_branch": s["annotation_branch"],
            "image_status": "PENDING_DOWNLOAD",
            "annotation_status": "PENDING_ANNOTATION",
            "review_status": "PENDING_REVIEW",
            "image_path": f"data/reference/ds08/images/{chip_id}.png",
            "annotation_path_infra": (
                f"data/reference/ds08/annotations_infra/{chip_id}.txt"
                if s["annotation_branch"] in ("INFRA", "BOTH") else None
            ),
            "annotation_path_fire_smoke": (
                f"data/reference/ds08/annotations_fire_smoke/{chip_id}.txt"
                if s["annotation_branch"] in ("FIRE_SMOKE", "BOTH") else None
            ),
        })

split_counts  = Counter(t["partition"] for t in tasks)
domain_counts = Counter(t["domain_type"] for t in tasks)
split_domain  = {}
for t in tasks:
    split_domain.setdefault(t["partition"], Counter())[t["domain_type"]] += 1

manifest = {
    "manifest_version": "2.0_REAL_SENTINEL2_PENDING",
    "status": "ANNOTATION_PENDING",
    "total_candidate_chips": len(tasks),
    "split_counts": dict(split_counts),
    "domain_counts": dict(domain_counts),
    "split_domain_breakdown": {k: dict(v) for k, v in split_domain.items()},
    "split_scene_counts": {
        "train": sum(1 for s in scenes if split_map[s["scene_id"]] == "train"),
        "val":   sum(1 for s in scenes if split_map[s["scene_id"]] == "val"),
        "test":  sum(1 for s in scenes if split_map[s["scene_id"]] == "test"),
    },
    "screening_summary": plan.get("screening_audit", {}),
    "tasks": tasks,
}

out = ROOT / "data/reference/ds08/chips_pending_annotation/annotation_task_manifest.json"
out.parent.mkdir(parents=True, exist_ok=True)
with open(out, "w", encoding="utf-8") as f:
    json.dump(manifest, f, indent=2)

print("Annotation task manifest written.")
print(f"Total chips:  {len(tasks)}")
print(f"Splits:       {dict(split_counts)}")
print(f"Domains:      {dict(domain_counts)}")
print(f"Scene counts: {manifest['split_scene_counts']}")
print(f"Split x Domain: {manifest['split_domain_breakdown']}")
