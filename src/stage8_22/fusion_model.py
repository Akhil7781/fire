"""
Stage 8.22: Multimodal Late-Fusion MLP Architecture Module.
Implements the compact, modular late-fusion MLP combining:
- 1D Causal TCN temporal representation (64D)
- Deep SAD anomaly latent representation (32D)
- YOLOv8n infrastructure visual representation (128D)
- YOLOv8n fire/smoke visual representation (128D)
- Sentinel-2 multi-spectral visual representation (128D)
- FIRMS causal geospatial/thermal features (27D)
- Modality presence mask (6D)

Supports missing modalities via explicit mask gating.
Outputs 128D fused representation and 4-class attribution logits.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from src.stage8_22.fusion_cohort import (
    MODALITY_DIMS,
    MODALITY_NAMES,
    TARGET_TAXONOMY,
    CLASS_NAME_TO_ID,
    ID_TO_CLASS_NAME,
)


class ModalityBranch(nn.Module):
    """Normalizes and projects a single modality representation to a common dimension."""

    def __init__(self, in_features: int, proj_dim: int, dropout: float = 0.1):
        super().__init__()
        self.in_features = in_features
        self.proj_dim = proj_dim
        self.norm = nn.LayerNorm(in_features)
        self.proj = nn.Linear(in_features, proj_dim)
        self.dropout = nn.Dropout(p=dropout)

    def forward(self, x: torch.Tensor, mask_val: torch.Tensor) -> torch.Tensor:
        """
        Forward pass with mask gating.
        Args:
            x: Input tensor [B, in_features]
            mask_val: Scalar or [B, 1] presence indicator in {0.0, 1.0}
        Returns:
            Projected representation [B, proj_dim] gated by mask.
        """
        # Ensure mask is [B, 1]
        if mask_val.dim() == 1:
            mask_val = mask_val.unsqueeze(1)

        normed = self.norm(x)
        projected = self.proj(normed)
        projected = F.gelu(projected)
        projected = self.dropout(projected)

        # Hard zero gating for absent modalities
        gated = projected * mask_val
        return gated


class MultimodalLateFusionMLP(nn.Module):
    """
    Compact late-fusion neural network for multimodal thermal-source attribution.
    Combines 6 modalities through branch projections and fusion MLP to 128D representation
    and 4-class output head.
    """

    def __init__(
        self,
        proj_dim: int = 64,
        fusion_hidden_dim: int = 256,
        fused_embedding_dim: int = 128,
        num_classes: int = 4,
        dropout: float = 0.2,
    ):
        super().__init__()
        self.proj_dim = proj_dim
        self.fusion_hidden_dim = fusion_hidden_dim
        self.fused_embedding_dim = fused_embedding_dim
        self.num_classes = num_classes

        # Modality projection branches
        self.branch_tcn = ModalityBranch(MODALITY_DIMS["tcn"], proj_dim, dropout)
        self.branch_sad = ModalityBranch(MODALITY_DIMS["sad"], proj_dim, dropout)
        self.branch_yolo_infra = ModalityBranch(MODALITY_DIMS["yolo_infra"], proj_dim, dropout)
        self.branch_yolo_fire = ModalityBranch(MODALITY_DIMS["yolo_fire"], proj_dim, dropout)
        self.branch_s2 = ModalityBranch(MODALITY_DIMS["s2"], proj_dim, dropout)
        self.branch_geo = ModalityBranch(MODALITY_DIMS["geo"], proj_dim, dropout)

        # Concatenation dimension: 6 branches * proj_dim + 6 mask bits
        concat_dim = len(MODALITY_NAMES) * proj_dim + len(MODALITY_NAMES)

        # Late-fusion MLP
        self.fusion_mlp = nn.Sequential(
            nn.Linear(concat_dim, fusion_hidden_dim),
            nn.LayerNorm(fusion_hidden_dim),
            nn.GELU(),
            nn.Dropout(p=dropout),
            nn.Linear(fusion_hidden_dim, fused_embedding_dim),
            nn.LayerNorm(fused_embedding_dim),
            nn.GELU(),
        )

        # Attribution decision head
        self.classifier_head = nn.Sequential(
            nn.Dropout(p=dropout * 0.5),
            nn.Linear(fused_embedding_dim, num_classes),
        )

    def extract_branches(
        self,
        x_tcn: torch.Tensor,
        x_sad: torch.Tensor,
        x_infra: torch.Tensor,
        x_fire: torch.Tensor,
        x_s2: torch.Tensor,
        x_geo: torch.Tensor,
        mask: torch.Tensor,
    ) -> torch.Tensor:
        """Projects all modality branches and concatenates with mask."""
        # Unpack mask bits [B, 6]
        m_tcn = mask[:, 0:1]
        m_sad = mask[:, 1:2]
        m_infra = mask[:, 2:3]
        m_fire = mask[:, 3:4]
        m_s2 = mask[:, 4:5]
        m_geo = mask[:, 5:6]

        h_tcn = self.branch_tcn(x_tcn, m_tcn)
        h_sad = self.branch_sad(x_sad, m_sad)
        h_infra = self.branch_yolo_infra(x_infra, m_infra)
        h_fire = self.branch_yolo_fire(x_fire, m_fire)
        h_s2 = self.branch_s2(x_s2, m_s2)
        h_geo = self.branch_geo(x_geo, m_geo)

        # Concatenate projected features and mask
        h_cat = torch.cat([h_tcn, h_sad, h_infra, h_fire, h_s2, h_geo, mask], dim=1)
        return h_cat

    def forward(
        self,
        x_tcn: torch.Tensor,
        x_sad: torch.Tensor,
        x_infra: torch.Tensor,
        x_fire: torch.Tensor,
        x_s2: torch.Tensor,
        x_geo: torch.Tensor,
        mask: torch.Tensor,
        return_embeddings: bool = False,
    ) -> Union[torch.Tensor, Tuple[torch.Tensor, torch.Tensor]]:
        """
        Forward pass of late-fusion MLP.
        Returns:
            logits: [B, num_classes] unnormalized classification logits
            (optional) z_fusion: [B, fused_embedding_dim] 128D fused representation
        """
        h_cat = self.extract_branches(x_tcn, x_sad, x_infra, x_fire, x_s2, x_geo, mask)
        z_fusion = self.fusion_mlp(h_cat)
        logits = self.classifier_head(z_fusion)

        if return_embeddings:
            return logits, z_fusion
        return logits

    def predict_probabilities(
        self,
        x_tcn: torch.Tensor,
        x_sad: torch.Tensor,
        x_infra: torch.Tensor,
        x_fire: torch.Tensor,
        x_s2: torch.Tensor,
        x_geo: torch.Tensor,
        mask: torch.Tensor,
    ) -> torch.Tensor:
        """Inference helper returning normalized class probabilities."""
        self.eval()
        with torch.no_grad():
            logits = self.forward(x_tcn, x_sad, x_infra, x_fire, x_s2, x_geo, mask)
            probs = F.softmax(logits, dim=-1)
        return probs

    def save_checkpoint(self, path: Path, extra_metadata: Optional[dict] = None):
        """Saves deterministic checkpoint."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        checkpoint = {
            "model_state_dict": self.state_dict(),
            "proj_dim": self.proj_dim,
            "fusion_hidden_dim": self.fusion_hidden_dim,
            "fused_embedding_dim": self.fused_embedding_dim,
            "num_classes": self.num_classes,
            "metadata": extra_metadata or {},
        }
        torch.save(checkpoint, str(path))

    @classmethod
    def load_checkpoint(cls, path: Path, map_location: str = "cpu") -> "MultimodalLateFusionMLP":
        """Loads model from checkpoint."""
        checkpoint = torch.load(str(path), map_location=map_location)
        model = cls(
            proj_dim=checkpoint.get("proj_dim", 64),
            fusion_hidden_dim=checkpoint.get("fusion_hidden_dim", 256),
            fused_embedding_dim=checkpoint.get("fused_embedding_dim", 128),
            num_classes=checkpoint.get("num_classes", 4),
        )
        model.load_state_dict(checkpoint["model_state_dict"])
        model.eval()
        return model
