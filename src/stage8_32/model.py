"""
Stage 8.32 Deep Learning Architecture Module.
Implements:
1. Grouped Feature Encoders with LayerNorm, GELU, and Dropout.
2. Gated Residual Multimodal Fusion.
3. Residual MLP representation blocks.
4. Direct, Hierarchical, and Multi-Task heads.
5. Focal Loss and Multi-Task Loss functions.
"""

from typing import Dict, List, Optional, Tuple, Any
import torch
import torch.nn as nn
import torch.nn.functional as F

class GroupEncoder(nn.Module):
    """Encodes a single physical modality into a latent embedding."""
    def __init__(self, in_features: int, hidden_dim: int, dropout: float = 0.15):
        super().__init__()
        if in_features > 0:
            self.net = nn.Sequential(
                nn.Linear(in_features, hidden_dim),
                nn.LayerNorm(hidden_dim),
                nn.GELU(),
                nn.Dropout(dropout)
            )
        else:
            self.net = None

    def forward(self, x: torch.Tensor) -> Optional[torch.Tensor]:
        if self.net is not None and x.shape[-1] > 0:
            return self.net(x)
        return None

class GatedResidualFusion(nn.Module):
    """
    Computes learned gating weights across active modality representations
    and fuses them with residual LayerNorm connections.
    """
    def __init__(self, hidden_dim: int, num_groups: int, dropout: float = 0.15):
        super().__init__()
        self.hidden_dim = hidden_dim
        # Gating gate generator for each group
        self.gate_proj = nn.ModuleList([
            nn.Sequential(
                nn.Linear(hidden_dim, hidden_dim),
                nn.Sigmoid()
            ) for _ in range(num_groups)
        ])
        self.fusion_proj = nn.Sequential(
            nn.Linear(num_groups * hidden_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout)
        )

    def forward(self, group_embs: List[torch.Tensor]) -> torch.Tensor:
        gated_embs = []
        for i, emb in enumerate(group_embs):
            gate = self.gate_proj[i](emb)
            gated_embs.append(gate * emb)
        concat_all = torch.cat(gated_embs, dim=-1)
        fused = self.fusion_proj(concat_all)
        return fused

class ResidualBlock(nn.Module):
    """Residual MLP block with pre-norm, GELU, and skip connection."""
    def __init__(self, hidden_dim: int, dropout: float = 0.15):
        super().__init__()
        self.norm = nn.LayerNorm(hidden_dim)
        self.fc1 = nn.Linear(hidden_dim, hidden_dim * 2)
        self.act = nn.GELU()
        self.fc2 = nn.Linear(hidden_dim * 2, hidden_dim)
        self.drop = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        residual = x
        h = self.fc2(self.drop(self.act(self.fc1(self.norm(x)))))
        return residual + self.drop(h)

class GroupedCausalThermalClassifier(nn.Module):
    """
    Clean Deep Learning Only Classifier for 4-Class Thermal Attribution.
    Strictly registry-free and causal.
    """
    def __init__(
        self,
        group_dims: Dict[str, int],
        hidden_dim: int = 64,
        num_res_blocks: int = 2,
        dropout: float = 0.15,
        num_classes: int = 4,
        active_groups: Optional[List[str]] = None
    ):
        super().__init__()
        self.hidden_dim = hidden_dim
        self.active_groups = active_groups or ["thermal", "historical", "industrial", "ecoregion", "geographic"]
        self.active_groups = [g for g in self.active_groups if group_dims.get(g, 0) > 0]

        # Individual group encoders
        self.encoders = nn.ModuleDict()
        for grp in self.active_groups:
            self.encoders[grp] = GroupEncoder(group_dims[grp], hidden_dim, dropout=dropout)

        # Gated fusion
        self.fusion = GatedResidualFusion(hidden_dim, len(self.active_groups), dropout=dropout)

        # Residual representation stack
        self.res_blocks = nn.ModuleList([
            ResidualBlock(hidden_dim, dropout=dropout) for _ in range(num_res_blocks)
        ])
        self.out_norm = nn.LayerNorm(hidden_dim)

        # Heads
        self.classifier_head = nn.Linear(hidden_dim, num_classes)
        self.binary_head = nn.Linear(hidden_dim, 2)       # Acute (0) vs Persistent (1)
        self.subclass_head = nn.Linear(hidden_dim, 3)     # Ind (0), For (1), Agr (2)

    def forward(self, batch: Dict[str, torch.Tensor]) -> Dict[str, torch.Tensor]:
        embs = []
        for grp in self.active_groups:
            key = f"{grp}_feats"
            if key in batch:
                enc = self.encoders[grp](batch[key])
                if enc is not None:
                    embs.append(enc)

        assert len(embs) == len(self.active_groups), "Mismatch between active groups and batch tensors"

        fused = self.fusion(embs)

        h = fused
        for block in self.res_blocks:
            h = block(h)
        latent = self.out_norm(h)

        logits_4class = self.classifier_head(latent)
        logits_binary = self.binary_head(latent)
        logits_subclass = self.subclass_head(latent)

        return {
            "logits_4class": logits_4class,
            "logits_binary": logits_binary,
            "logits_subclass": logits_subclass,
            "latent": latent
        }

    def predict_probabilities(
        self,
        batch: Dict[str, torch.Tensor],
        mode: str = "multi_task_blend"
    ) -> torch.Tensor:
        """
        Computes 4-class probabilities under specified inference mode:
        - 'direct_4class': Softmax(logits_4class)
        - 'hierarchical': P(per) = P(bin=1); P(acute_c) = P(bin=0) * P(sub=c)
        - 'multi_task_blend': 0.5 * P_direct + 0.5 * P_hierarchical
        """
        out = self.forward(batch)
        p_direct = F.softmax(out["logits_4class"], dim=-1)

        p_bin = F.softmax(out["logits_binary"], dim=-1)
        p_sub = F.softmax(out["logits_subclass"], dim=-1)

        p_hier = torch.zeros_like(p_direct)
        p_hier[:, 0] = p_bin[:, 0] * p_sub[:, 0] # Ind
        p_hier[:, 1] = p_bin[:, 0] * p_sub[:, 1] # For
        p_hier[:, 2] = p_bin[:, 0] * p_sub[:, 2] # Agr
        p_hier[:, 3] = p_bin[:, 1]               # Per

        if mode == "direct_4class":
            return p_direct
        elif mode == "hierarchical":
            return p_hier
        else: # multi_task_blend
            return 0.5 * p_direct + 0.5 * p_hier

class FocalLoss(nn.Module):
    """Multi-class Focal Loss with class-weighting and focusing parameter gamma."""
    def __init__(self, alpha: Optional[torch.Tensor] = None, gamma: float = 2.0):
        super().__init__()
        self.alpha = alpha
        self.gamma = gamma

    def forward(self, logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        log_p = F.log_softmax(logits, dim=-1)
        p = torch.exp(log_p)

        target_one_hot = F.one_hot(targets, num_classes=logits.size(-1)).float()
        p_t = (p * target_one_hot).sum(dim=-1)
        log_p_t = (log_p * target_one_hot).sum(dim=-1)

        loss = - ((1.0 - p_t) ** self.gamma) * log_p_t

        if self.alpha is not None:
            alpha_t = (self.alpha.to(targets.device) * target_one_hot).sum(dim=-1)
            loss = alpha_t * loss

        return loss.mean()
