"""
Stage 8.34 Task 5: Trusted Development Cohort Generation Module.
Creates the canonical trusted development cohort parquet (N=131)
with event-level spatiotemporal grouping, macro-region assignment,
and label quality flags.
STRICT TEST LOCK: Never touches the frozen 2026 test set.
"""

import json
import sys
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path("d:/DATA PREPROCESSING")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.stage8_32.spatial_split import assign_spatial_regions

def build_trusted_development_cohort() -> pd.DataFrame:
    df_coh = pd.read_parquet(PROJECT_ROOT / "data" / "interim" / "ds08_stage8_25_multimodal_event_cohort.parquet")
    dev_coh = df_coh[df_coh["split"].isin(["train", "val"])].copy().reset_index(drop=True)
    assert len(dev_coh) == 131, f"Expected 131 events, got {len(dev_coh)}"
    assert "test" not in dev_coh["split"].values

    # Assign contiguous spatial regions
    dev_coh = assign_spatial_regions(dev_coh)

    # Load label quality audit flags
    p_lbl_audit = PROJECT_ROOT / "artifacts" / "stage8_34" / "label_quality_audit.csv"
    if p_lbl_audit.exists():
        df_lbl_audit = pd.read_csv(p_lbl_audit)
        flag_map = dict(zip(df_lbl_audit["event_id"], df_lbl_audit["label_quality_flag"]))
        dev_coh["label_quality_flag"] = dev_coh["event_id"].map(flag_map)
    else:
        dev_coh["label_quality_flag"] = "LABEL_CONFIDENT"

    # Load component grouping from Task 4
    p_comp = PROJECT_ROOT / "artifacts" / "stage8_34" / "event_overlap_components.json"
    if p_comp.exists():
        with open(p_comp, "r", encoding="utf-8") as f:
            components = json.load(f)
        comp_map = {}
        for c in components:
            cid = c["component_id"]
            for eid in c["event_ids"]:
                comp_map[eid] = cid
        dev_coh["spatial_component_id"] = dev_coh["event_id"].map(comp_map)
    else:
        dev_coh["spatial_component_id"] = 0

    # Build clean canonical trusted cohort dataframe
    trusted_df = pd.DataFrame({
        "event_id": dev_coh["event_id"],
        "split": dev_coh["split"],
        "spatial_region": dev_coh["spatial_region"],
        "year": dev_coh["year"].astype(int),
        "target_class": dev_coh["target_class"],
        "class_id": dev_coh["class_id"].astype(int),
        "centroid_lat": dev_coh["centroid_lat"].astype(float),
        "centroid_lon": dev_coh["centroid_lon"].astype(float),
        "detection_count": dev_coh["detection_count"].astype(int),
        "label_quality_flag": dev_coh["label_quality_flag"],
        "spatial_component_id": dev_coh["spatial_component_id"].astype(int)
    })

    out_path = PROJECT_ROOT / "artifacts" / "stage8_34" / "trusted_development_cohort.parquet"
    trusted_df.to_parquet(out_path, index=False)
    print(f"Saved trusted development cohort ({len(trusted_df)} events) to {out_path}.")
    return trusted_df

if __name__ == "__main__":
    build_trusted_development_cohort()
