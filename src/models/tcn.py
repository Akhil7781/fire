"""
1D Dilated Causal Temporal Convolutional Network (TCN).

Architectural Invariants strictly enforced per FINAL_TRAINING_DATA_ARCHITECTURE_v2.md §3.2:
  1. 1D Causal Convolution: Output at timestep t depends strictly on historical timesteps <= t.
     Causal padding of (kernel_size - 1) * dilation on the left only; zero right padding.
  2. Input shape: (Batch, Timesteps=16, Channels=8).
  3. Receptive field: Dilations d in {1, 2, 4, 8, 16} with kernel_size k=3. With two CausalConv1d
     layers per residual block, RF = 1 + 2 * (k - 1) * sum(dilations) = 1 + 4 * 31 = 125 >= 16
     timesteps (or 1 + (k - 1) * sum(dilations) = 63 per stage), fully covering sequence causally.
  4. Residual connections: CausalConv1d + ReLU + Dropout(0.2) with 1x1 conv residual projection.
  5. Latent representation: Masked active pooling projected to z_TCN in R^64.
  6. Reconstruction heads: Multi-layer perceptrons predicting FRP (MW) and Thermal Contrast Delta-T (K).
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple, Union

import torch
import torch.nn as nn
import torch.nn.functional as F


class CausalConv1d(nn.Module):
    """
    1D Causal Convolution with left-only padding.
    Ensures that output at timestep t depends strictly on inputs at timesteps <= t.
    """

    def __init__(
        self,
        in_channels: int,
        out_channels: int,
        kernel_size: int = 3,
        dilation: int = 1,
    ):
        super().__init__()
        self.kernel_size = kernel_size
        self.dilation = dilation
        self.causal_pad = (kernel_size - 1) * dilation

        conv = nn.Conv1d(
            in_channels,
            out_channels,
            kernel_size=kernel_size,
            dilation=dilation,
            padding=0,
            bias=True,
        )
        self.conv = nn.utils.parametrizations.weight_norm(conv)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: Input tensor of shape (B, C, T)
        Returns:
            Output tensor of shape (B, C_out, T) with causal temporal alignment.
        """
        # Pad left by causal_pad, pad right by 0
        x_padded = F.pad(x, (self.causal_pad, 0))
        return self.conv(x_padded)


class TemporalBlock(nn.Module):
    """
    Residual dilated causal block with two CausalConv1d layers,
    ReLU activations, and Dropout.
    """

    def __init__(
        self,
        in_channels: int,
        out_channels: int,
        kernel_size: int = 3,
        dilation: int = 1,
        dropout: float = 0.2,
    ):
        super().__init__()
        self.conv1 = CausalConv1d(in_channels, out_channels, kernel_size, dilation)
        self.relu1 = nn.ReLU()
        self.drop1 = nn.Dropout(dropout)

        self.conv2 = CausalConv1d(out_channels, out_channels, kernel_size, dilation)
        self.relu2 = nn.ReLU()
        self.drop2 = nn.Dropout(dropout)

        self.residual = (
            nn.Conv1d(in_channels, out_channels, kernel_size=1)
            if in_channels != out_channels
            else nn.Identity()
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        res = self.residual(x)
        out = self.drop1(self.relu1(self.conv1(x)))
        out = self.drop2(self.relu2(self.conv2(out)))
        return out + res


class TemporalConvolutionalNetwork(nn.Module):
    """
    1D Dilated Causal TCN for self-supervised sequence pretraining and representation learning.
    Input: (B, T=16, C=8)
    Latent embedding: z_TCN in R^64
    Reconstruction targets: FRP (channel 3) and thermal_contrast_k (channel 2).
    """

    CHANNEL_NAMES: List[str] = [
        "elapsed_time_hours",      # 0
        "geodesic_distance_km",    # 1
        "thermal_contrast_k",      # 2 (reconstruction target)
        "frp_mw",                  # 3 (reconstruction target)
        "log1p_frp",               # 4
        "pixel_footprint_km2",     # 5
        "solar_zenith_deg",        # 6
        "daynight_flag",           # 7
    ]

    def __init__(
        self,
        in_channels: int = 8,
        hidden_channels: int = 64,
        dilations: Tuple[int, ...] = (1, 2, 4, 8, 16),
        latent_dim: int = 64,
        dropout: float = 0.2,
    ):
        super().__init__()
        self.in_channels = in_channels
        self.hidden_channels = hidden_channels
        self.dilations = dilations
        self.latent_dim = latent_dim
        self.dropout = dropout

        # Causal dilated temporal blocks
        layers = []
        c_in = in_channels
        for d in dilations:
            layers.append(
                TemporalBlock(
                    in_channels=c_in,
                    out_channels=hidden_channels,
                    kernel_size=3,
                    dilation=d,
                    dropout=dropout,
                )
            )
            c_in = hidden_channels
        self.network = nn.Sequential(*layers)

        # Latent projection: projects temporal features to z_TCN in R^64
        self.latent_proj = nn.Linear(hidden_channels, latent_dim)
        self.latent_norm = nn.LayerNorm(latent_dim)

        # Reconstruction heads for self-supervised pretraining
        # Predict normalized values of FRP and thermal contrast Delta-T
        self.frp_head = nn.Sequential(
            nn.Linear(hidden_channels, 32),
            nn.ReLU(),
            nn.Linear(32, 1),
        )
        self.thermal_contrast_head = nn.Sequential(
            nn.Linear(hidden_channels, 32),
            nn.ReLU(),
            nn.Linear(32, 1),
        )

    def extract_features(
        self,
        x: torch.Tensor,
        padding_mask: Optional[torch.Tensor] = None,
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Passes input sequence through dilated causal network.
        Args:
            x: (B, T=16, C=8) input tensor
            padding_mask: (B, T=16) boolean tensor (True for active, False for padding)
        Returns:
            h: (B, hidden_channels, T=16) per-timestep causal representation
            z_tcn: (B, latent_dim=64) normalized latent representation
        """
        # Transpose from (B, T, C) to (B, C, T) for 1D convolution
        x_t = x.transpose(1, 2)
        h = self.network(x_t)  # (B, hidden_channels, T)

        # Compute z_TCN via active-aware global pooling
        if padding_mask is not None:
            # Expand mask to (B, 1, T)
            mask_exp = padding_mask.unsqueeze(1).float()
            h_active = h * mask_exp
            h_pooled = h_active.sum(dim=2) / mask_exp.sum(dim=2).clamp(min=1.0)
        else:
            h_pooled = h.mean(dim=2)

        z_tcn = self.latent_norm(self.latent_proj(h_pooled))
        return h, z_tcn

    def encode(
        self,
        x: torch.Tensor,
        padding_mask: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        """
        Extracts 64-D latent temporal embedding z_TCN.
        Args:
            x: (B, T=16, C=8) input sequence
            padding_mask: (B, T=16) boolean active mask
        Returns:
            z_tcn: (B, 64) normalized latent temporal representation
        """
        _, z_tcn = self.extract_features(x, padding_mask)
        return z_tcn

    def forward(
        self,
        x: torch.Tensor,
        padding_mask: Optional[torch.Tensor] = None,
    ) -> Dict[str, torch.Tensor]:
        """
        Forward pass for self-supervised pretraining.
        Args:
            x: (B, T=16, C=8) input sequence (may have masked active timesteps)
            padding_mask: (B, T=16) boolean mask (True for active, False for padding)
        Returns:
            Dictionary with:
              - 'frp_pred': (B, T=16) predicted FRP values
              - 'thermal_contrast_pred': (B, T=16) predicted thermal contrast Delta-T
              - 'z_tcn': (B, 64) latent temporal embedding
              - 'hidden': (B, hidden_channels, 16) hidden state
        """
        h, z_tcn = self.extract_features(x, padding_mask)

        # Transpose to (B, T, hidden_channels) for per-timestep prediction heads
        h_steps = h.transpose(1, 2)
        frp_pred = self.frp_head(h_steps).squeeze(-1)                  # (B, T)
        dt_pred = self.thermal_contrast_head(h_steps).squeeze(-1)      # (B, T)

        return {
            "frp_pred": frp_pred,
            "thermal_contrast_pred": dt_pred,
            "z_tcn": z_tcn,
            "hidden": h,
        }
