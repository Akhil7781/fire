"""
Stage 8.33 Deep Learning Models & Architecture Optimization Module.
Implements:
1. Pure PyTorch Deep Learning Architectures (Zero classical ML models).
2. Group Encoders, Gated Residual Fusion, Residual MLP blocks.
3. Lightweight Causal Dilated 1D TCN for historical FIRMS sequences.
4. GRU sequence baseline for historical sequence comparison.
5. Dedicated Persistence Representation & Branch.
6. Candidate Models A through G for controlled architectural evaluation.
7. Loss functions: Weighted CE, Focal Loss, Multi-Task Loss, Hierarchical Loss.
"""

from typing import Dict, List, Optional, Tuple, Any
import torch
import torch.nn as nn
import torch.nn.functional as F

# =====================================================================
# 1. Base Components
# =====================================================================

class GroupEncoder(nn.Module):
    """Encodes a single physical modality group into a latent embedding."""
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
    """Learned gating weights across modality representations with residual LayerNorm."""
    def __init__(self, hidden_dim: int, num_groups: int, dropout: float = 0.15):
        super().__init__()
        self.hidden_dim = hidden_dim
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
        return self.fusion_proj(concat_all)

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

# =====================================================================
# 2. Causal Sequence Encoders (TCN and GRU)
# =====================================================================

class CausalConv1dBlock(nn.Module):
    """Dilated causal 1D convolution block with left padding to prevent lookahead."""
    def __init__(self, in_channels: int, out_channels: int, kernel_size: int = 3, dilation: int = 1, dropout: float = 0.15):
        super().__init__()
        self.pad_len = (kernel_size - 1) * dilation
        self.conv1 = nn.Conv1d(in_channels, out_channels, kernel_size=kernel_size, dilation=dilation, padding=0)
        self.norm1 = nn.BatchNorm1d(out_channels)
        self.act1 = nn.GELU()
        self.drop1 = nn.Dropout(dropout)
        self.conv2 = nn.Conv1d(out_channels, out_channels, kernel_size=kernel_size, dilation=dilation, padding=0)
        self.norm2 = nn.BatchNorm1d(out_channels)
        self.act2 = nn.GELU()
        self.drop2 = nn.Dropout(dropout)
        self.residual_conv = nn.Conv1d(in_channels, out_channels, 1) if in_channels != out_channels else nn.Identity()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x is (B, C, T)
        res = self.residual_conv(x)
        # Causal left-pad
        out = F.pad(x, (self.pad_len, 0))
        out = self.drop1(self.act1(self.norm1(self.conv1(out))))
        out = F.pad(out, (self.pad_len, 0))
        out = self.drop2(self.act2(self.norm2(self.conv2(out))))
        return out + res

class CausalTCNEncoder(nn.Module):
    """
    Lightweight Causal TCN processing historical FIRMS sequence (B, T, D=11).
    Uses dilations [1, 2, 4, 8] with kernel_size=3.
    Pools causally using masked average pooling.
    Handles empty / zero-length sequences by returning zero embeddings.
    """
    def __init__(self, in_features: int = 11, hidden_dim: int = 64, dilations: List[int] = [1, 2, 4, 8], dropout: float = 0.15):
        super().__init__()
        self.hidden_dim = hidden_dim
        self.input_proj = nn.Conv1d(in_features, hidden_dim, kernel_size=1)
        
        self.blocks = nn.ModuleList([
            CausalConv1dBlock(hidden_dim, hidden_dim, kernel_size=3, dilation=d, dropout=dropout)
            for d in dilations
        ])
        self.out_proj = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout)
        )

    def forward(self, seq_tensor: torch.Tensor, seq_mask: torch.Tensor) -> torch.Tensor:
        # seq_tensor: (B, T, D), seq_mask: (B, T)
        B, T, D = seq_tensor.shape
        # (B, D, T)
        x = seq_tensor.permute(0, 2, 1)
        x = self.input_proj(x)
        for block in self.blocks:
            x = block(x)
        # x is (B, hidden_dim, T)
        # Masked average pooling
        mask_expanded = seq_mask.unsqueeze(1)  # (B, 1, T)
        x_masked = x * mask_expanded
        sum_mask = mask_expanded.sum(dim=-1).clamp(min=1e-5)  # (B, 1)
        pooled = (x_masked.sum(dim=-1) / sum_mask)  # (B, hidden_dim)

        out = self.out_proj(pooled)
        # For samples where mask sum was zero (empty sequences), zero out representation
        has_any_seq = (seq_mask.sum(dim=-1, keepdim=True) > 0).float()
        return out * has_any_seq

class GRUSequenceEncoder(nn.Module):
    """Baseline GRU sequence encoder processing (B, T, D=11)."""
    def __init__(self, in_features: int = 11, hidden_dim: int = 64, dropout: float = 0.15):
        super().__init__()
        self.gru = nn.GRU(in_features, hidden_dim, batch_first=True, num_layers=1)
        self.out_proj = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout)
        )

    def forward(self, seq_tensor: torch.Tensor, seq_mask: torch.Tensor) -> torch.Tensor:
        # seq_tensor: (B, T, D)
        out, h_n = self.gru(seq_tensor)
        # h_n is (1, B, hidden_dim)
        emb = h_n.squeeze(0)
        out_emb = self.out_proj(emb)
        has_any_seq = (seq_mask.sum(dim=-1, keepdim=True) > 0).float()
        return out_emb * has_any_seq

# =====================================================================
# 3. Dedicated Persistence Representation
# =====================================================================

class DedicatedPersistenceBranch(nn.Module):
    """
    Dedicated Persistence Representation Module.
    Encodes raw FIRMS historical recurrence features directly to predict
    binary persistence (Acute vs Persistent) and provide a clean persistence embedding.
    Ensures that refinery flares near industrial facilities are recognized by recurrence,
    not confused by industrial proximity.
    """
    def __init__(self, hist_dim: int, hidden_dim: int = 64, dropout: float = 0.15):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(hist_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.LayerNorm(hidden_dim // 2),
            nn.GELU()
        )
        self.persistence_head = nn.Linear(hidden_dim // 2, 2)  # Binary: 0=Acute, 1=Persistent

    def forward(self, hist_feats: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        emb = self.net(hist_feats)
        logits_per = self.persistence_head(emb)
        return emb, logits_per

# =====================================================================
# 4. Candidate Model Architectures (A through G)
# =====================================================================

class ModelA_SimpleMLP(nn.Module):
    """MODEL A: Simple Flat MLP directly on concatenated validated features."""
    def __init__(self, total_dim: int, hidden_dim: int = 64, dropout: float = 0.15, num_classes: int = 4):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(total_dim, hidden_dim * 2),
            nn.LayerNorm(hidden_dim * 2),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim * 2, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, num_classes)
        )

    def forward(self, batch: Dict[str, torch.Tensor]) -> Dict[str, torch.Tensor]:
        feats = []
        for grp in ["thermal", "historical", "industrial", "ecoregion", "geographic"]:
            k = f"{grp}_feats"
            if k in batch and batch[k].shape[-1] > 0:
                feats.append(batch[k])
        x = torch.cat(feats, dim=-1)
        logits = self.net(x)
        return {"logits_4class": logits}

    def predict_probabilities(self, batch: Dict[str, torch.Tensor]) -> torch.Tensor:
        return F.softmax(self.forward(batch)["logits_4class"], dim=-1)

class ModelB_GroupedMLP(nn.Module):
    """MODEL B: Grouped MLP with separate group encoders concatenated into residual blocks."""
    def __init__(self, group_dims: Dict[str, int], hidden_dim: int = 64, dropout: float = 0.15, num_classes: int = 4):
        super().__init__()
        self.active_groups = [g for g, d in group_dims.items() if d > 0]
        self.encoders = nn.ModuleDict({
            g: GroupEncoder(group_dims[g], hidden_dim, dropout=dropout)
            for g in self.active_groups
        })
        self.proj = nn.Sequential(
            nn.Linear(len(self.active_groups) * hidden_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout)
        )
        self.res1 = ResidualBlock(hidden_dim, dropout=dropout)
        self.res2 = ResidualBlock(hidden_dim, dropout=dropout)
        self.head = nn.Linear(hidden_dim, num_classes)

    def forward(self, batch: Dict[str, torch.Tensor]) -> Dict[str, torch.Tensor]:
        embs = [self.encoders[g](batch[f"{g}_feats"]) for g in self.active_groups]
        concat = torch.cat(embs, dim=-1)
        h = self.res2(self.res1(self.proj(concat)))
        return {"logits_4class": self.head(h)}

    def predict_probabilities(self, batch: Dict[str, torch.Tensor]) -> torch.Tensor:
        return F.softmax(self.forward(batch)["logits_4class"], dim=-1)

class ModelC_GroupedGatedFusion(nn.Module):
    """MODEL C: Grouped MLP with Gated Residual Fusion and direct 4-class output."""
    def __init__(self, group_dims: Dict[str, int], hidden_dim: int = 64, dropout: float = 0.15, num_classes: int = 4):
        super().__init__()
        self.active_groups = [g for g, d in group_dims.items() if d > 0]
        self.encoders = nn.ModuleDict({
            g: GroupEncoder(group_dims[g], hidden_dim, dropout=dropout)
            for g in self.active_groups
        })
        self.fusion = GatedResidualFusion(hidden_dim, len(self.active_groups), dropout=dropout)
        self.res1 = ResidualBlock(hidden_dim, dropout=dropout)
        self.res2 = ResidualBlock(hidden_dim, dropout=dropout)
        self.head = nn.Linear(hidden_dim, num_classes)

    def forward(self, batch: Dict[str, torch.Tensor]) -> Dict[str, torch.Tensor]:
        embs = [self.encoders[g](batch[f"{g}_feats"]) for g in self.active_groups]
        fused = self.fusion(embs)
        h = self.res2(self.res1(fused))
        return {"logits_4class": self.head(h)}

    def predict_probabilities(self, batch: Dict[str, torch.Tensor]) -> torch.Tensor:
        return F.softmax(self.forward(batch)["logits_4class"], dim=-1)

class ModelD_GroupedMultiTask(nn.Module):
    """MODEL D: Grouped MLP with concatenated fusion and Multi-Task heads."""
    def __init__(self, group_dims: Dict[str, int], hidden_dim: int = 64, dropout: float = 0.15, num_classes: int = 4):
        super().__init__()
        self.active_groups = [g for g, d in group_dims.items() if d > 0]
        self.encoders = nn.ModuleDict({
            g: GroupEncoder(group_dims[g], hidden_dim, dropout=dropout)
            for g in self.active_groups
        })
        self.proj = nn.Sequential(
            nn.Linear(len(self.active_groups) * hidden_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout)
        )
        self.res1 = ResidualBlock(hidden_dim, dropout=dropout)
        self.res2 = ResidualBlock(hidden_dim, dropout=dropout)
        self.classifier_head = nn.Linear(hidden_dim, num_classes)
        self.binary_head = nn.Linear(hidden_dim, 2)
        self.subclass_head = nn.Linear(hidden_dim, 3)

    def forward(self, batch: Dict[str, torch.Tensor]) -> Dict[str, torch.Tensor]:
        embs = [self.encoders[g](batch[f"{g}_feats"]) for g in self.active_groups]
        concat = torch.cat(embs, dim=-1)
        h = self.res2(self.res1(self.proj(concat)))
        return {
            "logits_4class": self.classifier_head(h),
            "logits_binary": self.binary_head(h),
            "logits_subclass": self.subclass_head(h)
        }

    def predict_probabilities(self, batch: Dict[str, torch.Tensor]) -> torch.Tensor:
        out = self.forward(batch)
        p_dir = F.softmax(out["logits_4class"], dim=-1)
        p_bin = F.softmax(out["logits_binary"], dim=-1)
        p_sub = F.softmax(out["logits_subclass"], dim=-1)
        p_hier = torch.zeros_like(p_dir)
        p_hier[:, 0] = p_bin[:, 0] * p_sub[:, 0]
        p_hier[:, 1] = p_bin[:, 0] * p_sub[:, 1]
        p_hier[:, 2] = p_bin[:, 0] * p_sub[:, 2]
        p_hier[:, 3] = p_bin[:, 1]
        return 0.5 * p_dir + 0.5 * p_hier

class ModelE_Stage832Full(nn.Module):
    """MODEL E: Stage 8.32 Architecture (Grouped + Gated Residual Fusion + Multi-Task)."""
    def __init__(self, group_dims: Dict[str, int], hidden_dim: int = 64, dropout: float = 0.15, num_classes: int = 4):
        super().__init__()
        self.active_groups = [g for g, d in group_dims.items() if d > 0]
        self.encoders = nn.ModuleDict({
            g: GroupEncoder(group_dims[g], hidden_dim, dropout=dropout)
            for g in self.active_groups
        })
        self.fusion = GatedResidualFusion(hidden_dim, len(self.active_groups), dropout=dropout)
        self.res1 = ResidualBlock(hidden_dim, dropout=dropout)
        self.res2 = ResidualBlock(hidden_dim, dropout=dropout)
        self.classifier_head = nn.Linear(hidden_dim, num_classes)
        self.binary_head = nn.Linear(hidden_dim, 2)
        self.subclass_head = nn.Linear(hidden_dim, 3)

    def forward(self, batch: Dict[str, torch.Tensor]) -> Dict[str, torch.Tensor]:
        embs = [self.encoders[g](batch[f"{g}_feats"]) for g in self.active_groups]
        fused = self.fusion(embs)
        h = self.res2(self.res1(fused))
        return {
            "logits_4class": self.classifier_head(h),
            "logits_binary": self.binary_head(h),
            "logits_subclass": self.subclass_head(h)
        }

    def predict_probabilities(self, batch: Dict[str, torch.Tensor]) -> torch.Tensor:
        out = self.forward(batch)
        p_dir = F.softmax(out["logits_4class"], dim=-1)
        p_bin = F.softmax(out["logits_binary"], dim=-1)
        p_sub = F.softmax(out["logits_subclass"], dim=-1)
        p_hier = torch.zeros_like(p_dir)
        p_hier[:, 0] = p_bin[:, 0] * p_sub[:, 0]
        p_hier[:, 1] = p_bin[:, 0] * p_sub[:, 1]
        p_hier[:, 2] = p_bin[:, 0] * p_sub[:, 2]
        p_hier[:, 3] = p_bin[:, 1]
        return 0.5 * p_dir + 0.5 * p_hier

class ModelF_GroupedTCN(nn.Module):
    """MODEL F: Grouped MLP + Causal 1D TCN for historical FIRMS sequences."""
    def __init__(self, group_dims: Dict[str, int], hidden_dim: int = 64, dropout: float = 0.15, num_classes: int = 4):
        super().__init__()
        self.active_groups = [g for g, d in group_dims.items() if d > 0]
        self.encoders = nn.ModuleDict({
            g: GroupEncoder(group_dims[g], hidden_dim, dropout=dropout)
            for g in self.active_groups
        })
        self.tcn = CausalTCNEncoder(in_features=11, hidden_dim=hidden_dim, dropout=dropout)
        total_groups = len(self.active_groups) + 1
        self.proj = nn.Sequential(
            nn.Linear(total_groups * hidden_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout)
        )
        self.res1 = ResidualBlock(hidden_dim, dropout=dropout)
        self.res2 = ResidualBlock(hidden_dim, dropout=dropout)
        self.head = nn.Linear(hidden_dim, num_classes)

    def forward(self, batch: Dict[str, torch.Tensor]) -> Dict[str, torch.Tensor]:
        embs = [self.encoders[g](batch[f"{g}_feats"]) for g in self.active_groups]
        tcn_emb = self.tcn(batch["seq_tensor"], batch["seq_mask"])
        embs.append(tcn_emb)
        concat = torch.cat(embs, dim=-1)
        h = self.res2(self.res1(self.proj(concat)))
        return {"logits_4class": self.head(h), "tcn_emb": tcn_emb}

    def predict_probabilities(self, batch: Dict[str, torch.Tensor]) -> torch.Tensor:
        return F.softmax(self.forward(batch)["logits_4class"], dim=-1)

class ModelG_BestSimplified(nn.Module):
    """
    MODEL G: Best Simplified Robust Architecture.
    Combines:
    1. Grouped physical encoders (Thermal, Historical, Industrial, Ecoregion) WITHOUT raw Lat/Lon.
    2. Dedicated Persistence Branch directly from historical features to resolve persistent flares.
    3. Multitask acute discrimination (Forest vs Agricultural vs Industrial).
    4. Clean concated residual fusion without overparameterized gating.
    """
    def __init__(self, group_dims: Dict[str, int], hidden_dim: int = 64, dropout: float = 0.15, num_classes: int = 4):
        super().__init__()
        self.active_groups = [g for g, d in group_dims.items() if d > 0 and g != "geographic"]
        self.encoders = nn.ModuleDict({
            g: GroupEncoder(group_dims[g], hidden_dim, dropout=dropout)
            for g in self.active_groups
        })
        # Dedicated persistence module
        hist_dim = group_dims.get("historical", 104)
        self.persistence_branch = DedicatedPersistenceBranch(hist_dim, hidden_dim=hidden_dim, dropout=dropout)

        total_dim = len(self.active_groups) * hidden_dim + (hidden_dim // 2)
        self.proj = nn.Sequential(
            nn.Linear(total_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout)
        )
        self.res1 = ResidualBlock(hidden_dim, dropout=dropout)
        self.res2 = ResidualBlock(hidden_dim, dropout=dropout)
        
        self.classifier_head = nn.Linear(hidden_dim, num_classes)
        self.subclass_head = nn.Linear(hidden_dim, 3)  # Acute: Ind (0), For (1), Agr (2)

    def forward(self, batch: Dict[str, torch.Tensor]) -> Dict[str, torch.Tensor]:
        embs = [self.encoders[g](batch[f"{g}_feats"]) for g in self.active_groups]
        per_emb, logits_binary = self.persistence_branch(batch["historical_feats"])
        embs.append(per_emb)

        concat = torch.cat(embs, dim=-1)
        h = self.res2(self.res1(self.proj(concat)))
        logits_4class = self.classifier_head(h)
        logits_subclass = self.subclass_head(h)

        return {
            "logits_4class": logits_4class,
            "logits_binary": logits_binary,
            "logits_subclass": logits_subclass
        }

    def predict_probabilities(self, batch: Dict[str, torch.Tensor]) -> torch.Tensor:
        out = self.forward(batch)
        p_dir = F.softmax(out["logits_4class"], dim=-1)
        p_bin = F.softmax(out["logits_binary"], dim=-1)
        p_sub = F.softmax(out["logits_subclass"], dim=-1)
        
        p_hier = torch.zeros_like(p_dir)
        p_hier[:, 0] = p_bin[:, 0] * p_sub[:, 0]  # Industrial
        p_hier[:, 1] = p_bin[:, 0] * p_sub[:, 1]  # Forest
        p_hier[:, 2] = p_bin[:, 0] * p_sub[:, 2]  # Agricultural
        p_hier[:, 3] = p_bin[:, 1]                # Persistent
        return 0.5 * p_dir + 0.5 * p_hier

# =====================================================================
# 5. Loss Functions
# =====================================================================

class FocalLoss(nn.Module):
    """Multi-class Focal Loss with class weights and focusing parameter gamma."""
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

class HierarchicalLoss(nn.Module):
    """
    Hierarchical Classification Loss:
    Level 1: Binary (Acute vs Persistent)
    Level 2: 3-class Acute (Industrial vs Forest vs Agricultural)
    """
    def __init__(self, weight_bin: float = 1.0, weight_sub: float = 1.0):
        super().__init__()
        self.weight_bin = weight_bin
        self.weight_sub = weight_sub
        self.ce = nn.CrossEntropyLoss()

    def forward(self, logits_bin: torch.Tensor, logits_sub: torch.Tensor, class_ids: torch.Tensor) -> torch.Tensor:
        # Binary target: 1 if class_id == 3 else 0
        bin_targets = (class_ids == 3).long()
        loss_bin = self.ce(logits_bin, bin_targets)
        # Acute mask
        acute_mask = (class_ids < 3)
        if acute_mask.sum() > 0:
            loss_sub = self.ce(logits_sub[acute_mask], class_ids[acute_mask])
        else:
            loss_sub = torch.tensor(0.0, device=class_ids.device)
        return self.weight_bin * loss_bin + self.weight_sub * loss_sub
