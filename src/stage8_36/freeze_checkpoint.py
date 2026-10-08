"""Stage 8.36 Task 1: Final Checkpoint Freeze.

Copies and validates the immutable final model checkpoint, preprocessing scalers,
and feature schema from Stage 8.35 into models/stage8_36/.
"""

import hashlib
import json
import shutil
from pathlib import Path

PROJECT_ROOT = Path("d:/DATA PREPROCESSING")
SRC_DIR = PROJECT_ROOT / "models" / "stage8_35"
DST_DIR = PROJECT_ROOT / "models" / "stage8_36"

EXPECTED_CHECKPOINT_HASH = "5bdbfbd503a3c0acbd50caefd2b1c88b5e0190a7176d70a517165814722bcff2"

def compute_sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()

def freeze_checkpoint():
    DST_DIR.mkdir(parents=True, exist_ok=True)
    
    src_ckpt = SRC_DIR / "development_best_neural_model.pt"
    assert src_ckpt.exists(), f"Source checkpoint not found at {src_ckpt}"
    
    actual_src_hash = compute_sha256(src_ckpt)
    assert actual_src_hash == EXPECTED_CHECKPOINT_HASH, (
        f"Source checkpoint hash mismatch! Expected {EXPECTED_CHECKPOINT_HASH}, got {actual_src_hash}"
    )
    print(f"[FREEZE] Verified source checkpoint hash: {actual_src_hash}")
    
    # Copy model checkpoint
    dst_ckpt = DST_DIR / "final_neural_model.pt"
    shutil.copy2(src_ckpt, dst_ckpt)
    dst_hash = compute_sha256(dst_ckpt)
    assert dst_hash == EXPECTED_CHECKPOINT_HASH, f"Copied checkpoint hash mismatch! Got {dst_hash}"
    print(f"[FREEZE] Copied final neural model to {dst_ckpt} (Hash: {dst_hash})")
    
    # Save checkpoint hash file
    hash_file = DST_DIR / "checkpoint_hash.txt"
    hash_file.write_text(dst_hash, encoding="utf-8")
    print(f"[FREEZE] Saved checkpoint hash to {hash_file}")
    
    # Copy preprocessing scalers
    src_preproc = SRC_DIR / "preprocessing.pt"
    assert src_preproc.exists(), "Source preprocessing.pt not found"
    dst_preproc = DST_DIR / "preprocessing.pt"
    shutil.copy2(src_preproc, dst_preproc)
    print(f"[FREEZE] Copied preprocessing scalers to {dst_preproc}")
    
    # Copy and update model config
    src_config = SRC_DIR / "model_config.json"
    with open(src_config, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    cfg["stage"] = "8.36_final"
    cfg["checkpoint_file"] = "final_neural_model.pt"
    cfg["checkpoint_sha256"] = dst_hash
    cfg["deep_learning_only"] = True
    cfg["classical_ml_components"] = False
    
    dst_config = DST_DIR / "model_config.json"
    with open(dst_config, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
    print(f"[FREEZE] Saved final model config to {dst_config}")
    
    # Copy feature schema
    src_schema = SRC_DIR / "feature_schema.json"
    dst_schema = DST_DIR / "feature_schema.json"
    shutil.copy2(src_schema, dst_schema)
    print(f"[FREEZE] Copied feature schema to {dst_schema}")
    
    print("[FREEZE] Stage 8.36 Task 1 Checkpoint Freeze completed successfully.")

if __name__ == "__main__":
    freeze_checkpoint()
