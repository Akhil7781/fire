"""
Stage 8.25 Model Architectures:
1. ThermalMultiSensorEncoder (1D-CNN + MLP thermal branch)
2. HierarchicalAttributionClassifier (3-Stage Structured Tree)
3. FlatAttributionClassifier (Flat 4-Class Baseline)
4. SelfSupervisedThermalPretrainer (Masked Timestep Contrastive/Reconstruction)
"""

import math
from typing import Dict, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F

class ThermalMultiSensorEncoder(nn.Module):
    """
    Thermal Multi-Sensor Branch:
    Processes multi-timestep FIRMS thermal observations, FRP dynamics, and baseline statistics.
    Outputs: 64D thermal_multisensor_embedding.
    """
    def __init__(self, in_features: int = 32, hidden_dim: int = 64, out_dim: int = 64):
        super().__init__()
        self.conv1 = nn.Conv1d(1, 16, kernel_size=3, padding=1)
        self.bn1 = nn.BatchNorm1d(16)
        self.conv2 = nn.Conv1d(16, 32, kernel_size=3, padding=1)
        self.bn2 = nn.BatchNorm1d(32)
        self.fc = nn.Sequential(
            nn.Linear(32 * in_features, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(hidden_dim, out_dim)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (batch_size, 32)
        b, f = x.shape
        x_reshaped = x.unsqueeze(1) # (b, 1, 32)
        h = F.relu(self.bn1(self.conv1(x_reshaped)))
        h = F.relu(self.bn2(self.conv2(h)))
        h = h.view(b, -1)
        out = self.fc(h)
        return out

class HierarchicalAttributionClassifier(nn.Module):
    """
    Hierarchical 3-Stage Source-Attribution Classifier:
    - Head 1: Acute Fire vs Persistent Thermal Source (P_acute)
    - Head 2: Industrial vs Biomass Fire (given Acute) (P_ind_given_acute)
    - Head 3: Forest vs Agricultural Fire (given Biomass) (P_for_given_biomass)
    
    Produces 4-class probabilities:
    P(Industrial) = P_acute * P_ind_given_acute
    P(Forest)     = P_acute * (1 - P_ind_given_acute) * P_for_given_biomass
    P(Agri)       = P_acute * (1 - P_ind_given_acute) * (1 - P_for_given_biomass)
    P(Persistent) = 1 - P_acute
    """
    def __init__(self, in_dim: int = 64 + 16 + 16, hidden_dim: int = 64):
        super().__init__()
        self.backbone = nn.Sequential(
            nn.Linear(in_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.15),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU()
        )
        # Head 1: Acute vs Persistent
        self.head_acute = nn.Linear(hidden_dim, 1)
        # Head 2: Industrial vs Biomass
        self.head_industrial = nn.Linear(hidden_dim, 1)
        # Head 3: Forest vs Agricultural
        self.head_biomass = nn.Linear(hidden_dim, 1)

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, Dict[str, torch.Tensor]]:
        h = self.backbone(x)
        
        logit_acute = self.head_acute(h).squeeze(-1)
        logit_ind = self.head_industrial(h).squeeze(-1)
        logit_bio = self.head_biomass(h).squeeze(-1)

        p_acute = torch.sigmoid(logit_acute)
        p_ind_given_acute = torch.sigmoid(logit_ind)
        p_for_given_bio = torch.sigmoid(logit_bio)

        p_industrial = p_acute * p_ind_given_acute
        p_biomass = p_acute * (1.0 - p_ind_given_acute)
        p_forest = p_biomass * p_for_given_bio
        p_agri = p_biomass * (1.0 - p_for_given_bio)
        p_persistent = 1.0 - p_acute

        # Stack into 4-class probabilities [Industrial, Forest, Agri, Persistent]
        probs = torch.stack([p_industrial, p_forest, p_agri, p_persistent], dim=-1)
        # Numerical guard: ensure sum to 1.0 and >= 0.0
        probs = torch.clamp(probs, min=1e-7, max=1.0)
        probs = probs / probs.sum(dim=-1, keepdim=True)

        branch_outputs = {
            "p_acute": p_acute,
            "p_ind_given_acute": p_ind_given_acute,
            "p_for_given_bio": p_for_given_bio,
            "logit_acute": logit_acute,
            "logit_ind": logit_ind,
            "logit_bio": logit_bio
        }
        return probs, branch_outputs

class FlatAttributionClassifier(nn.Module):
    """
    Flat 4-Class Baseline Classifier:
    Direct softmax classification across all 4 classes simultaneously.
    """
    def __init__(self, in_dim: int = 64 + 16 + 16, hidden_dim: int = 64, num_classes: int = 4):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(in_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.15),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, num_classes)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        logits = self.net(x)
        probs = F.softmax(logits, dim=-1)
        return probs

class SelfSupervisedThermalPretrainer(nn.Module):
    """
    Self-Supervised Thermal Pretraining Branch:
    Masked sequence timestep autoencoder.
    Reconstructs randomly masked thermal dimensions (FRP dynamics, brightness, duration).
    """
    def __init__(self, in_features: int = 32, hidden_dim: int = 64):
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(in_features, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim)
        )
        self.decoder = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, in_features)
        )

    def forward(self, x: torch.Tensor, mask_ratio: float = 0.25) -> Tuple[torch.Tensor, torch.Tensor]:
        # Generate random mask
        mask = (torch.rand_like(x) < mask_ratio).float()
        x_masked = x * (1.0 - mask)
        
        encoded = self.encoder(x_masked)
        recon = self.decoder(encoded)
        return recon, mask
