"""Stage 8.34 Deep Learning Model Architectures.

Implements small, robust, pure PyTorch neural models:
1. StaticMLP: Concise baseline MLP on concatenated clean features.
2. GroupedGatedMLP: Per-modality Group Encoders with Sigmoid gating and Residual fusion.
3. PersistenceGatedMLP: Dedicated historical recurrence sub-branch for persistence disentanglement.
4. MultiTaskMLP: Shared representation with auxiliary binary persistence & 3-class acute heads.
5. CausalTCN_MLP: Integrates causal dilated 1D temporal convolution for historical sequences.

STRICT CONSTRAINTS:
- Pure PyTorch Deep Learning (Zero classical ML models in deployment).
- Compact architectures (< 50,000 parameters) to prevent overfitting on N=131 development cohort.
"""

from typing import Dict, List, Optional, Tuple, Any
import torch
import torch.nn as nn
import torch.nn.functional as F

# =====================================================================
# Base Components
# =====================================================================

class GroupEncoder(nn.Module):
    """Encodes a single physical modality into a latent vector."""
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
    """Learned modality gating weights with residual projection."""
    def __init__(self, hidden_dim: int, num_groups: int, dropout: float = 0.15):
        super().__init__()
        self.gate_proj = nn.ModuleList([
            nn.Sequential(
                nn.Linear(hidden_dim, hidden_dim),
                nn.Sigmoid()
            ) for _ in range(num_groups)
        ])
        self.fusion = nn.Sequential(
            nn.Linear(num_groups * hidden_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout)
        )

    def forward(self, group_embs: List[torch.Tensor]) -> torch.Tensor:
        gated = [self.gate_proj[i](emb) * emb for i, emb in enumerate(group_embs)]
        concat = torch.cat(gated, dim=-1)
        return self.fusion(concat)

class CausalConv1dBlock(nn.Module):
    """Dilated causal 1D convolution block with left-padding to prevent lookahead."""
    def __init__(self, in_channels: int, out_channels: int, kernel_size: int = 3, dilation: int = 1, dropout: float = 0.15):
        super().__init__()
        self.pad_len = (kernel_size - 1) * dilation
        self.conv1 = nn.Conv1d(in_channels, out_channels, kernel_size=kernel_size, dilation=dilation, padding=0)
        self.norm1 = nn.BatchNorm1d(out_channels)
        self.act1 = nn.GELU()
        self.drop1 = nn.Dropout(dropout)
        self.residual = nn.Conv1d(in_channels, out_channels, 1) if in_channels != out_channels else nn.Identity()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        res = self.residual(x)
        x_pad = F.pad(x, (self.pad_len, 0))
        out = self.drop1(self.act1(self.norm1(self.conv1(x_pad))))
        return out + res

class CausalTCNEncoder(nn.Module):
    """Lightweight 2-layer causal TCN for pre-alert FIRMS sequences."""
    def __init__(self, in_channels: int = 11, hidden_dim: int = 32, dropout: float = 0.15):
        super().__init__()
        self.block1 = CausalConv1dBlock(in_channels, hidden_dim, kernel_size=3, dilation=1, dropout=dropout)
        self.block2 = CausalConv1dBlock(hidden_dim, hidden_dim, kernel_size=3, dilation=2, dropout=dropout)
        self.pool = nn.AdaptiveAvgPool1d(1)

    def forward(self, seq_tensor: torch.Tensor, seq_mask: Optional[torch.Tensor] = None) -> torch.Tensor:
        # seq_tensor: (B, T, C) -> transpose to (B, C, T)
        x = seq_tensor.transpose(1, 2)
        h = self.block2(self.block1(x))
        pooled = self.pool(h).squeeze(-1)
        return pooled

# =====================================================================
# Architectures
# =====================================================================

class Architecture1_StaticMLP(nn.Module):
    """Concise 2-layer MLP on concatenated clean features."""
    def __init__(self, group_dims: Dict[str, int], hidden_dim: int = 48, num_classes: int = 4, dropout: float = 0.15):
        super().__init__()
        total_dim = sum(group_dims.values())
        self.net = nn.Sequential(
            nn.Linear(total_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.LayerNorm(hidden_dim // 2),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim // 2, num_classes)
        )

    def forward(self, batch: Dict[str, Any]) -> Dict[str, torch.Tensor]:
        feats = []
        for grp in ["thermal", "industrial", "ecoregion", "historical"]:
            if f"{grp}_feats" in batch:
                feats.append(batch[f"{grp}_feats"])
        x = torch.cat(feats, dim=-1)
        logits = self.net(x)
        return {"logits": logits, "probs": F.softmax(logits, dim=-1)}

class Architecture2_GroupedGatedMLP(nn.Module):
    """Per-modality Group Encoders with Sigmoid Gating and Residual Fusion."""
    def __init__(self, group_dims: Dict[str, int], hidden_dim: int = 32, num_classes: int = 4, dropout: float = 0.15):
        super().__init__()
        self.groups = ["thermal", "industrial", "ecoregion", "historical"]
        self.encoders = nn.ModuleDict({
            g: GroupEncoder(group_dims.get(g, 0), hidden_dim, dropout)
            for g in self.groups
        })
        self.fusion = GatedResidualFusion(hidden_dim, num_groups=len(self.groups), dropout=dropout)
        self.classifier = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, num_classes)
        )

    def forward(self, batch: Dict[str, Any]) -> Dict[str, torch.Tensor]:
        embs = [self.encoders[g](batch[f"{g}_feats"]) for g in self.groups]
        fused = self.fusion(embs)
        logits = self.classifier(fused)
        return {"logits": logits, "probs": F.softmax(logits, dim=-1)}

class Architecture3_PersistenceGatedMLP(nn.Module):
    """
    Dedicated historical recurrence persistence branch.
    Outputs:
    - p_pers: P(class=3 | historical recurrence)
    - p_acute: P(class in {0,1,2} | thermal, industrial, ecoregion)
    - final_probs: (1 - p_pers) * p_acute for classes 0..2, p_pers for class 3.
    """
    def __init__(self, group_dims: Dict[str, int], hidden_dim: int = 32, dropout: float = 0.15):
        super().__init__()
        self.hist_encoder = GroupEncoder(group_dims.get("historical", 0), hidden_dim, dropout)
        self.persistence_head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.GELU(),
            nn.Linear(hidden_dim // 2, 1)
        )

        acute_groups = ["thermal", "industrial", "ecoregion"]
        self.acute_encoders = nn.ModuleDict({
            g: GroupEncoder(group_dims.get(g, 0), hidden_dim, dropout)
            for g in acute_groups
        })
        self.acute_fusion = GatedResidualFusion(hidden_dim, num_groups=len(acute_groups), dropout=dropout)
        self.acute_classifier = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, 3)  # 0=Ind, 1=Forest, 2=Agri
        )

    def forward(self, batch: Dict[str, Any]) -> Dict[str, torch.Tensor]:
        # Persistence branch
        h_emb = self.hist_encoder(batch["historical_feats"])
        pers_logit = self.persistence_head(h_emb)
        p_pers = torch.sigmoid(pers_logit)  # (B, 1)

        # Acute branch
        acute_embs = [self.acute_encoders[g](batch[f"{g}_feats"]) for g in ["thermal", "industrial", "ecoregion"]]
        fused_acute = self.acute_fusion(acute_embs)
        acute_logits = self.acute_classifier(fused_acute)
        p_acute = F.softmax(acute_logits, dim=-1)  # (B, 3)

        # Unified 4-class probabilities
        # classes 0..2: (1 - p_pers) * p_acute_i
        # class 3: p_pers
        prob_012 = (1.0 - p_pers) * p_acute
        probs = torch.cat([prob_012, p_pers], dim=-1)
        # Compute pseudo-logits for loss compatibility
        eps = 1e-7
        logits = torch.log(probs.clamp(min=eps))

        return {
            "logits": logits,
            "probs": probs,
            "pers_prob": p_pers.squeeze(-1),
            "acute_probs": p_acute
        }

class Architecture4_MultiTaskMLP(nn.Module):
    """Shared representation with joint multi-task heads."""
    def __init__(self, group_dims: Dict[str, int], hidden_dim: int = 32, dropout: float = 0.15):
        super().__init__()
        self.groups = ["thermal", "industrial", "ecoregion", "historical"]
        self.encoders = nn.ModuleDict({
            g: GroupEncoder(group_dims.get(g, 0), hidden_dim, dropout)
            for g in self.groups
        })
        self.fusion = GatedResidualFusion(hidden_dim, num_groups=len(self.groups), dropout=dropout)
        
        # Primary head (4-class)
        self.primary_head = nn.Linear(hidden_dim, 4)
        # Auxiliary heads
        self.aux_pers_head = nn.Linear(hidden_dim, 1)
        self.aux_acute_head = nn.Linear(hidden_dim, 3)

    def forward(self, batch: Dict[str, Any]) -> Dict[str, torch.Tensor]:
        embs = [self.encoders[g](batch[f"{g}_feats"]) for g in self.groups]
        fused = self.fusion(embs)
        
        logits = self.primary_head(fused)
        aux_pers = self.aux_pers_head(fused).squeeze(-1)
        aux_acute = self.aux_acute_head(fused)

        return {
            "logits": logits,
            "probs": F.softmax(logits, dim=-1),
            "aux_pers_logits": aux_pers,
            "aux_acute_logits": aux_acute
        }

class Architecture5_CausalTCN_MLP(nn.Module):
    """Grouped Gated MLP + Causal 1D TCN for historical sequence tensor."""
    def __init__(self, group_dims: Dict[str, int], hidden_dim: int = 32, num_classes: int = 4, dropout: float = 0.15):
        super().__init__()
        self.tabular_groups = ["thermal", "industrial", "ecoregion", "historical"]
        self.encoders = nn.ModuleDict({
            g: GroupEncoder(group_dims.get(g, 0), hidden_dim, dropout)
            for g in self.tabular_groups
        })
        self.tcn = CausalTCNEncoder(in_channels=11, hidden_dim=hidden_dim, dropout=dropout)
        
        # 5 groups total: 4 tabular + 1 TCN sequence
        self.fusion = GatedResidualFusion(hidden_dim, num_groups=5, dropout=dropout)
        self.classifier = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, num_classes)
        )

    def forward(self, batch: Dict[str, Any]) -> Dict[str, torch.Tensor]:
        embs = [self.encoders[g](batch[f"{g}_feats"]) for g in self.tabular_groups]
        tcn_emb = self.tcn(batch["seq_tensor"], batch.get("seq_mask"))
        embs.append(tcn_emb)
        fused = self.fusion(embs)
        logits = self.classifier(fused)
        return {"logits": logits, "probs": F.softmax(logits, dim=-1)}
