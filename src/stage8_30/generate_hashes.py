"""
Generate SHA-256 hashes for Stage 8.30 artifacts and frozen predecessors.
"""

import hashlib
import json
from pathlib import Path

PROJECT_ROOT = Path("d:/DATA PREPROCESSING")

FILES_TO_HASH = [
    # Frozen Predecessors
    "data/reference/ds08/manifests/stage8_25/independent_test_manifest.json",
    "data/reference/ds08/manifests/stage8_25/industrial_facility_database.json",
    "models/stage8_28/causal_temporal_encoder.pt",
    "models/stage8_28/causal_classifier.pt",
    "artifacts/stage8_28/causal_feature_audit.csv",
    "artifacts/stage8_29/stage8_29_summary.json",
    "artifacts/stage8_29/stage8_29_final_report.md",
    "artifacts/stage8_29/no_registry_horizon_results.csv",
    # Stage 8.30 Interim Datasets
    "data/interim/ds08_stage8_30_causal_prefix_dataset.parquet",
    "data/interim/ds08_stage8_30_causal_features.parquet",
    "data/interim/ds08_stage8_30_historical_sequences.parquet",
    # Stage 8.30 Models
    "models/stage8_30/historical_recurrence_encoder.pt",
    "models/stage8_30/registry_free_causal_classifier.pt",
    "models/stage8_30/scaler.json",
    "models/stage8_30/metadata.json",
    # Stage 8.30 Artifacts
    "artifacts/stage8_30/stage8_30_summary.json",
    "artifacts/stage8_30/stage8_30_final_report.md",
    "artifacts/stage8_30/ablation_results.csv",
    "artifacts/stage8_30/multi_horizon_results.csv",
    "artifacts/stage8_30/prediction_flip_analysis.csv",
    "artifacts/stage8_30/error_analysis.csv",
    "artifacts/stage8_30/feature_provenance.csv",
    "artifacts/stage8_30/historical_feature_audit.csv",
    "artifacts/stage8_30/historical_sequence_audit.csv",
    "artifacts/stage8_30/bootstrap_metrics.json",
]

def hash_file(filepath: Path) -> dict:
    if not filepath.exists():
        return {"exists": False, "sha256": None, "size_bytes": 0}
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return {
        "exists": True,
        "sha256": h.hexdigest(),
        "size_bytes": filepath.stat().st_size
    }

def main():
    hashes = {}
    for rel_path in FILES_TO_HASH:
        p = PROJECT_ROOT / rel_path
        info = hash_file(p)
        hashes[rel_path.replace("\\", "/")] = info
        print(f"{rel_path}: {'FOUND' if info['exists'] else 'MISSING'} - {info['sha256']}")

    out_path = PROJECT_ROOT / "artifacts" / "stage8_30" / "artifact_hashes.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(hashes, f, indent=2)
    print(f"\nSaved {len(hashes)} hashes to {out_path}")

if __name__ == "__main__":
    main()
