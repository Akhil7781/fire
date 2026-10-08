"""Stage 8.36 Final Model Definition.

Pure PyTorch implementation of Architecture1_StaticMLP.
Immutable frozen architecture for Stage 8.36 terminal evaluation.
"""

from typing import Dict, Any
import torch
import torch.nn as nn
import torch.nn.functional as F

class Architecture1_StaticMLP(nn.Module):
    """Concise 2-layer MLP on concatenated clean causal features."""
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
