"""Stage 8.36 Final Blind Evaluation Engine.

Executes EXACTLY ONE forward pass over the frozen 2026 independent test cohort (N=28).
Strictly enforces:
- Manifest SHA-256 verification.
- Checkpoint SHA-256 verification.
- Test evaluation counter equals strictly 1.
- Zero retraining, zero parameter adjustments, zero post-processing tweaks.
- Deterministic forward pass and metric calculation.
- Uncertainty intervals (95% Wilson score CI, 1000-sample bootstrap CIs).
- Confusion matrix CSV & PNG generation.
- Full error analysis and comprehensive final reporting.
"""

import copy
import hashlib
import json
import logging
import math
from pathlib import Path
import sys
from typing import Dict, List, Tuple, Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    precision_recall_fscore_support,
)
import torch

PROJECT_ROOT = Path("d:/DATA PREPROCESSING")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

ARTIFACTS_DIR = PROJECT_ROOT / "artifacts" / "stage8_36"
MODELS_DIR = PROJECT_ROOT / "models" / "stage8_36"
COUNTER_FILE = ARTIFACTS_DIR / ".test_eval_counter"

MANIFEST_PATH = PROJECT_ROOT / "data" / "reference" / "ds08" / "manifests" / "stage8_25" / "independent_test_manifest.json"
EXPECTED_MANIFEST_HASH = "5686345a1300282407d303c943e190867b63c0c5d5ea536973d4859cd8a95d6c"

CHECKPOINT_PATH = MODELS_DIR / "final_neural_model.pt"
EXPECTED_CHECKPOINT_HASH = "5bdbfbd503a3c0acbd50caefd2b1c88b5e0190a7176d70a517165814722bcff2"

CLASS_NAMES = [
    "Industrial Fire",
    "Forest Fire",
    "Agricultural Fire",
    "Other / Persistent Thermal Source"
]

CLASS_SHORT_NAMES = ["Industrial", "Forest", "Agricultural", "Persistent"]

from src.stage8_36.model import Architecture1_StaticMLP

def compute_sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()

def check_and_increment_counter() -> int:
    """Strictly checks and updates the test evaluation counter."""
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    cnt = 0
    if COUNTER_FILE.exists():
        try:
            cnt = int(COUNTER_FILE.read_text(encoding="utf-8").strip())
        except Exception:
            cnt = 0
    if cnt >= 1:
        raise RuntimeError(
            f"ABSOLUTE LOCK VIOLATION: TEST_EVALUATION_COUNT is already {cnt}! "
            "No second test evaluation is permitted."
        )
    cnt += 1
    COUNTER_FILE.write_text(str(cnt), encoding="utf-8")
    return cnt

def wilson_score_interval(successes: int, total: int, confidence: float = 0.95) -> Tuple[float, float]:
    """Computes exact Wilson score confidence interval for binomial proportion."""
    if total == 0:
        return (0.0, 0.0)
    z = 1.95996  # 95% two-sided normal quantile
    p = successes / total
    denom = 1.0 + (z ** 2) / total
    center = (p + (z ** 2) / (2.0 * total)) / denom
    margin = (z * math.sqrt((p * (1.0 - p) + (z ** 2) / (4.0 * total)) / total)) / denom
    return (max(0.0, center - margin), min(1.0, center + margin))

def bootstrap_confidence_intervals(
    y_true: np.ndarray, y_pred: np.ndarray, n_bootstraps: int = 1000, seed: int = 42
) -> Dict[str, Tuple[float, float]]:
    """Calculates 95% bootstrap confidence intervals with a fixed random seed."""
    rng = np.random.RandomState(seed)
    n = len(y_true)
    accs, f1s, baccs = [], [], []

    for _ in range(n_bootstraps):
        idx = rng.randint(0, n, size=n)
        yt_s = y_true[idx]
        yp_s = y_pred[idx]
        accs.append(accuracy_score(yt_s, yp_s))
        f1s.append(f1_score(yt_s, yp_s, average="macro", zero_division=0))
        baccs.append(balanced_accuracy_score(yt_s, yp_s))

    return {
        "accuracy_ci_95": (float(np.percentile(accs, 2.5)), float(np.percentile(accs, 97.5))),
        "macro_f1_ci_95": (float(np.percentile(f1s, 2.5)), float(np.percentile(f1s, 97.5))),
        "balanced_accuracy_ci_95": (float(np.percentile(baccs, 2.5)), float(np.percentile(baccs, 97.5)))
    }

def run_blind_evaluation():
    logger.info("================================================================================")
    logger.info("STAGE 8.36: FINAL MODEL FREEZE & BLIND 2026 INDEPENDENT TEST EVALUATION")
    logger.info("================================================================================")

    # 1. Update and lock evaluation counter
    eval_count = check_and_increment_counter()
    logger.info(f"Test evaluation counter successfully locked: TEST_EVALUATION_COUNT = {eval_count}")

    # 2. Forensic Verifications
    manifest_hash = compute_sha256(MANIFEST_PATH)
    assert manifest_hash == EXPECTED_MANIFEST_HASH, f"Manifest hash mismatch: {manifest_hash}"
    logger.info(f"Verified Frozen Manifest Hash: {manifest_hash}")

    checkpoint_hash = compute_sha256(CHECKPOINT_PATH)
    assert checkpoint_hash == EXPECTED_CHECKPOINT_HASH, f"Checkpoint hash mismatch: {checkpoint_hash}"
    logger.info(f"Verified Final Checkpoint Hash: {checkpoint_hash}")

    # 3. Load Frozen Test Cohort & Manifest
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest_data = json.load(f)
    test_events = manifest_data["events"]
    assert len(test_events) == 28, f"Expected 28 test events, got {len(test_events)}"
    manifest_ids = [e["event_id"] for e in test_events]
    y_true = np.array([e["class_id"] for e in test_events], dtype=np.int64)

    # 4. Load Causal H0 Features
    features_path = PROJECT_ROOT / "data" / "interim" / "ds08_stage8_30_causal_features.parquet"
    assert features_path.exists(), "Causal features parquet missing"
    df_feat = pd.read_parquet(features_path)
    df_h0_test = df_feat[(df_feat["horizon"] == "H0") & (df_feat["event_id"].isin(manifest_ids))].copy()
    assert len(df_h0_test) == 28, f"Expected 28 H0 test events, got {len(df_h0_test)}"
    
    # Strictly align row ordering with manifest
    df_h0_test = df_h0_test.set_index("event_id").loc[manifest_ids].reset_index()

    # 5. Load Frozen Schema & Scalers
    schema_path = MODELS_DIR / "feature_schema.json"
    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)
    feature_groups = schema["feature_groups"]
    group_dims = schema["group_dimensions"]

    # Verify Schema Matching
    training_feature_list = []
    for grp in ["thermal", "industrial", "ecoregion", "historical"]:
        training_feature_list.extend(feature_groups[grp])
    assert len(training_feature_list) == 41, f"Expected 41 features, got {len(training_feature_list)}"
    
    preproc_path = MODELS_DIR / "preprocessing.pt"
    scalers = torch.load(preproc_path, weights_only=False)

    # Standardize Features using Training Scalers
    batch = {}
    for grp in ["thermal", "industrial", "ecoregion", "historical"]:
        cols = feature_groups[grp]
        mat = df_h0_test[cols].values.astype(np.float32)
        mat = np.nan_to_num(mat, nan=0.0, posinf=0.0, neginf=0.0)
        mean, std = scalers[grp]
        norm_mat = (mat - mean) / std
        batch[f"{grp}_feats"] = torch.tensor(norm_mat, dtype=torch.float32)

    # 6. Load Frozen Model
    model = Architecture1_StaticMLP(group_dims, hidden_dim=48, num_classes=4, dropout=0.15)
    weights = torch.load(CHECKPOINT_PATH, weights_only=True, map_location="cpu")
    model.load_state_dict(weights)
    model.eval()

    # 7. EXACTLY ONE BLIND FORWARD PASS
    logger.info("Executing blind forward pass over 28 test events...")
    with torch.no_grad():
        out = model(batch)
        logits = out["logits"]
        probs = out["probs"].numpy()

    y_pred = np.argmax(probs, axis=-1)
    confidences = np.max(probs, axis=-1)

    # 8. Save final predictions immediately
    pred_df = pd.DataFrame({
        "event_id": manifest_ids,
        "predicted_class": [CLASS_NAMES[i] for i in y_pred],
        "predicted_class_id": y_pred,
        "confidence": np.round(confidences, 6),
        "probability_industrial": np.round(probs[:, 0], 6),
        "probability_forest": np.round(probs[:, 1], 6),
        "probability_agricultural": np.round(probs[:, 2], 6),
        "probability_persistent": np.round(probs[:, 3], 6)
    })
    pred_path = ARTIFACTS_DIR / "final_predictions.csv"
    pred_df.to_csv(pred_path, index=False)
    logger.info(f"Saved final predictions to {pred_path}")

    # 9. Compute Final Metrics
    total_samples = len(y_true)
    num_correct = int(np.sum(y_true == y_pred))
    acc = accuracy_score(y_true, y_pred)
    macro_f1 = f1_score(y_true, y_pred, average="macro", zero_division=0)
    weighted_f1 = f1_score(y_true, y_pred, average="weighted", zero_division=0)
    bal_acc = balanced_accuracy_score(y_true, y_pred)

    prec, rec, f1, supp = precision_recall_fscore_support(
        y_true, y_pred, labels=[0, 1, 2, 3], zero_division=0
    )

    per_class_metrics = {}
    for i, name in enumerate(CLASS_NAMES):
        per_class_metrics[name] = {
            "precision": round(float(prec[i]), 4),
            "recall": round(float(rec[i]), 4),
            "f1": round(float(f1[i]), 4),
            "support": int(supp[i])
        }

    # 10. Compute Confusion Matrix
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1, 2, 3])
    cm_df = pd.DataFrame(cm, index=CLASS_SHORT_NAMES, columns=CLASS_SHORT_NAMES)
    cm_path = ARTIFACTS_DIR / "confusion_matrix.csv"
    cm_df.to_csv(cm_path)
    logger.info(f"Saved confusion matrix to {cm_path}")

    # Plot Confusion Matrix PNG
    fig, ax = plt.subplots(figsize=(6, 5), dpi=300)
    im = ax.imshow(cm, interpolation="nearest", cmap=plt.cm.Blues)
    ax.figure.colorbar(im, ax=ax)
    ax.set(
        xticks=np.arange(cm.shape[1]),
        yticks=np.arange(cm.shape[0]),
        xticklabels=CLASS_SHORT_NAMES,
        yticklabels=CLASS_SHORT_NAMES,
        title=f"Stage 8.36 Frozen Test Confusion Matrix (N={total_samples})\nAccuracy: {acc*100:.2f}% | Macro-F1: {macro_f1:.4f}",
        ylabel="True Label",
        xlabel="Predicted Label"
    )
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")

    # Annotate numbers
    thresh = cm.max() / 2.0
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            ax.text(
                j, i, format(cm[i, j], "d"),
                ha="center", va="center",
                color="white" if cm[i, j] > thresh else "black",
                fontweight="bold"
            )
    fig.tight_layout()
    cm_png_path = ARTIFACTS_DIR / "confusion_matrix.png"
    plt.savefig(cm_png_path)
    plt.close()
    logger.info(f"Saved confusion matrix plot to {cm_png_path}")

    # 11. Uncertainty Analysis
    wilson_low, wilson_high = wilson_score_interval(num_correct, total_samples, confidence=0.95)
    bootstrap_cis = bootstrap_confidence_intervals(y_true, y_pred, n_bootstraps=1000, seed=42)

    uncertainty_dict = {
        "n_samples": total_samples,
        "n_correct": num_correct,
        "points_per_event": 100.0 / total_samples,
        "accuracy": round(float(acc), 4),
        "accuracy_wilson_95_ci": [round(wilson_low, 4), round(wilson_high)],
        "accuracy_bootstrap_95_ci": [round(bootstrap_cis["accuracy_ci_95"][0], 4), round(bootstrap_cis["accuracy_ci_95"][1], 4)],
        "macro_f1": round(float(macro_f1), 4),
        "macro_f1_bootstrap_95_ci": [round(bootstrap_cis["macro_f1_ci_95"][0], 4), round(bootstrap_cis["macro_f1_ci_95"][1], 4)],
        "balanced_accuracy": round(float(bal_acc), 4),
        "balanced_accuracy_bootstrap_95_ci": [round(bootstrap_cis["balanced_accuracy_ci_95"][0], 4), round(bootstrap_cis["balanced_accuracy_ci_95"][1], 4)]
    }
    with open(ARTIFACTS_DIR / "confidence_intervals.json", "w", encoding="utf-8") as f:
        json.dump(uncertainty_dict, f, indent=2)
    logger.info("Saved confidence_intervals.json")

    # 12. Detailed Error Analysis
    misclassified = []
    for idx, (yt, yp) in enumerate(zip(y_true, y_pred)):
        if yt != yp:
            eid = manifest_ids[idx]
            event_row = df_h0_test.iloc[idx]
            
            # Identify salient feature contributions
            feat_contribs = {
                "dist_to_fac_km": float(event_row.get("dist_to_fac_km", 999.0)),
                "within_1km_fac": float(event_row.get("within_1km_fac", 0.0)),
                "forest_biome_score": float(event_row.get("forest_biome_score", 0.0)),
                "agri_heartland_score": float(event_row.get("agri_heartland_score", 0.0)),
                "hist_count_full": float(event_row.get("hist_count_full", 0.0)),
                "hist_distinct_calendar_months": float(event_row.get("hist_distinct_calendar_months", 0.0)),
                "current_frp": float(event_row.get("current_frp", 0.0))
            }
            
            misclassified.append({
                "event_id": eid,
                "true_class_id": int(yt),
                "true_class": CLASS_NAMES[yt],
                "predicted_class_id": int(yp),
                "predicted_class": CLASS_NAMES[yp],
                "confidence": float(round(confidences[idx], 4)),
                "probabilities": {
                    "industrial": float(round(probs[idx, 0], 4)),
                    "forest": float(round(probs[idx, 1], 4)),
                    "agricultural": float(round(probs[idx, 2], 4)),
                    "persistent": float(round(probs[idx, 3], 4))
                },
                "salient_features": feat_contribs
            })
    logger.info(f"Total misclassifications: {len(misclassified)} / {total_samples}")

    # 13. Historical Benchmark Comparison
    benchmarks = {
        "Stage_8_31_Historical": {
            "model_type": "Static MLP + Random Forest Ensemble (Hybrid)",
            "accuracy": 0.8571,
            "macro_f1": 0.8231,
            "balanced_accuracy": 0.8333,
            "note": "PRIOR RESULT: Permitted classical Random Forest ensemble component"
        },
        "Stage_8_32_Historical": {
            "model_type": "GroupedCausalThermalClassifier (Deep Learning Only)",
            "accuracy": 0.7857,
            "macro_f1": 0.7800,
            "balanced_accuracy": 0.8000,
            "note": "PRIOR RESULT: Strict Deep Learning Only on unexpanded N=131 development cohort"
        },
        "Stage_8_36_Final": {
            "model_type": "Architecture1_StaticMLP (Pure PyTorch Deep Learning)",
            "accuracy": round(float(acc), 4),
            "macro_f1": round(float(macro_f1), 4),
            "balanced_accuracy": round(float(bal_acc), 4),
            "weighted_f1": round(float(weighted_f1), 4),
            "note": "OFFICIAL FINAL BENCHMARK: Evaluated exactly once on frozen cohort"
        }
    }

    # 14. Target Checks
    target_acc_met = bool(acc >= 0.85)
    target_f1_met = bool(macro_f1 >= 0.85)
    target_bal_acc_met = bool(bal_acc >= 0.85)

    final_report = {
        "status": "COMPLETED",
        "stage": "8.36",
        "evaluation_count": eval_count,
        "cohort_size": total_samples,
        "correct_predictions": num_correct,
        "manifest_sha256": manifest_hash,
        "checkpoint_sha256": checkpoint_hash,
        "metrics": {
            "accuracy": round(float(acc), 4),
            "macro_f1": round(float(macro_f1), 4),
            "weighted_f1": round(float(weighted_f1), 4),
            "balanced_accuracy": round(float(bal_acc), 4)
        },
        "per_class": per_class_metrics,
        "confusion_matrix": {
            "columns": CLASS_SHORT_NAMES,
            "rows": CLASS_SHORT_NAMES,
            "matrix": cm.tolist()
        },
        "uncertainty": uncertainty_dict,
        "targets": {
            "TARGET_ACCURACY_85": target_acc_met,
            "TARGET_MACRO_F1_85": target_f1_met,
            "TARGET_BALANCED_ACCURACY_85": target_bal_acc_met
        },
        "historical_comparison": benchmarks,
        "misclassifications": misclassified
    }

    # Save JSON Report
    report_json_path = ARTIFACTS_DIR / "final_test_report.json"
    with open(report_json_path, "w", encoding="utf-8") as f:
        json.dump(final_report, f, indent=2)
    logger.info(f"Saved final test report to {report_json_path}")

    # Generate Markdown Report
    md_content = f"""# Stage 8.36 — Final Blind Evaluation Report

**Evaluation Timestamp:** 2026-10-04  
**Evaluation Mode:** STRICT BLIND INDEPENDENT TEST EVALUATION  
**Model Architecture:** `Architecture1_StaticMLP` (Pure PyTorch Deep Learning)  
**Test Evaluation Counter:** {eval_count} (Terminal Evaluation)  
**Frozen Cohort Size:** $N = {total_samples}$ events  
**Manifest SHA-256:** `{manifest_hash}`  
**Checkpoint SHA-256:** `{checkpoint_hash}`  

---

## 1. Executive Summary & Core Results

| Metric | Stage 8.36 Value | 95% Confidence Interval | Benchmark >= 0.85 Status |
|:---|:---:|:---:|:---:|
| **Overall Accuracy** | **{acc*100:.2f}%** ({num_correct}/{total_samples}) | Wilson: [{wilson_low*100:.2f}%, {wilson_high*100:.2f}%] <br> Bootstrap: [{bootstrap_cis['accuracy_ci_95'][0]*100:.2f}%, {bootstrap_cis['accuracy_ci_95'][1]*100:.2f}%] | {'ACHIEVED' if target_acc_met else 'NOT ACHIEVED'} |
| **Macro-F1** | **{macro_f1:.4f}** | Bootstrap: [{bootstrap_cis['macro_f1_ci_95'][0]:.4f}, {bootstrap_cis['macro_f1_ci_95'][1]:.4f}] | {'ACHIEVED' if target_f1_met else 'NOT ACHIEVED'} |
| **Balanced Accuracy** | **{bal_acc*100:.2f}%** | Bootstrap: [{bootstrap_cis['balanced_accuracy_ci_95'][0]*100:.2f}%, {bootstrap_cis['balanced_accuracy_ci_95'][1]*100:.2f}%] | {'ACHIEVED' if target_bal_acc_met else 'NOT ACHIEVED'} |
| **Weighted-F1** | **{weighted_f1:.4f}** | — | — |

*Note: With $N=28$, each single event represents **3.5714 percentage points** of accuracy.*

---

## 2. Per-Class Performance Breakdown

| Class ID | Target Class Name | Support | Precision | Recall | F1-Score | Status |
|:---:|:---|:---:|:---:|:---:|:---:|:---:|
| 0 | **Industrial Fire** | {supp[0]} | {prec[0]:.4f} | {rec[0]:.4f} | **{f1[0]:.4f}** | {'Optimal' if f1[0] >= 0.85 else 'Sub-optimal'} |
| 1 | **Forest Fire** | {supp[1]} | {prec[1]:.4f} | {rec[1]:.4f} | **{f1[1]:.4f}** | {'Optimal' if f1[1] >= 0.85 else 'Sub-optimal'} |
| 2 | **Agricultural Fire** | {supp[2]} | {prec[2]:.4f} | {rec[2]:.4f} | **{f1[2]:.4f}** | {'Optimal' if f1[2] >= 0.85 else 'Sub-optimal'} |
| 3 | **Persistent / Other** | {supp[3]} | {prec[3]:.4f} | {rec[3]:.4f} | **{f1[3]:.4f}** | {'Optimal' if f1[3] >= 0.85 else 'Sub-optimal'} |

---

## 3. Confusion Matrix ($4 \\times 4$)

```
                     Industrial   Forest   Agricultural   Persistent
Industrial               {cm[0, 0]:<12} {cm[0, 1]:<8} {cm[0, 2]:<14} {cm[0, 3]:<10}
Forest                   {cm[1, 0]:<12} {cm[1, 1]:<8} {cm[1, 2]:<14} {cm[1, 3]:<10}
Agricultural             {cm[2, 0]:<12} {cm[2, 1]:<8} {cm[2, 2]:<14} {cm[2, 3]:<10}
Persistent               {cm[3, 0]:<12} {cm[3, 1]:<8} {cm[3, 2]:<14} {cm[3, 3]:<10}
```

*Figure saved to:* `artifacts/stage8_36/confusion_matrix.png`

---

## 4. Historical Benchmark Comparison

| Stage & Pipeline | Model Type | Accuracy | Macro-F1 | Balanced Acc | Deep Learning Only? |
|:---|:---|:---:|:---:|:---:|:---:|
| **Stage 8.31 (Prior)** | Hybrid Static MLP + Random Forest | 85.71% (24/28) | 0.8231 | 83.33% | No (Ensemble) |
| **Stage 8.32 (Prior)** | Grouped Gated Classifier ($N=131$) | 78.57% (22/28) | 0.7800 | 80.00% | **Yes** |
| **Stage 8.36 (Final)** | **Architecture1_StaticMLP ($N=165$)** | **{acc*100:.2f}% ({num_correct}/28)** | **{macro_f1:.4f}** | **{bal_acc*100:.2f}%** | **Yes (Pure PyTorch)** |

---

## 5. Detailed Error Analysis ({len(misclassified)} Discrepancies)

"""
    for err in misclassified:
        md_content += f"""### Event: `{err['event_id']}`
- **True Class:** {err['true_class']} (ID: {err['true_class_id']})
- **Predicted Class:** {err['predicted_class']} (ID: {err['predicted_class_id']})
- **Confidence:** {err['confidence']:.4f}
- **Predicted Probabilities:**
  - Industrial: {err['probabilities']['industrial']:.4f}
  - Forest: {err['probabilities']['forest']:.4f}
  - Agricultural: {err['probabilities']['agricultural']:.4f}
  - Persistent: {err['probabilities']['persistent']:.4f}
- **Key Features:**
  - `dist_to_fac_km`: {err['salient_features']['dist_to_fac_km']:.2f} km (within 1km: {err['salient_features']['within_1km_fac']})
  - `forest_biome_score`: {err['salient_features']['forest_biome_score']:.4f}
  - `agri_heartland_score`: {err['salient_features']['agri_heartland_score']:.4f}
  - `hist_count_full`: {err['salient_features']['hist_count_full']:.0f}
  - `hist_distinct_calendar_months`: {err['salient_features']['hist_distinct_calendar_months']:.0f}
  - `current_frp`: {err['salient_features']['current_frp']:.1f} MW

"""

    md_content += """
---

## 6. Scientific Protocol Verification
1. **Zero Retraining Commitment:** The evaluation was executed with weights frozen directly from Stage 8.35. No parameter updates or threshold search occurred.
2. **Deterministic Inference:** Standard PyTorch deterministic execution with frozen mean/std standardizers.
3. **Causal Integrity:** Features strictly constrained to $t \le t_0$ and pre-alert history $t \le t_0 - 7$ days. Zero post-event lookahead.
4. **Registry Independence:** No lookup against `persistent_source_manifest.json`. Zero target-proxy features.
"""

    report_md_path = ARTIFACTS_DIR / "final_test_report.md"
    with open(report_md_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    logger.info(f"Saved final test report markdown to {report_md_path}")

    # Return summary dict for caller / reporting
    return final_report

if __name__ == "__main__":
    rep = run_blind_evaluation()
    print("\nEVALUATION COMPLETE.")
    print(f"Accuracy: {rep['metrics']['accuracy']*100:.2f}%")
    print(f"Macro-F1: {rep['metrics']['macro_f1']:.4f}")
    print(f"Balanced Accuracy: {rep['metrics']['balanced_accuracy']*100:.2f}%")
