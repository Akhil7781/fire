"""
Deep Semi-Supervised Anomaly Detection (Deep SAD) Architecture.

Authoritative Specification:
  - FINAL_TRAINING_DATA_ARCHITECTURE_v2.md §3.5
  - PROJECT_SPEC.md §8
  - Input: 27 Causal Tabular Features (D_in = 27)
  - Latent Representation: z_SAD in R^32
  - Scalar Anomaly Score: s(x) = ||phi(x; W) - c||^2
  - Linear(27, 128, bias=False) -> LeakyReLU(0.1) ->
    Linear(128, 64, bias=False) -> LeakyReLU(0.1) ->
    Linear(64, 32, bias=False)
  - Trainable parameters: 13,696
  - Fixed center c in R^32, initialized from unlabeled train data, ||c|| >= 0.10.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple, Union

import torch
import torch.nn as nn
import torch.nn.functional as F


class DeepSAD(nn.Module):
    """
    Deep Semi-Supervised Anomaly Detection network for 1D tabular satellite observations.
    Maps 27 causal features to a 32-dimensional latent anomaly space.
    """

    FEATURE_NAMES: List[str] = [
        "bright_ti4",
        "bright_ti5",
        "frp",
        "pixel_area",
        "scan",
        "track",
        "delta_t_robust_scaled",
        "temp_ratio_robust_scaled",
        "frp_density_robust_scaled",
        "frp_log1p_robust_scaled",
        "time_since_last_det_2km_robust_scaled",
        "spatial_dispersion_24h_2km_robust_scaled",
        "sin_diurnal",
        "cos_diurnal",
        "sin_lst",
        "cos_lst",
        "sin_annual",
        "cos_annual",
        "hist_count_6h_2km",
        "hist_count_24h_2km",
        "has_prior_24h_2km",
        "mean_frp_6h_2km",
        "max_frp_6h_2km",
        "mean_frp_24h_2km",
        "max_frp_24h_2km",
        "day_ratio_24h_2km",
        "daynight_binary",
    ]

    def __init__(
        self,
        in_features: int = 27,
        latent_dim: int = 32,
        leaky_relu_slope: float = 0.1,
    ):
        super().__init__()
        self.in_features = in_features
        self.latent_dim = latent_dim
        self.leaky_relu_slope = leaky_relu_slope

        # 3-Layer MLP with zero bias to prevent representation collapse
        self.network = nn.Sequential(
            nn.Linear(in_features, 128, bias=False),
            nn.LeakyReLU(leaky_relu_slope),
            nn.Linear(128, 64, bias=False),
            nn.LeakyReLU(leaky_relu_slope),
            nn.Linear(64, latent_dim, bias=False),
        )

        # Persistent non-trainable center buffer c in R^32
        self.register_buffer("c", torch.zeros(latent_dim, dtype=torch.float32))
        self.is_center_initialized: bool = False

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Passes input through Deep SAD network to compute latent representation z_SAD.
        Args:
            x: (B, 27) input tensor of causal features
        Returns:
            z_sad: (B, 32) latent anomaly representation
        """
        return self.network(x)

    def compute_anomaly_score(self, x: torch.Tensor) -> torch.Tensor:
        """
        Computes scalar anomaly score s(x) = ||phi(x) - c||^2.
        Args:
            x: (B, 27) input tensor
        Returns:
            scores: (B,) squared Euclidean distance from center c
        """
        assert self.is_center_initialized, "Center c must be initialized before computing anomaly scores."
        z = self.network(x)  # (B, 32)
        diff = z - self.c.unsqueeze(0)  # (B, 32)
        return torch.sum(diff ** 2, dim=-1)  # (B,)

    def init_center(
        self,
        x_init: torch.Tensor,
        eps_norm: float = 0.10,
    ) -> torch.Tensor:
        """
        Initializes hypersphere center c from a forward pass over unlabeled training samples.
        The center vector is fixed and registered as a non-trainable persistent buffer.
        Args:
            x_init: (N_init, 27) active training samples from unlabeled pool
            eps_norm: minimum required norm ||c|| >= eps_norm (default 0.10)
        Returns:
            c: (32,) initialized center vector
        """
        self.eval()
        with torch.no_grad():
            z_init = self.network(x_init)
            c = torch.mean(z_init, dim=0)

            c_norm = torch.norm(c).item()
            if c_norm < eps_norm:
                # If too close to origin, shift coordinates outward to avoid collapse
                shift = torch.ones_like(c) * (eps_norm / (c.numel() ** 0.5))
                c = c + shift

        self.c.copy_(c)
        self.is_center_initialized = True
        return self.c.clone()
