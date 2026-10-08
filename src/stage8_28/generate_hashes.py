"""
Generates artifacts/stage8_28/artifact_hashes.json recording cryptographic SHA-256 hashes
for all frozen inputs, predecessor models, Stage 8.27 baselines, Stage 8.28 models, datasets, and reports.
"""

import hashlib
import json
from pathlib import Path

PROJECT_ROOT = Path("d:/DATA PREPROCESSING")

FILES_TO_HASH = [
    # 1. Frozen Independent Test Manifest & Catalogs
    "data/reference/ds08/manifests/stage8_25/independent_test_manifest.json",
    "data/interim/ds08_stage8_25_physical_events.parquet",
    "data/interim/ds08_stage8_25_multiyear_firms.parquet",
    "data/reference/ds08/manifests/stage8_25/industrial_facility_database.json",
    "data/reference/ds08/manifests/stage8_25/persistent_source_manifest.json",

    # 2. Frozen Predecessor Models
    "models/stage7a/best_tcn.pt",
    "models/stage7b/best_deep_sad.pt",
    "models/stage8_21/best_s2_encoder.pt",
    "models/stage6/best_infrastructure.pt",
    "models/stage6/best_fire_smoke.pt",
    "models/stage8_22/best_multimodal_fusion.pt",

    # 3. Stage 8.26 Clean Baselines
    "reports/stage8_26_audit_summary.json",
    "reports/stage8_26_forensic_audit_report.md",

    # 4. Stage 8.27 Artifacts
    "data/interim/ds08_stage8_27_causal_prefix_dataset.parquet",
    "data/interim/ds08_stage8_27_causal_features.parquet",
    "models/stage8_27/best_causal_temporal_encoder.pt",
    "models/stage8_27/best_hierarchical_causal_classifier.pt",
    "src/stage8_27/prefix_dataset.py",
    "src/stage8_27/train_and_evaluate.py",

    # 5. Stage 8.28 Code & Datasets
    "src/stage8_28/prefix_dataset.py",
    "src/stage8_28/models.py",
    "src/stage8_28/train_and_evaluate.py",
    "data/interim/ds08_stage8_28_causal_prefix_dataset.parquet",
    "data/interim/ds08_stage8_28_causal_features.parquet",

    # 6. Stage 8.28 Models
    "models/stage8_28/causal_temporal_encoder.pt",
    "models/stage8_28/causal_classifier.pt",
    "models/stage8_28/scaler.json",
    "models/stage8_28/metadata.json",

    # 7. Stage 8.28 Artifacts
    "artifacts/stage8_28/stage8_28_artifact_audit.json",
    "artifacts/stage8_28/causal_feature_audit.csv",
    "artifacts/stage8_28/horizon_prefix_audit.csv",
    "artifacts/stage8_28/facility_baseline_audit.csv",
    "artifacts/stage8_28/horizon_prediction_audit.csv",
    "artifacts/stage8_28/confusion_matrices.json",
    "artifacts/stage8_28/bootstrap_metrics.json",
    "artifacts/stage8_28/leakage_audit.json",
    "artifacts/stage8_28/stage8_28_summary.json"
]

def generate_hashes():
    hashes = {}
    for rel_path in FILES_TO_HASH:
        p = PROJECT_ROOT / rel_path
        if p.exists():
            h = hashlib.sha256(p.read_bytes()).hexdigest()
            size = p.stat().st_size
            hashes[rel_path] = {
                "exists": True,
                "sha256": h,
                "size_bytes": size
            }
        else:
            hashes[rel_path] = {
                "exists": False,
                "sha256": None,
                "size_bytes": None
            }

    out_path = PROJECT_ROOT / "artifacts" / "stage8_28" / "artifact_hashes.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(hashes, f, indent=2)
    print(f"Wrote {len(hashes)} artifact hashes to {out_path}")

if __name__ == "__main__":
    generate_hashes()
