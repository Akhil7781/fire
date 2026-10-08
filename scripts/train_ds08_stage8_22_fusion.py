"""
Stage 8.22: Multimodal Late-Fusion Pipeline Runner Script.
Executes:
1. Training of MultimodalLateFusionMLP on the labeled modeling cohort.
2. Baselines evaluation (Phase F).
3. Ablation study (Phase G).
4. Leave-one-modality-out interpretability analysis (Phase I).
5. Persistence integration and prediction explanations (Phase H & J).
6. Serializing all artifacts into models/fusion/.
"""

import json
from pathlib import Path
import sys
import pandas as pd
import torch

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.stage8_22.evaluation import (
    MultimodalFusionDataset,
    compute_modality_importance,
    generate_prediction_record,
    run_baselines_and_ablations,
    train_fusion_model,
)

LABELED_DATA_PATH = PROJECT_ROOT / "data" / "interim" / "ds08_stage8_22_labeled_fusion_subset.parquet"
OUTPUT_DIR = PROJECT_ROOT / "models" / "fusion"


def main():
    print("=" * 80)
    print("STAGE 8.22: MULTIMODAL FUSION TRAINING & EVALUATION PIPELINE")
    print("=" * 80)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"\nLoading labeled fusion cohort from {LABELED_DATA_PATH}...")
    df_labeled = pd.read_parquet(LABELED_DATA_PATH)
    print(f"Loaded {len(df_labeled)} labeled samples.")

    # 1. Train Model
    print("\n--- PHASE K: TRAINING MULTIMODAL LATE-FUSION MLP ---")
    model, training_metrics = train_fusion_model(
        df_labeled,
        epochs=15,
        batch_size=32,
        lr=1e-3,
        weight_decay=1e-4,
        random_seed=42,
        output_dir=OUTPUT_DIR,
    )

    # 2. Baselines & Ablations
    print("\n--- PHASE F & G: BASELINES & ABLATIONS ---")
    baselines, ablations = run_baselines_and_ablations(model, df_labeled)

    # 3. Explainability & Modality Importance
    print("\n--- PHASE I: MODALITY INTERPRETABILITY (LOMO) ---")
    val_sup = df_labeled[(df_labeled["target_class_id"] >= 0) & (df_labeled["partition"] == "val")]
    val_ds = MultimodalFusionDataset(val_sup, is_train=False)
    modality_importance = compute_modality_importance(model, val_ds)
    print("Leave-One-Modality-Out Importance (Macro F1 drop on Val):")
    for mod, drop in modality_importance.items():
        print(f"  {mod:12s}: {drop:+.4f}")

    # 4. Persistence & Sample Prediction Semantics
    print("\n--- PHASE H & J: SAMPLE PREDICTION SEMANTICS & EXPLANATIONS ---")
    sample_records = []
    # Pick one sample per class
    for cid in range(4):
        sub = df_labeled[df_labeled["target_class_id"] == cid]
        if len(sub) > 0:
            rec = generate_prediction_record(model, sub.iloc[0])
            sample_records.append(rec)
            print(f"\nClass {cid} Sample ({rec['observation_id']}):")
            print(f"  True: {sub.iloc[0]['human_observed_class']} | Pred: {rec['predicted_class']} (Conf: {rec['confidence']:.2f})")
            print(f"  Persistence Score: {rec['persistence_score']} | Acute Likelihood: {rec['acute_likelihood']}")
            print(f"  Explanation:\n  {rec['explanation'].replace(chr(10), chr(10) + '  ')}")

    # 5. Compile and save evaluation summary
    eval_summary = {
        "stage": "Stage 8.22: Multimodal Late Fusion",
        "training_metrics": training_metrics,
        "baselines": baselines,
        "ablations": ablations,
        "modality_importance_lomo": modality_importance,
        "sample_prediction_explanations": sample_records,
    }

    eval_summary_path = OUTPUT_DIR / "evaluation_summary.json"
    with open(eval_summary_path, "w", encoding="utf-8") as f:
        json.dump(eval_summary, f, indent=2)

    print(f"\nSuccessfully generated and saved all evaluation artifacts to {OUTPUT_DIR}.")


if __name__ == "__main__":
    main()
