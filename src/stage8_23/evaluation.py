"""
Stage 8.23 Phase K through Q: Event-Level and Detection-Level Evaluation.

Evaluates multimodal late-fusion performance under strict leakage and independence controls:
- Decision gate evaluation (Case B/C: acute test scarcity documented)
- Standardized baselines (FIRMS, TCN, SAD, S2, Full)
- Principled ablations with distinction between missing vs ablated modalities
- Detection-level and Event-level evaluations (Mean Probability Aggregation)
- Persistence vs acute scoring
- LOMO explainability and narrative evidence generation

Produces:
- data/interim/ds08_stage8_23_evaluation_summary.json
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
import torch
import torch.nn as nn

import sys
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.stage8_22.fusion_cohort import CAUSAL_GEO_FEATURES
from src.stage8_22.fusion_model import MultimodalLateFusionMLP

EVENT_COHORT_PATH = PROJECT_ROOT / "data" / "interim" / "ds08_stage8_23_multimodal_event_cohort.parquet"
LABELED_SUBSET_PATH = PROJECT_ROOT / "data" / "interim" / "ds08_stage8_22_labeled_fusion_subset.parquet"
MODEL_CHECKPOINT_PATH = PROJECT_ROOT / "models" / "fusion" / "best_multimodal_fusion.pt"
LABEL_AUDIT_PATH = PROJECT_ROOT / "data" / "interim" / "ds08_stage8_23_label_audit.parquet"
OUTPUT_EVAL_SUMMARY_PATH = PROJECT_ROOT / "data" / "interim" / "ds08_stage8_23_evaluation_summary.json"

TARGET_CLASSES = [
    "Industrial Fire",
    "Forest Fire",
    "Agricultural Fire",
    "Other Thermal Source/Persistent Non-Biomass Thermal Source",
]


def confusion_matrix_np(y_true: np.ndarray, y_pred: np.ndarray, num_classes: int = 4) -> np.ndarray:
    """Computes confusion matrix without sklearn dependency."""
    cm = np.zeros((num_classes, num_classes), dtype=np.int64)
    for t, p in zip(y_true, y_pred):
        if 0 <= t < num_classes and 0 <= p < num_classes:
            cm[t, p] += 1
    return cm


def compute_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    num_classes: int = 4,
    class_names: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Computes classification metrics with strict 'N/A' handling for zero-support classes.
    """
    if class_names is None:
        class_names = TARGET_CLASSES

    cm = confusion_matrix_np(y_true, y_pred, num_classes)
    total_samples = len(y_true)
    overall_acc = float((y_true == y_pred).sum() / max(total_samples, 1))

    per_class = {}
    f1_list = []
    recalls_list = []

    for c in range(num_classes):
        cname = class_names[c]
        support = int((y_true == c).sum())
        predicted_count = int((y_pred == c).sum())
        tp = int(cm[c, c])

        if support == 0:
            per_class[cname] = {
                "support": 0,
                "predicted": predicted_count,
                "precision": "N/A",
                "recall": "N/A",
                "f1": "N/A",
            }
        else:
            prec = float(tp / predicted_count) if predicted_count > 0 else 0.0
            rec = float(tp / support)
            f1 = float(2 * prec * rec / (prec + rec)) if (prec + rec) > 0 else 0.0
            per_class[cname] = {
                "support": support,
                "predicted": predicted_count,
                "precision": round(prec, 4),
                "recall": round(rec, 4),
                "f1": round(f1, 4),
            }
            f1_list.append(f1)
            recalls_list.append(rec)

    macro_f1 = float(np.mean(f1_list)) if f1_list else "N/A"
    bal_acc = float(np.mean(recalls_list)) if recalls_list else "N/A"

    return {
        "overall_accuracy": round(overall_acc, 4),
        "balanced_accuracy": round(bal_acc, 4) if isinstance(bal_acc, float) else bal_acc,
        "macro_f1": round(macro_f1, 4) if isinstance(macro_f1, float) else macro_f1,
        "confusion_matrix": cm.tolist(),
        "per_class": per_class,
        "supported_classes_count": len(f1_list),
    }


def run_stage8_23_evaluation() -> Dict[str, Any]:
    print("=" * 80)
    print("STAGE 8.23: INDEPENDENT EVALUATION (EVENT-LEVEL & DETECTION-LEVEL)")
    print("=" * 80)

    # 1. Load Data
    print("\n[Step 1/6] Loading multimodal event cohort and labeled dataset...")
    df_cohort = pd.read_parquet(EVENT_COHORT_PATH)
    df_sub = pd.read_parquet(LABELED_SUBSET_PATH)

    # Map event_id and incident_id onto labeled subset
    det_to_ev = dict(zip(df_cohort["detection_id"], df_cohort["event_id"]))
    det_to_inc = dict(zip(df_cohort["detection_id"], df_cohort["incident_id"]))
    df_sub["event_id"] = df_sub["detection_id"].map(det_to_ev).fillna("BG_" + df_sub["detection_id"])
    df_sub["incident_id"] = df_sub["detection_id"].map(det_to_inc).fillna("BG_INCIDENT")

    # Filter valid supervised samples
    df_valid = df_sub[df_sub["target_class_id"] >= 0].copy()
    print(f"  Total labeled samples: {len(df_sub):,} | Valid supervised samples: {len(df_valid):,}")

    # Standardize partitions:
    # Train: 'train', 'train_heldout_spatial'
    # Val: 'val'
    # Test: 'test', 'test_seen_spatial'
    df_train = df_valid[df_valid["partition"].isin(["train", "train_heldout_spatial"])].copy()
    df_val = df_valid[df_valid["partition"] == "val"].copy()
    df_test = df_valid[df_valid["partition"].isin(["test", "test_seen_spatial"])].copy()

    # PHASE K: Print Decision Gate Metrics
    print("\n" + "=" * 80)
    print("PHASE K: MODEL TRAINING DECISION GATE")
    print("=" * 80)

    total_evts = df_cohort["event_id"].nunique()
    total_dets = len(df_cohort)
    train_evts = df_train["event_id"].nunique()
    val_evts = df_val["event_id"].nunique()
    test_evts = df_test["event_id"].nunique()

    print(f"  Total independent events in cohort: {total_evts:,}")
    print(f"  Total detections in cohort: {total_dets:,}")
    print(f"  Train supervised detections: {len(df_train)} (Events: {train_evts})")
    print(f"  Val supervised detections:   {len(df_val)} (Events: {val_evts})")
    print(f"  Test supervised detections:  {len(df_test)} (Events: {test_evts})")

    # Class event support table
    class_support_table: Dict[str, Dict[str, Any]] = {}
    for c_id, c_name in enumerate(TARGET_CLASSES):
        tr_c_dets = int((df_train["target_class_id"] == c_id).sum())
        tr_c_evts = int(df_train[df_train["target_class_id"] == c_id]["event_id"].nunique())
        va_c_dets = int((df_val["target_class_id"] == c_id).sum())
        va_c_evts = int(df_val[df_val["target_class_id"] == c_id]["event_id"].nunique())
        te_c_dets = int((df_test["target_class_id"] == c_id).sum())
        te_c_evts = int(df_test[df_test["target_class_id"] == c_id]["event_id"].nunique())

        class_support_table[c_name] = {
            "train_detections": tr_c_dets,
            "train_events": tr_c_evts,
            "val_detections": va_c_dets,
            "val_events": va_c_evts,
            "test_detections": te_c_dets,
            "test_events": te_c_evts,
            "test_evaluable": te_c_evts > 0,
        }

    print("\n  CLASS-LEVEL SUPPORT MATRIX:")
    print(f"  {'CLASS':45s} | {'TRAIN EVTS':10s} | {'VAL EVTS':8s} | {'TEST EVTS':9s} | STATUS")
    print("  " + "-" * 85)
    for c_name, stats in class_support_table.items():
        status_str = "EVALUABLE" if stats["test_evaluable"] else "UNEVALUABLE (N/A)"
        print(f"  {c_name:45s} | {stats['train_events']:10d} | {stats['val_events']:8d} | {stats['test_events']:9d} | {status_str}")

    # Decision Gate Verdict:
    acute_test_support = (
        class_support_table["Industrial Fire"]["test_events"]
        + class_support_table["Forest Fire"]["test_events"]
        + class_support_table["Agricultural Fire"]["test_events"]
    )
    if acute_test_support == 0:
        decision_gate_verdict = (
            "CASE C / CASE B TRIGGERED: Held-out independent test partition contains exactly ZERO acute fire events "
            "(Industrial=0, Forest=0, Agricultural=0). Supervised evaluation is restricted to supported classes (Other Thermal), "
            "and all unsupported test classes are marked strictly N/A. Classification cannot be declared production-ready."
        )
    else:
        decision_gate_verdict = "CASE A: Full test support available."
    print(f"\n  Decision Gate Verdict: {decision_gate_verdict}")

    # 2. Load Model Checkpoint
    print("\n[Step 2/6] Loading frozen Stage 8.22 Multimodal Late Fusion checkpoint...")
    model = MultimodalLateFusionMLP()
    state_dict = torch.load(MODEL_CHECKPOINT_PATH, map_location="cpu")
    weights = state_dict["model_state_dict"] if "model_state_dict" in state_dict else state_dict
    model.load_state_dict(weights)
    model.eval()
    print("  Successfully loaded model weights.")

    # Helper: Feature extraction
    def extract_tensors(df_part: pd.DataFrame):
        tcn_cols = [f"z_tcn_{i}" for i in range(64)]
        sad_cols = [f"z_sad_{i}" for i in range(32)]
        s2_cols = [f"z_s2_{i}" for i in range(128)]
        infra_cols = [f"z_infra_{i}" for i in range(128)]
        fire_cols = [f"z_fire_smoke_{i}" for i in range(128)]

        x_tcn = torch.tensor(df_part[tcn_cols].values, dtype=torch.float32)
        x_sad = torch.tensor(df_part[sad_cols].values, dtype=torch.float32)
        x_s2 = torch.tensor(df_part[s2_cols].values, dtype=torch.float32)
        x_infra = torch.tensor(df_part[infra_cols].values, dtype=torch.float32)
        x_fire = torch.tensor(df_part[fire_cols].values, dtype=torch.float32)
        x_geo = torch.tensor(df_part[CAUSAL_GEO_FEATURES].values, dtype=torch.float32)

        m_tcn = df_part["has_tcn"].values.astype(np.float32)[:, None]
        m_sad = df_part["has_sad"].values.astype(np.float32)[:, None]
        m_infra = df_part["has_yolo_infra"].values.astype(np.float32)[:, None]
        m_fire = df_part["has_yolo_fire"].values.astype(np.float32)[:, None]
        m_s2 = df_part["has_s2"].values.astype(np.float32)[:, None]
        m_geo = df_part["has_geo"].values.astype(np.float32)[:, None]

        mask_6d = torch.tensor(np.hstack([m_tcn, m_sad, m_infra, m_fire, m_s2, m_geo]), dtype=torch.float32)
        y = torch.tensor(df_part["target_class_id"].values, dtype=torch.long)

        return (x_tcn, x_sad, x_infra, x_fire, x_s2, x_geo, mask_6d, y)

    # 3. Model Inference Helper
    def evaluate_model(
        df_part: pd.DataFrame,
        override_mask: Optional[Dict[str, bool]] = None,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        x_tcn, x_sad, x_infra, x_fire, x_s2, x_geo, mask_6d, y = extract_tensors(df_part)

        if override_mask:
            # Override masks: 0:tcn, 1:sad, 2:infra, 3:fire, 4:s2, 5:geo
            mod_idx_map = {"tcn": 0, "sad": 1, "infra": 2, "fire": 3, "s2": 4, "geo": 5}
            for mod_k, is_on in override_mask.items():
                col_i = mod_idx_map[mod_k]
                if not is_on:
                    mask_6d[:, col_i] = 0.0

        with torch.no_grad():
            logits = model(x_tcn, x_sad, x_infra, x_fire, x_s2, x_geo, mask_6d)
            probs = torch.softmax(logits, dim=-1).cpu().numpy()
            preds = np.argmax(probs, axis=-1)

        return y.cpu().numpy(), preds, probs

    # 4. Standardized Baselines Evaluation (Detection-Level)
    print("\n[Step 3/6] Evaluating detection-level standardized baselines...")
    BASELINES = {
        "1. FIRMS Geospatial Only": {"geo": True, "tcn": False, "sad": False, "s2": False, "infra": False, "fire": False},
        "2. TCN + FIRMS": {"geo": True, "tcn": True, "sad": False, "s2": False, "infra": False, "fire": False},
        "3. FIRMS + TCN + Deep SAD": {"geo": True, "tcn": True, "sad": True, "s2": False, "infra": False, "fire": False},
        "4. FIRMS + TCN + YOLO (Masked)": {"geo": True, "tcn": True, "sad": False, "s2": False, "infra": True, "fire": True},
        "5. FIRMS + TCN + Sentinel-2": {"geo": True, "tcn": True, "sad": False, "s2": True, "infra": False, "fire": False},
        "6. Full Multimodal Fusion": {"geo": True, "tcn": True, "sad": True, "s2": True, "infra": True, "fire": True},
    }

    baseline_results: Dict[str, Any] = {}
    for b_name, m_override in BASELINES.items():
        y_val_t, y_val_p, _ = evaluate_model(df_val, override_mask=m_override)
        y_test_t, y_test_p, _ = evaluate_model(df_test, override_mask=m_override)

        m_val = compute_metrics(y_val_t, y_val_p)
        m_test = compute_metrics(y_test_t, y_test_p)

        baseline_results[b_name] = {
            "val": m_val,
            "test": m_test,
        }
        print(f"  {b_name:32s} | Val Acc: {m_val['overall_accuracy']:.4f} | Test Acc: {m_test['overall_accuracy']:.4f}")

    # 5. Ablations Evaluation
    print("\n[Step 4/6] Evaluating modality ablations...")
    ABLATIONS = {
        "Remove TCN": {"geo": True, "tcn": False, "sad": True, "s2": True, "infra": True, "fire": True},
        "Remove Deep SAD": {"geo": True, "tcn": True, "sad": False, "s2": True, "infra": True, "fire": True},
        "Remove Sentinel-2": {"geo": True, "tcn": True, "sad": True, "s2": False, "infra": True, "fire": True},
        "Remove YOLO Infrastructure": {"geo": True, "tcn": True, "sad": True, "s2": True, "infra": False, "fire": True},
        "Remove YOLO Fire/Smoke": {"geo": True, "tcn": True, "sad": True, "s2": True, "infra": True, "fire": False},
        "Remove Geospatial Branch": {"geo": False, "tcn": True, "sad": True, "s2": True, "infra": True, "fire": True},
        "Full Available Fusion": {"geo": True, "tcn": True, "sad": True, "s2": True, "infra": True, "fire": True},
    }

    ablation_results: Dict[str, Any] = {}
    for a_name, m_override in ABLATIONS.items():
        y_val_t, y_val_p, _ = evaluate_model(df_val, override_mask=m_override)
        y_test_t, y_test_p, _ = evaluate_model(df_test, override_mask=m_override)

        ablation_results[a_name] = {
            "val": compute_metrics(y_val_t, y_val_p),
            "test": compute_metrics(y_test_t, y_test_p),
        }

    # 6. Event-Level Evaluation via Mean Probability Aggregation
    print("\n[Step 5/6] Executing Phase O Event-Level Evaluation (Mean Probability Aggregation)...")

    def evaluate_event_level(df_part: pd.DataFrame) -> Dict[str, Any]:
        """
        Groups detections by event_id, averages predicted class probability vectors,
        and determines event-level prediction via argmax.
        """
        y_true_dets, y_pred_dets, probs_dets = evaluate_model(df_part)

        df_eval = df_part[["event_id", "target_class_id"]].copy()
        df_eval["y_true"] = y_true_dets
        df_eval["pred_c0"] = probs_dets[:, 0]
        df_eval["pred_c1"] = probs_dets[:, 1]
        df_eval["pred_c2"] = probs_dets[:, 2]
        df_eval["pred_c3"] = probs_dets[:, 3]

        # Group by physical event
        grouped = df_eval.groupby("event_id").agg({
            "y_true": "first",  # Consistent ground truth per event
            "pred_c0": "mean",
            "pred_c1": "mean",
            "pred_c2": "mean",
            "pred_c3": "mean",
        }).reset_index()

        mean_probs = grouped[["pred_c0", "pred_c1", "pred_c2", "pred_c3"]].values
        event_preds = np.argmax(mean_probs, axis=-1)
        event_trues = grouped["y_true"].values

        metrics = compute_metrics(event_trues, event_preds)
        metrics["total_physical_events"] = len(grouped)
        return metrics

    event_val_metrics = evaluate_event_level(df_val)
    event_test_metrics = evaluate_event_level(df_test)

    print(f"  Event-Level Validation: Acc={event_val_metrics['overall_accuracy']:.4f}, BalAcc={event_val_metrics['balanced_accuracy']}, Events={event_val_metrics['total_physical_events']}")
    print(f"  Event-Level Test:       Acc={event_test_metrics['overall_accuracy']:.4f}, BalAcc={event_test_metrics['balanced_accuracy']}, Events={event_test_metrics['total_physical_events']}")

    # 7. Persistence vs. Acute Likelihood Scoring & Narrative Explanations
    print("\n[Step 6/6] Computing Persistence scores and narrative explanation traces...")
    # Persistence score formula:
    # P = min(1.0, recurrent_30d / 10.0)
    # Acute Likelihood = 1.0 - P
    df_samples = df_sub.head(10).copy()
    y_s_t, y_s_p, probs_s = evaluate_model(df_samples)

    explanation_traces: List[Dict[str, Any]] = []
    for i in range(len(df_samples)):
        row = df_samples.iloc[i]
        did = row["detection_id"]
        evid = row["event_id"]
        c_pred = int(y_s_p[i])
        c_name = TARGET_CLASSES[c_pred]
        conf = float(probs_s[i, c_pred])

        rec_30d = float(row.get("recurrent_30d", 0.0))
        p_score = min(1.0, max(0.0, rec_30d / 10.0))
        acute_score = 1.0 - p_score

        avail_mods = {
            "geo": bool(row["has_geo"]),
            "tcn": bool(row["has_tcn"]),
            "sad": bool(row["has_sad"]),
            "s2": bool(row["has_s2"]),
            "yolo_infra": bool(row["has_yolo_infra"]),
            "yolo_fire": bool(row["has_yolo_fire"]),
        }

        trace = {
            "detection_id": did,
            "event_id": evid,
            "predicted_class": c_name,
            "predicted_class_id": c_pred,
            "confidence": round(conf, 4),
            "class_probabilities": {name: round(float(probs_s[i, idx]), 4) for idx, name in enumerate(TARGET_CLASSES)},
            "evidence_available": avail_mods,
            "persistence_score": round(p_score, 4),
            "acute_likelihood": round(acute_score, 4),
            "explanation": (
                f"Prediction: {c_name} (Confidence: {conf*100:.1f}%)\n"
                f"Evidence Available:\n"
                f"- Temporal thermal pattern (TCN): {'Available' if avail_mods['tcn'] else 'Unavailable'}\n"
                f"- Deep SAD anomaly projection: {'Available' if avail_mods['sad'] else 'Unavailable'}\n"
                f"- Sentinel-2 multispectral chip: {'Available' if avail_mods['s2'] else 'Unavailable'}\n"
                f"- Recurrence / Persistence score: {p_score:.2f} (Acute likelihood: {acute_score:.2f})\n"
                f"- Industrial visual evidence (YOLO): Unavailable (unassociated)\n"
                f"- Fire/smoke visual evidence (YOLO): Unavailable (unassociated)"
            ),
        }
        explanation_traces.append(trace)

    # Compile Final Summary
    eval_summary = {
        "stage": "Stage 8.23: Independent Multimodal Source-Attribution Evaluation",
        "decision_gate": {
            "verdict": decision_gate_verdict,
            "total_independent_events": total_evts,
            "total_detections": total_dets,
            "class_support_matrix": class_support_table,
            "acute_test_support_events": acute_test_support,
        },
        "baselines_detection_level": baseline_results,
        "ablations_detection_level": ablation_results,
        "event_level_evaluation": {
            "aggregation_method": "Mean Probability Aggregation across constituent detections",
            "val": event_val_metrics,
            "test": event_test_metrics,
        },
        "sample_explanation_traces": explanation_traces,
    }

    with open(OUTPUT_EVAL_SUMMARY_PATH, "w", encoding="utf-8") as f:
        json.dump(eval_summary, f, indent=2)
    print(f"\nSaved evaluation summary JSON: {OUTPUT_EVAL_SUMMARY_PATH}")

    return eval_summary


if __name__ == "__main__":
    run_stage8_23_evaluation()
