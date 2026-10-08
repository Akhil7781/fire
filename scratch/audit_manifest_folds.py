import json
from collections import Counter

p = "data/reference/ds08/manifests/stage8_19/ds08_expansion_candidates_v1.json"
with open(p, "r", encoding="utf-8") as f:
    d = json.load(f)
records = d["records"]

folds = ["Fold 1", "Fold 2", "Fold 3", "Fold 4", "Fold 5", "BENCHMARK_HELD_OUT"]
strata = ["STR-1", "STR-2", "STR-3", "STR-4", "STR-5", "STR-6", "STR-7"]

grid = {s: {f: 0 for f in folds} for s in strata}
for r in records:
    grid[r["stratum_id"]][r["assigned_fold"]] += 1

hdr = f"{'Stratum':<10} | " + " | ".join(f"{f:<10}" for f in folds) + " | Total"
print(hdr)
print("-" * len(hdr))
for s in strata:
    row_sum = sum(grid[s][f] for f in folds)
    row_str = f"{s:<10} | " + " | ".join(f"{grid[s][f]:<10}" for f in folds) + f" | {row_sum}"
    print(row_str)
print("-" * len(hdr))
col_totals = [sum(grid[s][f] for s in strata) for f in folds]
tot_str = f"{'TOTAL':<10} | " + " | ".join(f"{tot:<10}" for tot in col_totals) + f" | {sum(col_totals)}"
print(tot_str)
