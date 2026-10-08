"""
Stage 8.21 - Sentinel-2 Embedding Extraction Script
Generates deterministic 128D visual embeddings for every valid accepted Sentinel-2 chip.
Input: Normalized spectral arrays [5, 512, 512]
Output: data/interim/ds08_stage8_21_s2_embeddings.parquet (and json)
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any, Dict, List

import numpy as np
import pandas as pd
import torch

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.stage8_21.s2_encoder import Sentinel2Encoder

ANNOTATIONS_PARQUET = PROJECT_ROOT / "data" / "interim" / "ds08_stage8_21_review_annotations.parquet"
MODEL_CHECKPOINT = PROJECT_ROOT / "models" / "s2_encoder" / "best_s2_encoder.pt"
OUTPUT_EMBEDDINGS_PARQUET = PROJECT_ROOT / "data" / "interim" / "ds08_stage8_21_s2_embeddings.parquet"
OUTPUT_EMBEDDINGS_JSON = PROJECT_ROOT / "data" / "interim" / "ds08_stage8_21_s2_embeddings.json"


def extract_embeddings(
    annotations_path: Path = ANNOTATIONS_PARQUET,
    checkpoint_path: Path = MODEL_CHECKPOINT,
    output_parquet: Path = OUTPUT_EMBEDDINGS_PARQUET,
    output_json: Path = OUTPUT_EMBEDDINGS_JSON,
    device: str = "cpu",
) -> pd.DataFrame:
    print("=" * 80)
    print("STAGE 8.21: SENTINEL-2 128D EMBEDDING EXTRACTION")
    print("=" * 80)

    # 1. Load model checkpoint
    if not checkpoint_path.exists():
        raise FileNotFoundError(f"Model checkpoint not found: {checkpoint_path}")

    model = Sentinel2Encoder.load_checkpoint(checkpoint_path)
    model.to(device)
    model.eval()
    print(f"Loaded Sentinel2Encoder checkpoint from: {checkpoint_path}")

    # 2. Load reviewed annotations
    df_ann = pd.read_parquet(annotations_path)
    print(f"Processing {len(df_ann)} reviewed chips...")

    records = df_ann.to_dict(orient="records")
    embedding_rows = []

    with torch.no_grad():
        for r in records:
            sid = r["sample_id"]
            norm_path = PROJECT_ROOT / r["normalized_path"]

            arr = np.load(norm_path).astype(np.float32)  # (5, 512, 512)
            tensor_x = torch.from_numpy(arr).unsqueeze(0).to(device)  # (1, 5, 512, 512)

            # Deterministic inference
            z = model(tensor_x, normalize=True)  # (1, 128)
            emb_vec = z.squeeze(0).cpu().numpy().tolist()

            # Integrity checks
            assert len(emb_vec) == 128, f"Expected 128 dimensions, got {len(emb_vec)}"
            assert not np.isnan(emb_vec).any(), f"NaN detected in embedding for {sid}"
            assert not np.isinf(emb_vec).any(), f"Inf detected in embedding for {sid}"

            row = {
                "sample_id": sid,
                "acquisition_timestamp": r["acquisition_timestamp"],
                "latitude": float(r["latitude"]),
                "longitude": float(r["longitude"]),
                "product_id": r["source_product"],
                "human_observed_class": r["human_observed_class"],
                "label_status": r["label_status"],
            }

            # Add each dimension
            for i, val in enumerate(emb_vec):
                row[f"dim_{i:03d}"] = float(val)

            embedding_rows.append(row)
            print(f"  Extracted 128D embedding for {sid} ({r['human_observed_class']}) - norm: {np.linalg.norm(emb_vec):.4f}")

    df_emb = pd.DataFrame(embedding_rows)

    # Save Parquet
    output_parquet.parent.mkdir(parents=True, exist_ok=True)
    df_emb.to_parquet(output_parquet, index=False)

    # Save JSON
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(embedding_rows, f, indent=2)

    print(f"\nSaved {len(df_emb)} embeddings to:")
    print(f"  Parquet: {output_parquet}")
    print(f"  JSON:    {output_json}")
    return df_emb


if __name__ == "__main__":
    extract_embeddings()
