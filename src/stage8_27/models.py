"""
Stage 8.27 Causal Temporal & Hierarchical Attribution Models.
Contains:
1. CausalEarlyTemporalEncoder (GRU / Causal TCN based sequence processor)
2. HierarchicalCausalClassifier (3-stage tree with multi-horizon auxiliary forecasting heads)
3. FlatCausalClassifier (Flat 4-class baseline)
"""

import math
from typing import Dict, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F

class CausalEarlyTemporalEncoder(nn.Module):
    """
    Causal sequence encoder for variable-length prefixes of thermal observations.
    Input per timestep: [frp, bright_ti4, bright_ti5, delta_ti, is_night, elapsed_hours] (6D).
    Output: z_early in R^64.
    Strictly causal: processes observations strictly in chronological order without future attention.
    """
    def __init__(self, in_features: int = 6, hidden_dim: int = 64, out_dim: int = 64):
        super().__init__()
        self.in_proj = nn.Sequential(
            nn.Linear(in_features, hidden_dim),
            nn.ReLU(),
            nn.LayerNorm(hidden_dim)
        )
        # Causal GRU (unidirectional)
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

    def forward(self, x_seq: torch.Tensor, lengths: torch.Tensor = None) -> torch.Tensor:
        """
        x_seq: (B, L, in_features)
        lengths: (B,) number of valid observations per sample
        """
        b, l, d = x_seq.shape
        h = self.in_proj(x_seq)
        out, h_n = self.gru(h)
        # Take the representation at the final valid observation
        if lengths is not None:
            batch_idx = torch.arange(b, device=x_seq.device)
            last_idx = torch.clamp(lengths - 1, min=0)
            z_last = out[batch_idx, last_idx]
        else:
            z_last = out[:, -1]
        z_early = self.out_proj(z_last)
        return z_early

class HierarchicalCausalClassifier(nn.Module):
    """
    Hierarchical 3-Stage Attribution Classifier:
    Head 1: Acute vs Persistent (Other Thermal Source)
    Head 2: Industrial vs Biomass
    Head 3: Forest vs Agricultural
    Auxiliary heads: Next FRP prediction, Acute/Persistent state forecasting.
    """
    def __init__(self, in_dim: int = 80, hidden_dim: int = 64):
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
    Flat 4-class baseline classifier.
    """
    def __init__(self, in_dim: int = 80, hidden_dim: int = 64, num_classes: int = 4):
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
