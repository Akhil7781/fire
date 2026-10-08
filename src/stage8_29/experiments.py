"""
Stage 8.29 Comprehensive Experimentation Suite:
- Independent-Registry and Target-Proxy Robustness Audit
- Controlled Ablations (FULL, NO_PERSISTENT_REGISTRY, NO_FACILITY_REGISTRY, NO_STATIC_REGISTRIES, CURRENT_THERMAL_ONLY, TEMPORAL_ONLY, GEOGRAPHIC_ONLY, NON_REGISTRY_MULTIMODAL)
- Multi-Horizon Evaluation Without Persistent Registry (H0..H24, Retro)
- Temporal Representation Value Test (With vs Without Temporal Embedding at H0 and H24)
- Spatial Memorization & Coordinate Perturbation Diagnostic
- Registry Permutation & Random Registry Controls
- Prediction Flip Analysis (FULL vs NO_REGISTRY)
- Small-Sample Uncertainty Quantification
"""

import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Any

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim

PROJECT_ROOT = Path("d:/DATA PREPROCESSING")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.stage8_28.models import CausalEarlyTemporalEncoder, HierarchicalCausalClassifier, FlatCausalClassifier

CLASS_NAMES = [
    "Industrial Fire",
    "Forest Fire",
    "Agricultural Fire",
    "Other Thermal Source/Persistent Non-Biomass Thermal Source"
]

HORIZON_NAMES = ["H0", "H1", "H2", "H3", "H6", "H12", "H24", "Retro"]

FEATURE_COLS_ALL = [
    # Current detection (5)
    "current_frp", "current_bright_ti4", "current_bright_ti5", "current_delta_ti", "current_is_night",
    # Trajectory so far (9)
    "detections_observed_so_far", "elapsed_observation_hours", "mean_frp_observed_so_far", "max_frp_observed_so_far",
    "std_frp_observed_so_far", "night_ratio_observed_so_far", "spatial_extent_observed_so_far", "frp_trend_observed_so_far", "time_since_prev_h",
    # Industrial facility context (6)
    "dist_to_fac_km", "within_1km_fac", "within_5km_fac", "facility_baseline_frp", "frp_deviation", "facility_frp_zscore",
    # Persistent source registry context (3)
    "dist_to_persistent_registry_km", "within_1km_persistent_registry", "within_5km_persistent_registry",
    # Historical recurrence (1)
    "prior_historical_recurrence_count",
    # Static geography & biomes (4)
    "centroid_lat", "centroid_lon", "forest_biome_score", "agri_heartland_score",
    # Modality availability flags (2)
    "s2_available", "landsat_available"
]

SKEWED_COLS = ["current_frp", "detections_observed_so_far", "elapsed_observation_hours", "mean_frp_observed_so_far",
               "max_frp_observed_so_far", "std_frp_observed_so_far", "spatial_extent_observed_so_far", "dist_to_fac_km",
               "facility_baseline_frp", "frp_deviation", "facility_frp_zscore", "dist_to_persistent_registry_km",
               "prior_historical_recurrence_count"]

def compute_metrics(y_true: np.ndarray, preds: np.ndarray, num_classes: int = 4) -> Dict[str, Any]:
    cm = np.zeros((num_classes, num_classes), dtype=int)
    for t, p in zip(y_true, preds):
        cm[t, p] += 1
    
    total = len(y_true)
    acc = float(np.sum(y_true == preds) / max(total, 1))
    
    per_f1 = []
    recalls = []
    precisions = []
    for c in range(num_classes):
        tp = cm[c, c]
        fn = np.sum(cm[c, :]) - tp
        fp = np.sum(cm[:, c]) - tp
        
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2.0 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0
        
        per_f1.append(float(f1))
        recalls.append(float(rec))
        precisions.append(float(prec))
        
    bal_acc = float(np.mean(recalls))
    macro_f1 = float(np.mean(per_f1))
    macro_prec = float(np.mean(precisions))
    macro_rec = float(np.mean(recalls))
    
    return {
        "accuracy": acc,
        "balanced_accuracy": bal_acc,
        "macro_f1": macro_f1,
        "macro_precision": macro_prec,
        "macro_recall": macro_rec,
        "per_class_f1": per_f1,
        "per_class_recall": recalls,
        "per_class_precision": precisions,
        "confusion_matrix": cm.tolist()
    }

def fit_scaler(df_train, feature_cols):
    X = df_train[feature_cols].values.astype(np.float32).copy()
    for col in SKEWED_COLS:
        if col in feature_cols:
            idx = feature_cols.index(col)
            X[:, idx] = np.log1p(np.maximum(X[:, idx], 0.0))
    mean = X.mean(axis=0)
    std = X.std(axis=0) + 1e-6
    return {"mean": mean.tolist(), "std": std.tolist(), "cols": feature_cols}

def apply_scaler(df, scaler):
    cols = scaler["cols"]
    X = df[cols].values.astype(np.float32).copy()
    for col in SKEWED_COLS:
        if col in cols:
            idx = cols.index(col)
            X[:, idx] = np.log1p(np.maximum(X[:, idx], 0.0))
    mean_arr = np.array(scaler["mean"], dtype=np.float32)
    std_arr = np.array(scaler["std"], dtype=np.float32)
    X_norm = (X - mean_arr) / std_arr
    return torch.tensor(X_norm, dtype=torch.float32)

def train_classifier(X_train, y_train, X_val, y_val, in_dim, epochs=120, lr=0.008):
    torch.manual_seed(42)
    clf = HierarchicalCausalClassifier(in_dim=in_dim, hidden_dim=64)
    optimizer = optim.AdamW(clf.parameters(), lr=lr, weight_decay=1e-4)

    best_val_f1 = -1.0
    best_state = None

    for epoch in range(1, epochs + 1):
        clf.train()
        probs, aux = clf(X_train)

        y_acute = (y_train < 3).float()
        loss_acute = F.binary_cross_entropy_with_logits(aux["logit_acute"], y_acute)

        acute_mask = (y_train < 3)
        if acute_mask.sum() > 0:
            y_ind = (y_train[acute_mask] == 0).float()
            loss_ind = F.binary_cross_entropy_with_logits(aux["logit_ind"][acute_mask], y_ind)
        else:
            loss_ind = torch.tensor(0.0)

        bio_mask = (y_train == 1) | (y_train == 2)
        if bio_mask.sum() > 0:
            y_bio = (y_train[bio_mask] == 1).float()
            loss_bio = F.binary_cross_entropy_with_logits(aux["logit_bio"][bio_mask], y_bio)
        else:
            loss_bio = torch.tensor(0.0)

        loss_nll = F.nll_loss(torch.log(probs), y_train)
        loss_state = F.cross_entropy(aux["pred_state"], y_acute.long())
        total_loss = loss_nll + 0.3 * loss_acute + 0.2 * loss_ind + 0.2 * loss_bio + 0.1 * loss_state

        optimizer.zero_grad()
        total_loss.backward()
        optimizer.step()

        clf.eval()
        with torch.no_grad():
            val_probs, _ = clf(X_val)
            val_preds = val_probs.argmax(dim=-1).numpy()
            m_val = compute_metrics(y_val.numpy(), val_preds)
            if m_val["macro_f1"] > best_val_f1:
                best_val_f1 = m_val["macro_f1"]
                best_state = {k: v.clone() for k, v in clf.state_dict().items()}

    clf.load_state_dict(best_state)
    return clf

def evaluate_model(clf, X_test, y_test):
    clf.eval()
    with torch.no_grad():
        probs_t, _ = clf(X_test)
        probs = probs_t.cpu().numpy()
        preds = np.argmax(probs, axis=-1)
        y_true = y_test.cpu().numpy()
    m = compute_metrics(y_true, preds, num_classes=4)
    m["probs"] = probs
    m["preds"] = preds
    return m

def compute_bootstrap_ci(y_true, preds, n_boot=1000, seed=42):
    np.random.seed(seed)
    n = len(y_true)
    b_accs, b_f1s = [], []
    for _ in range(n_boot):
        idx = np.random.choice(n, size=n, replace=True)
        mb = compute_metrics(y_true[idx], preds[idx])
        b_accs.append(mb["accuracy"])
        b_f1s.append(mb["macro_f1"])
    acc_ci = [float(np.percentile(b_accs, 2.5)), float(np.percentile(b_accs, 97.5))]
    f1_ci = [float(np.percentile(b_f1s, 2.5)), float(np.percentile(b_f1s, 97.5))]
    return acc_ci, f1_ci

def run_all_experiments():
    print("=" * 80, flush=True)
    print("STAGE 8.29 COMPREHENSIVE EXPERIMENTATION AND AUDIT PIPELINE", flush=True)
    print("=" * 80, flush=True)

    artifacts_dir = PROJECT_ROOT / "artifacts" / "stage8_29"
    models_dir = PROJECT_ROOT / "models" / "stage8_29"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    models_dir.mkdir(parents=True, exist_ok=True)

    # Load Stage 8.28 data & models
    feat_path = PROJECT_ROOT / "data" / "interim" / "ds08_stage8_28_causal_features.parquet"
    prefix_path = PROJECT_ROOT / "data" / "interim" / "ds08_stage8_28_causal_prefix_dataset.parquet"
    firms_path = PROJECT_ROOT / "data" / "interim" / "ds08_stage8_25_multiyear_firms.parquet"

    df_feat = pd.read_parquet(feat_path)
    df_prefix = pd.read_parquet(prefix_path)
    df_firms = pd.read_parquet(firms_path)
    df_firms["acq_dt"] = pd.to_datetime(df_firms["acq_datetime_utc"])

    # Load frozen temporal encoder from Stage 8.28
    enc_path = PROJECT_ROOT / "models" / "stage8_28" / "causal_temporal_encoder.pt"
    temporal_encoder = CausalEarlyTemporalEncoder(in_features=6, hidden_dim=64, out_dim=64)
    temporal_encoder.load_state_dict(torch.load(enc_path, map_location="cpu"))
    temporal_encoder.eval()

    # Fast sequence lookup
    firms_indexed = {r["detection_id"]: (r["acq_dt"], float(r["frp"]), float(r["bright_ti4"]), float(r["bright_ti5"]), float(r["bright_ti4"] - r["bright_ti5"]), 1.0 if r["daynight"]=="N" else 0.0) for _, r in df_firms.iterrows()}

    def extract_sequences_fast(df_sub):
        seqs, lens = [], []
        for _, row in df_sub.iterrows():
            dids = row["detection_ids_seen"]
            if not isinstance(dids, list):
                dids = dids.tolist()
            dets_info = sorted([firms_indexed[did] for did in dids if did in firms_indexed], key=lambda x: x[0])
            t0 = dets_info[0][0]
            seq_steps = []
            for dt, frp, ti4, ti5, dti, is_n in dets_info:
                dt_h = max((dt - t0).total_seconds() / 3600.0, 0.0)
                seq_steps.append([frp, ti4, ti5, dti, is_n, dt_h])
            seqs.append(np.array(seq_steps, dtype=np.float32))
            lens.append(len(seq_steps))
        max_len = max(lens)
        pad = np.zeros((len(seqs), max_len, 6), dtype=np.float32)
        for i, s in enumerate(seqs):
            pad[i, :len(s), :] = s
        return torch.tensor(pad, dtype=torch.float32), torch.tensor(lens, dtype=torch.int64)

    # Extract sequences and temporal embeddings
    print("Extracting causal temporal embeddings for all horizons and splits...", flush=True)
    splits = ["train", "val", "test"]
    z_dict = {}
    for sp in splits:
        sp_pref = df_prefix[df_prefix["split"] == sp].reset_index(drop=True)
        X_seq, lens_seq = extract_sequences_fast(sp_pref)
        with torch.no_grad():
            z_emb = temporal_encoder(X_seq, lens_seq)
        z_dict[sp] = z_emb

    train_df = df_feat[df_feat["split"] == "train"].reset_index(drop=True)
    val_df = df_feat[df_feat["split"] == "val"].reset_index(drop=True)
    test_df = df_feat[df_feat["split"] == "test"].reset_index(drop=True)

    y_train = torch.tensor(train_df["class_id"].values, dtype=torch.int64)
    y_val = torch.tensor(val_df["class_id"].values, dtype=torch.int64)
    y_test = torch.tensor(test_df["class_id"].values, dtype=torch.int64)

    # Filter H0 test subsets for Section 4 ablations
    test_h0_mask = (test_df["horizon"] == "H0").values
    test_h0_df = test_df[test_h0_mask].reset_index(drop=True)
    y_test_h0 = torch.tensor(test_h0_df["class_id"].values, dtype=torch.int64)
    z_test_h0 = z_dict["test"][test_h0_mask]

    # Filter H0 val subsets for model selection
    val_h0_mask = (val_df["horizon"] == "H0").values
    val_h0_df = val_df[val_h0_mask].reset_index(drop=True)
    y_val_h0 = torch.tensor(val_h0_df["class_id"].values, dtype=torch.int64)
    z_val_h0 = z_dict["val"][val_h0_mask]

    # =========================================================================
    # SECTION 4 & 5: RUN CONTROLLED ABLATIONS AT H0
    # =========================================================================
    print("\n" + "=" * 80, flush=True)
    print("SECTION 4 & 5: CONTROLLED ABLATIONS AT H0 ALERT TIME", flush=True)
    print("=" * 80, flush=True)

    persistent_registry_cols = ["dist_to_persistent_registry_km", "within_1km_persistent_registry", "within_5km_persistent_registry"]
    facility_registry_cols = ["dist_to_fac_km", "within_1km_fac", "within_5km_fac", "facility_baseline_frp", "frp_deviation", "facility_frp_zscore"]
    current_thermal_cols = ["current_frp", "current_bright_ti4", "current_bright_ti5", "current_delta_ti", "current_is_night"]
    geographic_cols = ["centroid_lat", "centroid_lon", "forest_biome_score", "agri_heartland_score"]

    ablation_definitions = {
        "Stage 8.28 FULL": {
            "use_temporal": True,
            "feature_cols": FEATURE_COLS_ALL
        },
        "NO_PERSISTENT_REGISTRY": {
            "use_temporal": True,
            "feature_cols": [c for c in FEATURE_COLS_ALL if c not in persistent_registry_cols]
        },
        "NO_FACILITY_REGISTRY": {
            "use_temporal": True,
            "feature_cols": [c for c in FEATURE_COLS_ALL if c not in facility_registry_cols]
        },
        "NO_STATIC_REGISTRIES": {
            "use_temporal": True,
            "feature_cols": [c for c in FEATURE_COLS_ALL if c not in persistent_registry_cols and c not in facility_registry_cols]
        },
        "CURRENT_THERMAL_ONLY": {
            "use_temporal": False,
            "feature_cols": current_thermal_cols
        },
        "TEMPORAL_ONLY": {
            "use_temporal": True,
            "feature_cols": []
        },
        "GEOGRAPHIC_ONLY": {
            "use_temporal": False,
            "feature_cols": geographic_cols
        },
        "NON_REGISTRY_MULTIMODAL": {
            "use_temporal": True,
            "feature_cols": [c for c in FEATURE_COLS_ALL if c not in persistent_registry_cols and c not in facility_registry_cols]
        }
    }

    ablation_results = []
    trained_models = {}

    for abl_name, config in ablation_definitions.items():
        use_temp = config["use_temporal"]
        cols = config["feature_cols"]

        # Build feature tensors
        parts_train, parts_val, parts_test = [], [], []
        if use_temp:
            parts_train.append(z_dict["train"])
            parts_val.append(z_dict["val"])
            parts_test.append(z_test_h0)

        if len(cols) > 0:
            scaler = fit_scaler(train_df, cols)
            X_tr_tab = apply_scaler(train_df, scaler)
            X_va_tab = apply_scaler(val_df, scaler)
            X_te_tab = apply_scaler(test_h0_df, scaler)
            parts_train.append(X_tr_tab)
            parts_val.append(X_va_tab)
            parts_test.append(X_te_tab)

        X_tr = torch.cat(parts_train, dim=-1)
        X_va = torch.cat(parts_val, dim=-1)
        X_te = torch.cat(parts_test, dim=-1)

        in_dim = X_tr.shape[-1]
        clf = train_classifier(X_tr, y_train, X_va, y_val, in_dim=in_dim, epochs=100)
        trained_models[abl_name] = (clf, cols, use_temp)

        eval_res = evaluate_model(clf, X_te, y_test_h0)
        acc_ci, f1_ci = compute_bootstrap_ci(y_test_h0.numpy(), eval_res["preds"])

        row = {
            "Model": abl_name,
            "Input_Dim": in_dim,
            "H0_Accuracy": eval_res["accuracy"],
            "Macro_F1": eval_res["macro_f1"],
            "Balanced_Acc": eval_res["balanced_accuracy"],
            "Industrial_F1": eval_res["per_class_f1"][0],
            "Forest_F1": eval_res["per_class_f1"][1],
            "Agricultural_F1": eval_res["per_class_f1"][2],
            "Persistent_F1": eval_res["per_class_f1"][3],
            "Accuracy_95_CI": acc_ci,
            "Macro_F1_95_CI": f1_ci
        }
        ablation_results.append(row)

        print(f"\n[{abl_name:<24}] (In-Dim = {in_dim})")
        print(f"  H0 Accuracy:     {eval_res['accuracy']*100:.2f}% (CI: [{acc_ci[0]:.4f}, {acc_ci[1]:.4f}])")
        print(f"  Macro-F1:        {eval_res['macro_f1']:.4f} (CI: [{f1_ci[0]:.4f}, {f1_ci[1]:.4f}])")
        print(f"  Balanced Acc:    {eval_res['balanced_accuracy']:.4f}")
        print(f"  Per-Class F1:    Ind={eval_res['per_class_f1'][0]:.4f} | For={eval_res['per_class_f1'][1]:.4f} | Agr={eval_res['per_class_f1'][2]:.4f} | Per={eval_res['per_class_f1'][3]:.4f}")
        print(f"  Confusion Matrix: {eval_res['confusion_matrix']}")

    # =========================================================================
    # SECTION 6: MULTI-HORIZON EVALUATION WITHOUT PERSISTENT REGISTRY
    # =========================================================================
    print("\n" + "=" * 80, flush=True)
    print("SECTION 6: MULTI-HORIZON EVALUATION FOR NO_PERSISTENT_REGISTRY", flush=True)
    print("=" * 80, flush=True)

    no_reg_clf, no_reg_cols, _ = trained_models["NO_PERSISTENT_REGISTRY"]
    no_reg_scaler = fit_scaler(train_df, no_reg_cols)

    horizon_records = []
    no_reg_preds_by_horizon = {}

    for h_name in HORIZON_NAMES:
        mask_h = (test_df["horizon"] == h_name).values
        sub_feat = test_df[mask_h].reset_index(drop=True)
        z_h = z_dict["test"][mask_h]
        y_h = torch.tensor(sub_feat["class_id"].values, dtype=torch.int64)

        X_tab_h = apply_scaler(sub_feat, no_reg_scaler)
        X_full_h = torch.cat([z_h, X_tab_h], dim=-1)

        eval_h = evaluate_model(no_reg_clf, X_full_h, y_h)
        acc_ci_h, f1_ci_h = compute_bootstrap_ci(y_h.numpy(), eval_h["preds"])
        no_reg_preds_by_horizon[h_name] = eval_h

        rec = {
            "horizon": h_name,
            "num_events": len(y_h),
            "accuracy": eval_h["accuracy"],
            "macro_f1": eval_h["macro_f1"],
            "balanced_accuracy": eval_h["balanced_accuracy"],
            "industrial_f1": eval_h["per_class_f1"][0],
            "forest_f1": eval_h["per_class_f1"][1],
            "agricultural_f1": eval_h["per_class_f1"][2],
            "persistent_f1": eval_h["per_class_f1"][3],
            "accuracy_ci_95": str(acc_ci_h),
            "macro_f1_ci_95": str(f1_ci_h),
            "confusion_matrix": str(eval_h["confusion_matrix"])
        }
        horizon_records.append(rec)
        print(f"Horizon {h_name:<5}: Acc = {eval_h['accuracy']*100:.2f}%, Macro-F1 = {eval_h['macro_f1']:.4f}, Bal-Acc = {eval_h['balanced_accuracy']:.4f}")

    df_no_reg_horizon = pd.DataFrame(horizon_records)
    no_reg_out_csv = artifacts_dir / "no_registry_horizon_results.csv"
    df_no_reg_horizon.to_csv(no_reg_out_csv, index=False)
    print(f"Wrote no-registry horizon results to {no_reg_out_csv}", flush=True)

    # =========================================================================
    # SECTION 9: TEMPORAL REPRESENTATION VALUE TEST
    # =========================================================================
    print("\n" + "=" * 80, flush=True)
    print("SECTION 9: TEMPORAL REPRESENTATION VALUE TEST (WITH vs WITHOUT TEMPORAL EMBEDDING)", flush=True)
    print("=" * 80, flush=True)

    # Train tabular-only model without temporal embedding on FULL features
    scaler_full = fit_scaler(train_df, FEATURE_COLS_ALL)
    X_tr_tab_full = apply_scaler(train_df, scaler_full)
    X_va_tab_full = apply_scaler(val_df, scaler_full)
    clf_no_temp = train_classifier(X_tr_tab_full, y_train, X_va_tab_full, y_val, in_dim=len(FEATURE_COLS_ALL))

    # Evaluate at H0
    X_te_h0_tab_full = apply_scaler(test_h0_df, scaler_full)
    eval_no_temp_h0 = evaluate_model(clf_no_temp, X_te_h0_tab_full, y_test_h0)

    # Evaluate at H24
    mask_h24 = (test_df["horizon"] == "H24").values
    test_h24_df = test_df[mask_h24].reset_index(drop=True)
    y_test_h24 = torch.tensor(test_h24_df["class_id"].values, dtype=torch.int64)
    X_te_h24_tab_full = apply_scaler(test_h24_df, scaler_full)
    eval_no_temp_h24 = evaluate_model(clf_no_temp, X_te_h24_tab_full, y_test_h24)

    # Model with temporal embedding at H0 and H24
    full_clf, _, _ = trained_models["Stage 8.28 FULL"]
    z_test_h24 = z_dict["test"][mask_h24]
    X_te_h0_with_temp = torch.cat([z_test_h0, X_te_h0_tab_full], dim=-1)
    X_te_h24_with_temp = torch.cat([z_test_h24, X_te_h24_tab_full], dim=-1)
    eval_with_temp_h0 = evaluate_model(full_clf, X_te_h0_with_temp, y_test_h0)
    eval_with_temp_h24 = evaluate_model(full_clf, X_te_h24_with_temp, y_test_h24)

    temporal_value_summary = {
        "H0_with_temporal": {"accuracy": eval_with_temp_h0["accuracy"], "macro_f1": eval_with_temp_h0["macro_f1"]},
        "H0_without_temporal": {"accuracy": eval_no_temp_h0["accuracy"], "macro_f1": eval_no_temp_h0["macro_f1"]},
        "H0_delta_accuracy": eval_with_temp_h0["accuracy"] - eval_no_temp_h0["accuracy"],
        "H24_with_temporal": {"accuracy": eval_with_temp_h24["accuracy"], "macro_f1": eval_with_temp_h24["macro_f1"]},
        "H24_without_temporal": {"accuracy": eval_no_temp_h24["accuracy"], "macro_f1": eval_no_temp_h24["macro_f1"]},
        "H24_delta_accuracy": eval_with_temp_h24["accuracy"] - eval_no_temp_h24["accuracy"]
    }
    print(f"H0:  With Temp Acc = {eval_with_temp_h0['accuracy']*100:.2f}% | Without Temp Acc = {eval_no_temp_h0['accuracy']*100:.2f}% (Delta = {temporal_value_summary['H0_delta_accuracy']:+.4f})")
    print(f"H24: With Temp Acc = {eval_with_temp_h24['accuracy']*100:.2f}% | Without Temp Acc = {eval_no_temp_h24['accuracy']*100:.2f}% (Delta = {temporal_value_summary['H24_delta_accuracy']:+.4f})")

    # =========================================================================
    # SECTION 10: SPATIAL MEMORIZATION & COORDINATE PERTURBATION TEST
    # =========================================================================
    print("\n" + "=" * 80, flush=True)
    print("SECTION 10: SPATIAL MEMORIZATION & COORDINATE PERTURBATION TEST", flush=True)
    print("=" * 80, flush=True)

    events_all = pd.read_parquet(PROJECT_ROOT / "data" / "interim" / "ds08_stage8_25_physical_events.parquet")
    train_events_df = events_all[events_all["year"] < 2025].reset_index(drop=True)

    def haversine_km(lat1, lon1, lat2, lon2):
        r = 6371.0
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlam = math.radians(lon2 - lon1)
        a = math.sin(dphi / 2.0)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2.0)**2
        return r * 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

    nearest_tr_distances = []
    for _, te in test_h0_df.iterrows():
        tlat, tlon = te["centroid_lat"], te["centroid_lon"]
        d_min = min(haversine_km(tlat, tlon, tre["centroid_lat"], tre["centroid_lon"]) for _, tre in train_events_df.iterrows())
        nearest_tr_distances.append(d_min)

    print(f"Test-to-Train Geographic Separation: Min = {min(nearest_tr_distances):.1f} km, Mean = {np.mean(nearest_tr_distances):.1f} km, Max = {max(nearest_tr_distances):.1f} km")

    # Coordinate perturbation test on test_h0_df
    # Add +/- 0.05 deg (~5.5 km) perturbation to lat/lon and measure prediction change
    pert_prob_changes = []
    pert_pred_changes = 0
    full_probs_h0 = eval_with_temp_h0["probs"]

    for jitter in [0.02, 0.05]:
        pert_df = test_h0_df.copy()
        np.random.seed(42)
        pert_df["centroid_lat"] += np.random.uniform(-jitter, jitter, size=len(pert_df))
        pert_df["centroid_lon"] += np.random.uniform(-jitter, jitter, size=len(pert_df))
        X_pert_tab = apply_scaler(pert_df, scaler_full)
        X_pert = torch.cat([z_test_h0, X_pert_tab], dim=-1)
        eval_pert = evaluate_model(full_clf, X_pert, y_test_h0)
        p_diff = np.mean(np.abs(full_probs_h0 - eval_pert["probs"]))
        n_flips = int((eval_with_temp_h0["preds"] != eval_pert["preds"]).sum())
        pert_prob_changes.append({"jitter_deg": jitter, "mean_prob_diff": float(p_diff), "prediction_flips": n_flips})
        print(f"Coordinate Jitter +/- {jitter} deg (~{jitter*111:.1f} km): Mean Prob Shift = {p_diff:.4f}, Prediction Flips = {n_flips}/{len(test_h0_df)}")

    # =========================================================================
    # SECTION 11: REGISTRY PERMUTATION & RANDOM REGISTRY CONTROL
    # =========================================================================
    print("\n" + "=" * 80, flush=True)
    print("SECTION 11: REGISTRY PERMUTATION & RANDOM REGISTRY CONTROL", flush=True)
    print("=" * 80, flush=True)

    # Random Registry Control: randomly relocate the 52 persistent registry coordinates across India
    with open(PROJECT_ROOT / "data" / "reference" / "ds08" / "manifests" / "stage8_25" / "persistent_source_manifest.json") as f:
        real_sources = json.load(f)["sources"]

    np.random.seed(999)
    # Generate 52 random coordinates across India bounding box (Lat: 8..32, Lon: 70..90)
    rand_lats = np.random.uniform(8.0, 32.0, size=52)
    rand_lons = np.random.uniform(70.0, 90.0, size=52)

    def recompute_random_registry_features(df):
        df_mod = df.copy()
        new_dists = []
        for _, r in df_mod.iterrows():
            d = min(haversine_km(r["centroid_lat"], r["centroid_lon"], rlat, rlon) for rlat, rlon in zip(rand_lats, rand_lons))
            new_dists.append(d)
        df_mod["dist_to_persistent_registry_km"] = new_dists
        df_mod["within_1km_persistent_registry"] = [1.0 if d <= 1.0 else 0.0 for d in new_dists]
        df_mod["within_5km_persistent_registry"] = [1.0 if d <= 5.0 else 0.0 for d in new_dists]
        return df_mod

    train_df_rand = recompute_random_registry_features(train_df)
    val_df_rand = recompute_random_registry_features(val_df)
    test_h0_df_rand = recompute_random_registry_features(test_h0_df)

    scaler_rand = fit_scaler(train_df_rand, FEATURE_COLS_ALL)
    X_tr_rand = torch.cat([z_dict["train"], apply_scaler(train_df_rand, scaler_rand)], dim=-1)
    X_va_rand = torch.cat([z_dict["val"], apply_scaler(val_df_rand, scaler_rand)], dim=-1)
    X_te_rand = torch.cat([z_test_h0, apply_scaler(test_h0_df_rand, scaler_rand)], dim=-1)

    clf_rand = train_classifier(X_tr_rand, y_train, X_va_rand, y_val, in_dim=X_tr_rand.shape[-1], epochs=100)
    eval_rand = evaluate_model(clf_rand, X_te_rand, y_test_h0)

    print(f"FULL Model Accuracy (Real Registry):   {eval_with_temp_h0['accuracy']*100:.2f}%")
    print(f"NO_REGISTRY Model Accuracy:             {ablation_results[1]['H0_Accuracy']*100:.2f}%")
    print(f"RANDOM_REGISTRY Model Accuracy:         {eval_rand['accuracy']*100:.2f}%, Macro-F1 = {eval_rand['macro_f1']:.4f}")
    print(f"Random Registry Confusion Matrix:       {eval_rand['confusion_matrix']}")

    # =========================================================================
    # SECTION 12: PREDICTION FLIP ANALYSIS (FULL vs NO_REGISTRY)
    # =========================================================================
    print("\n" + "=" * 80, flush=True)
    print("SECTION 12: PREDICTION FLIP ANALYSIS (FULL vs NO_REGISTRY)", flush=True)
    print("=" * 80, flush=True)

    full_preds = eval_with_temp_h0["preds"]
    no_reg_preds = ablation_results[1]["Model"] # from NO_PERSISTENT_REGISTRY
    eval_no_reg = evaluate_model(no_reg_clf, torch.cat([z_test_h0, apply_scaler(test_h0_df, no_reg_scaler)], dim=-1), y_test_h0)
    no_reg_preds_arr = eval_no_reg["preds"]
    no_reg_probs_arr = eval_no_reg["probs"]

    flip_records = []
    for i, row in test_h0_df.iterrows():
        eid = row["event_id"]
        tc = row["target_class"]
        cid = int(row["class_id"])
        p_full = int(full_preds[i])
        p_noreg = int(no_reg_preds_arr[i])
        prob_full = full_probs_h0[i]
        prob_noreg = no_reg_probs_arr[i]

        d_per = float(row["dist_to_persistent_registry_km"])
        d_fac = float(row["dist_to_fac_km"])
        c_frp = float(row["current_frp"])
        emb_norm = float(torch.norm(z_test_h0[i]).item())

        is_flipped = bool(p_full != p_noreg)
        if is_flipped:
            reason = f"Flip from {CLASS_NAMES[p_full][:15]} to {CLASS_NAMES[p_noreg][:15]} when registry distance ({d_per:.2f}km) is removed."
        else:
            reason = "Stable prediction (invariant to persistent registry)."

        flip_records.append({
            "event_id": eid,
            "true_class": tc,
            "class_id": cid,
            "full_prediction": CLASS_NAMES[p_full],
            "no_reg_prediction": CLASS_NAMES[p_noreg],
            "full_confidence": float(np.max(prob_full)),
            "no_reg_confidence": float(np.max(prob_noreg)),
            "full_prob_target": float(prob_full[cid]),
            "no_reg_prob_target": float(prob_noreg[cid]),
            "prediction_flipped": is_flipped,
            "dist_to_persistent_registry_km": d_per,
            "dist_to_facility_km": d_fac,
            "current_frp": c_frp,
            "temporal_emb_norm": emb_norm,
            "flip_reason": reason
        })

    df_flips = pd.DataFrame(flip_records)
    flips_out_path = artifacts_dir / "prediction_flip_analysis.csv"
    df_flips.to_csv(flips_out_path, index=False)
    print(f"Wrote prediction flip analysis to {flips_out_path}", flush=True)

    flipped_count = df_flips["prediction_flipped"].sum()
    print(f"Total Prediction Flips: {flipped_count} / {len(df_flips)} ({flipped_count/len(df_flips)*100:.1f}%)")
    for _, fr in df_flips[df_flips["prediction_flipped"]].iterrows():
        print(f"  Event: {fr['event_id'][:35]} | True: {fr['true_class'][:12]} | Full: {fr['full_prediction'][:12]} -> NoReg: {fr['no_reg_prediction'][:12]}")

    # =========================================================================
    # SECTION 13: SMALL-SAMPLE UNCERTAINTY QUANTIFICATION
    # =========================================================================
    print("\n" + "=" * 80, flush=True)
    print("SECTION 13: SMALL-SAMPLE UNCERTAINTY QUANTIFICATION (N=28)", flush=True)
    print("=" * 80, flush=True)

    discrete_table = [
        {"correct_events": 28, "total_events": 28, "accuracy": 1.0000, "description": "100.0% perfect benchmark"},
        {"correct_events": 27, "total_events": 28, "accuracy": 0.9643, "description": "Stage 8.28 verified full model (1 error)"},
        {"correct_events": 26, "total_events": 28, "accuracy": 0.9286, "description": "Stage 8.28 H24 / Stage 8.29 no-registry (2 errors)"},
        {"correct_events": 25, "total_events": 28, "accuracy": 0.8929, "description": "Stage 8.27 reported (3 errors)"},
        {"correct_events": 24, "total_events": 28, "accuracy": 0.8571, "description": "Lowest integer passing 85% threshold (4 errors)"},
        {"correct_events": 23, "total_events": 28, "accuracy": 0.8214, "description": "First failing integer below 85% threshold (5 errors)"}
    ]
    df_discrete = pd.DataFrame(discrete_table)
    print(df_discrete)

    # Save summary JSON
    summary_data = {
        "metadata": {
            "stage": "8.29",
            "date": "2026-10-04",
            "test_events_count": 28
        },
        "ablations_h0": ablation_results,
        "no_registry_horizons": horizon_records,
        "temporal_value_test": temporal_value_summary,
        "spatial_memorization": {
            "nearest_train_distance_km_mean": float(np.mean(nearest_tr_distances)),
            "nearest_train_distance_km_min": float(min(nearest_tr_distances)),
            "coordinate_perturbation_tests": pert_prob_changes
        },
        "registry_permutation_test": {
            "full_accuracy": eval_with_temp_h0["accuracy"],
            "no_registry_accuracy": eval_no_reg["accuracy"],
            "random_registry_accuracy": eval_rand["accuracy"],
            "random_registry_macro_f1": eval_rand["macro_f1"]
        },
        "prediction_flips": {
            "total_flips": int(flipped_count),
            "flipped_events": df_flips[df_flips["prediction_flipped"]][["event_id", "true_class", "full_prediction", "no_reg_prediction"]].to_dict(orient="records")
        },
        "small_sample_uncertainty": {
            "discrete_levels": discrete_table,
            "single_event_sensitivity_pct": 3.5714
        }
    }

    with open(artifacts_dir / "stage8_29_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2)
    print(f"\nWrote full Stage 8.29 summary JSON to {artifacts_dir / 'stage8_29_summary.json'}", flush=True)

    return summary_data

if __name__ == "__main__":
    run_all_experiments()
