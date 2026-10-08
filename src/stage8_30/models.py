"""
Stage 8.30 Registry-Free Causal Neural Architectures.

Includes:
1. HistoricalThermalRecurrenceEncoder:
   - 2-layer UNIDIRECTIONAL GRU (bidirectional is FORBIDDEN).
   - Masked attention pooling over variable-length sequence.
   - Strictly respects chronological order.
   - Outputs 64-dimensional historical embedding.
2. CurrentThermalEncoder:
   - Compact MLP/GRU for current causal observations (<= t0 + H).
   - Outputs 64-dimensional current-alert embedding.
3. RegistryFreeCausalClassifier:
   - Hierarchical fusion of Historical (64D) + Current (64D) + Geo/Context + Multi-Scale History.
   - 128D latent representation.
   - Acute vs Persistent binary head (auxiliary diagnostic).
   - Acute subclass head (Industrial, Forest, Agricultural).
   - Final 4-class head.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F

class HistoricalThermalRecurrenceEncoder(nn.Module):
    def __init__(self, in_features: int = 11, hidden_dim: int = 64, num_layers: int = 2, dropout: float = 0.1):
        super().__init__()
        self.in_features = in_features
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers

        # Input feature projection
        self.input_proj = nn.Sequential(
            nn.Linear(in_features, hidden_dim),
            nn.GELU(),
            nn.LayerNorm(hidden_dim)
        )

        # Strictly 2-layer UNIDIRECTIONAL GRU (bidirectional is FORBIDDEN)
        self.gru = nn.GRU(
            input_size=hidden_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            bidirectional=False,
            dropout=dropout if num_layers > 1 else 0.0
        )

        # Attention pooling head
        self.attn_net = nn.Sequential(
            nn.Linear(hidden_dim, 32),
            nn.Tanh(),
            nn.Linear(32, 1)
        )

        self.out_norm = nn.LayerNorm(hidden_dim)

    def forward(self, x: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: Tensor of shape (B, L, in_features)
            mask: BoolTensor of shape (B, L), True where valid, False where padded.
        Returns:
            embedding: Tensor of shape (B, 64)
        """
        B, L, _ = x.shape
        if L == 0 or not mask.any():
            return torch.zeros(B, self.hidden_dim, device=x.device, dtype=x.dtype)

        proj = self.input_proj(x) # (B, L, hidden_dim)
        gru_out, _ = self.gru(proj) # (B, L, hidden_dim)

        # Masked attention pooling
        scores = self.attn_net(gru_out).squeeze(-1) # (B, L)
        scores = scores.masked_fill(~mask, -1e9)
        attn_weights = F.softmax(scores, dim=-1).unsqueeze(-1) # (B, L, 1)

        # Handle rows where entire sequence is padded/empty
        has_any = mask.any(dim=-1, keepdim=True) # (B, 1)
        attn_weights = torch.where(has_any.unsqueeze(-1), attn_weights, torch.zeros_like(attn_weights))

        pooled = torch.sum(gru_out * attn_weights, dim=1) # (B, hidden_dim)
        pooled = torch.where(has_any, self.out_norm(pooled), torch.zeros_like(pooled))

        return pooled

class CurrentThermalEncoder(nn.Module):
    def __init__(self, in_features: int = 14, hidden_dim: int = 64):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(in_features, hidden_dim),
            nn.GELU(),
            nn.LayerNorm(hidden_dim),
            nn.Linear(hidden_dim, hidden_dim),
            nn.GELU(),
            nn.LayerNorm(hidden_dim)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)

class RegistryFreeCausalClassifier(nn.Module):
    def __init__(
        self,
        hist_seq_dim: int = 11,
        curr_dim: int = 14,
        geo_dim: int = 11,
        hist_summary_dim: int = 96,
        latent_dim: int = 128,
        num_classes: int = 4,
        dropout: float = 0.15
    ):
        super().__init__()
        self.hist_encoder = HistoricalThermalRecurrenceEncoder(in_features=hist_seq_dim, hidden_dim=64)
        self.curr_encoder = CurrentThermalEncoder(in_features=curr_dim, hidden_dim=64)

        # Context & multi-scale summary projection
        context_in_dim = geo_dim + hist_summary_dim
        self.context_proj = nn.Sequential(
            nn.Linear(context_in_dim, 64),
            nn.GELU(),
            nn.LayerNorm(64)
        )

        # Multimodal fusion: 64 (hist) + 64 (curr) + 64 (context) = 192D
        fusion_in_dim = 64 + 64 + 64
        self.fusion = nn.Sequential(
            nn.Linear(fusion_in_dim, latent_dim),
            nn.GELU(),
            nn.LayerNorm(latent_dim),
            nn.Dropout(dropout)
        )

        # Heads
        # 1. Auxiliary Acute vs Persistent binary head (0 = Acute [0,1,2], 1 = Persistent [3])
        self.binary_head = nn.Linear(latent_dim, 2)

        # 2. Auxiliary Acute subclass head (0 = Industrial, 1 = Forest, 2 = Agricultural)
        self.subclass_head = nn.Linear(latent_dim, 3)

        # 3. Final 4-class head (0 = Ind, 1 = For, 2 = Agr, 3 = Per)
        self.classifier_head = nn.Linear(latent_dim, num_classes)

    def forward(
        self,
        hist_seq: torch.Tensor,
        hist_mask: torch.Tensor,
        curr_feats: torch.Tensor,
        geo_feats: torch.Tensor,
        hist_summary_feats: torch.Tensor
    ):
        hist_emb = self.hist_encoder(hist_seq, hist_mask) # (B, 64)
        curr_emb = self.curr_encoder(curr_feats)           # (B, 64)

        context_all = torch.cat([geo_feats, hist_summary_feats], dim=-1)
        context_emb = self.context_proj(context_all)       # (B, 64)

        fused_in = torch.cat([hist_emb, curr_emb, context_emb], dim=-1) # (B, 192)
        latent = self.fusion(fused_in)                     # (B, 128)

        logits_4class = self.classifier_head(latent)       # (B, 4)
        logits_binary = self.binary_head(latent)           # (B, 2)
        logits_subclass = self.subclass_head(latent)       # (B, 3)

        return {
            "logits_4class": logits_4class,
            "logits_binary": logits_binary,
            "logits_subclass": logits_subclass,
            "latent": latent,
            "hist_emb": hist_emb,
            "curr_emb": curr_emb
        }

def compute_hierarchical_probabilities(logits_4class: torch.Tensor, logits_binary: torch.Tensor, logits_subclass: torch.Tensor) -> torch.Tensor:
    """
    Computes hierarchical probabilities combining Acute vs Persistent with Acute subclasses:
    P(class 3) = P(persistent)
    P(class c) = P(acute) * P(subclass c | acute) for c in {0, 1, 2}.
    Also blends with direct 4-class softmax.
    """
    p_direct = F.softmax(logits_4class, dim=-1)

    p_bin = F.softmax(logits_binary, dim=-1) # [p_acute, p_persistent]
    p_sub = F.softmax(logits_subclass, dim=-1) # [p_ind, p_for, p_agr]

    p_hier = torch.zeros_like(p_direct)
    p_hier[:, 0] = p_bin[:, 0] * p_sub[:, 0]
    p_hier[:, 1] = p_bin[:, 0] * p_sub[:, 1]
    p_hier[:, 2] = p_bin[:, 0] * p_sub[:, 2]
    p_hier[:, 3] = p_bin[:, 1]

    # Weighted ensemble: 0.5 * direct + 0.5 * hierarchical
    p_final = 0.5 * p_direct + 0.5 * p_hier
    return p_final
