"""
Stage 8.28 Causal Temporal Encoder and Hierarchical Attribution Classifier.

Components:
1. CausalEarlyTemporalEncoder:
   - 2-layer unidirectional GRU (hidden_dim=64)
   - strictly causal: no future timestep access, no bidirectional recurrence
   - explicit next-step forecasting heads:
     * head_next_frp: predicts FRP at t+1
     * head_next_delta_t: predicts elapsed hours to t+1
   - produces z_early in R^64 at latest observed timestep
2. HierarchicalCausalClassifier:
   - Takes combined [z_early (64D), causal_tabular_features (30D)] = 94D
   - 3-stage hierarchical attribution:
     * Stage 1: Acute Fire vs Persistent Non-Biomass
     * Stage 2: Industrial Fire vs Biomass Fire
     * Stage 3: Forest Fire vs Agricultural Fire
   - Auxiliary heads for self-supervision: next FRP, acute state
3. FlatCausalClassifier:
   - Flat 4-class baseline for stress tests, ablations, and label permutation tests
"""

import math
from typing import Dict, Tuple, Optional

import torch
import torch.nn as nn
import torch.nn.functional as F

class CausalEarlyTemporalEncoder(nn.Module):
    """
    Causal sequence encoder for variable-length prefixes of thermal observations.
    Input per timestep: [frp, bright_ti4, bright_ti5, delta_ti, is_night, elapsed_hours] (6D).
    Output: z_early in R^64.
    Strictly causal: processes observations strictly in chronological order without future attention.
    Equipped with next-step forecasting heads for self-supervised causal training.
    """
    def __init__(self, in_features: int = 6, hidden_dim: int = 64, out_dim: int = 64):
        super().__init__()
        self.in_proj = nn.Sequential(
            nn.Linear(in_features, hidden_dim),
            nn.ReLU(),
            nn.LayerNorm(hidden_dim)
        )
        # Causal GRU (strictly unidirectional, 2 layers)
        self.gru = nn.GRU(
            input_size=hidden_dim,
            hidden_size=hidden_dim,
            num_layers=2,
            batch_first=True,
            bidirectional=False
        )
        self.out_proj = nn.Sequential(
            nn.Linear(hidden_dim, out_dim),
            nn.ReLU(),
            nn.LayerNorm(out_dim)
        )
        # Explicit next-step forecasting heads (Section 6)
        self.head_next_frp = nn.Sequential(
            nn.Linear(hidden_dim, 32),
            nn.ReLU(),
            nn.Linear(32, 1)
        )
        self.head_next_delta_t = nn.Sequential(
            nn.Linear(hidden_dim, 32),
            nn.ReLU(),
            nn.Linear(32, 1)
        )

    def forward_sequence(self, x_seq: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Processes full sequence causally and produces next-step predictions for all valid steps t < L-1.
        x_seq: (B, L, 6)
        Returns:
            pred_next_frp: (B, L-1)
            pred_next_delta_t: (B, L-1)
            z_seq: (B, L, out_dim)
        """
        b, l, d = x_seq.shape
        h = self.in_proj(x_seq)
        gru_out, _ = self.gru(h) # (B, L, hidden_dim)
        z_seq = self.out_proj(gru_out)

        if l > 1:
            # Predict for timesteps 0 to L-2
            h_prefix = gru_out[:, :-1, :] # (B, L-1, hidden_dim)
            pred_next_frp = self.head_next_frp(h_prefix).squeeze(-1) # (B, L-1)
            pred_next_delta_t = self.head_next_delta_t(h_prefix).squeeze(-1) # (B, L-1)
        else:
            pred_next_frp = torch.zeros((b, 0), device=x_seq.device)
            pred_next_delta_t = torch.zeros((b, 0), device=x_seq.device)

        return pred_next_frp, pred_next_delta_t, z_seq

    def forward(self, x_seq: torch.Tensor, lengths: Optional[torch.Tensor] = None) -> torch.Tensor:
        """
        Extracts causal embedding z_early at the latest valid observation for each sample.
        x_seq: (B, L, 6)
        lengths: (B,) number of valid observations per sequence
        Returns:
            z_early: (B, out_dim)
        """
        b, l, d = x_seq.shape
        h = self.in_proj(x_seq)
        gru_out, _ = self.gru(h)
        if lengths is not None:
            batch_idx = torch.arange(b, device=x_seq.device)
            last_idx = torch.clamp(lengths - 1, min=0)
            z_last = gru_out[batch_idx, last_idx]
        else:
            z_last = gru_out[:, -1]
        z_early = self.out_proj(z_last)
        return z_early

class HierarchicalCausalClassifier(nn.Module):
    """
    Hierarchical 3-Stage Attribution Classifier:
    Input: [z_early (64D), causal_tabular_features (30D)] = 94D
    Stage 1: Acute Fire (1) vs Persistent Non-Biomass (0)
    Stage 2: Industrial Fire (1) vs Biomass Fire (0)
    Stage 3: Forest Fire (1) vs Agricultural Fire (0)
    Auxiliary heads: Next FRP prediction, Acute/Persistent state forecasting.
    """
    def __init__(self, in_dim: int = 94, hidden_dim: int = 64):
        super().__init__()
        self.backbone = nn.Sequential(
            nn.Linear(in_dim, hidden_dim),
            nn.ReLU(),
            nn.LayerNorm(hidden_dim),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.LayerNorm(hidden_dim)
        )

        # Stage 1: Acute Fire (1) vs Persistent Non-Biomass (0)
        self.head_acute = nn.Linear(hidden_dim, 1)

        # Stage 2: Industrial Fire (1) vs Biomass Fire (0)
        self.head_ind = nn.Linear(hidden_dim, 1)

        # Stage 3: Forest Fire (1) vs Agricultural Fire (0)
        self.head_bio = nn.Linear(hidden_dim, 1)

        # Auxiliary Forecasting Heads (Multi-horizon self-supervision)
        self.aux_next_frp = nn.Linear(hidden_dim, 1)
        self.aux_state = nn.Linear(hidden_dim, 2)

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, Dict[str, torch.Tensor]]:
        feat = self.backbone(x)

        logit_acute = self.head_acute(feat).squeeze(-1)
        logit_ind = self.head_ind(feat).squeeze(-1)
        logit_bio = self.head_bio(feat).squeeze(-1)

        p_acute = torch.sigmoid(logit_acute)
        p_persistent = 1.0 - p_acute

        p_ind_given_acute = torch.sigmoid(logit_ind)
        p_bio_given_acute = 1.0 - p_ind_given_acute

        p_forest_given_bio = torch.sigmoid(logit_bio)
        p_agri_given_bio = 1.0 - p_forest_given_bio

        # Joint 4-class probabilities:
        # Class 0: Industrial Fire
        # Class 1: Forest Fire
        # Class 2: Agricultural Fire
        # Class 3: Other Thermal Source / Persistent Non-Biomass
        p_ind = p_acute * p_ind_given_acute
        p_for = p_acute * p_bio_given_acute * p_forest_given_bio
        p_agr = p_acute * p_bio_given_acute * p_agri_given_bio
        p_per = p_persistent

        probs = torch.stack([p_ind, p_for, p_agr, p_per], dim=-1)
        # Ensure numerical safety
        probs = torch.clamp(probs, min=1e-7, max=1.0)
        probs = probs / probs.sum(dim=-1, keepdim=True)

        aux_outputs = {
            "logit_acute": logit_acute,
            "logit_ind": logit_ind,
            "logit_bio": logit_bio,
            "pred_next_frp": self.aux_next_frp(feat).squeeze(-1),
            "pred_state": self.aux_state(feat)
        }

        return probs, aux_outputs

class FlatCausalClassifier(nn.Module):
    """
    Flat 4-class baseline classifier for stress tests and ablations.
    """
    def __init__(self, in_dim: int = 94, hidden_dim: int = 64, num_classes: int = 4):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(in_dim, hidden_dim),
            nn.ReLU(),
            nn.LayerNorm(hidden_dim),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, num_classes)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        logits = self.net(x)
        probs = F.softmax(logits, dim=-1)
        return probs
