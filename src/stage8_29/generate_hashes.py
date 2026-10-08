"""
Generates artifacts/stage8_29/artifact_hashes.json recording cryptographic SHA-256 hashes
for all Stage 8.28 frozen baselines, Stage 8.29 audit tables, provenance docs, and reports.
"""

import hashlib
import json
from pathlib import Path

PROJECT_ROOT = Path("d:/DATA PREPROCESSING")

FILES_TO_HASH = [
    # 1. Frozen Test Manifest & Registry
    "data/reference/ds08/manifests/stage8_25/independent_test_manifest.json",
    "data/reference/ds08/manifests/stage8_25/persistent_source_manifest.json",
    "data/reference/ds08/manifests/stage8_25/industrial_facility_database.json",

    # 2. Frozen Stage 8.28 Checkpoints
    "models/stage8_28/causal_temporal_encoder.pt",
    "models/stage8_28/causal_classifier.pt",
    "models/stage8_28/scaler.json",
    "models/stage8_28/metadata.json",
    "artifacts/stage8_28/stage8_28_summary.json",
    "artifacts/stage8_28/stage8_28_final_report.md",

    # 3. Stage 8.29 Code
    "src/stage8_29/experiments.py",

    # 4. Stage 8.29 Audit & Result Artifacts
    "artifacts/stage8_29/persistent_registry_provenance.md",
    "artifacts/stage8_29/registry_target_proxy_audit.csv",
    "artifacts/stage8_29/temporal_loss_audit.csv",
    "artifacts/stage8_29/no_registry_horizon_results.csv",
    "artifacts/stage8_29/prediction_flip_analysis.csv",
    "artifacts/stage8_29/stage8_29_summary.json"
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

    out_path = PROJECT_ROOT / "artifacts" / "stage8_29" / "artifact_hashes.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(hashes, f, indent=2)
    print(f"Wrote {len(hashes)} artifact hashes to {out_path}")

if __name__ == "__main__":
    generate_hashes()
