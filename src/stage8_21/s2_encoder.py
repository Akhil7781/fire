"""
Stage 8.21 - Sentinel-2 5-Channel Visual Encoder
Implements lightweight deep-learning visual encoder adapted for 5 spectral channels:
Input: [B, 5, 512, 512] (Channels: B02, B03, B04, B11, B12)
Output: z_s2 in R^128

Principled 5-channel adaptation:
- Input channels: [B02 (Blue), B03 (Green), B04 (Red), B11 (SWIR-1), B12 (SWIR-2)]
- Stem adapts 3-channel pretrained convolutional weights:
    * Channel 0 (B02 Blue)  <- RGB Blue weight
    * Channel 1 (B03 Green) <- RGB Green weight
    * Channel 2 (B04 Red)   <- RGB Red weight
    * Channel 3 (B11 SWIR1) <- RGB Mean weight
    * Channel 4 (B12 SWIR2) <- RGB Mean weight
    * Scaled by 3/5 to preserve activation variance across input channels.
- Global Average Pooling -> Projection Head -> L2 Normalized 128D Embedding.
"""

from pathlib import Path
from typing import Optional, Tuple
import torch
import torch.nn as nn
import torch.nn.functional as F
import torchvision.models as models


class Sentinel2Encoder(nn.Module):
    """
    Lightweight 5-channel Sentinel-2 visual feature encoder producing 128D embeddings.
    """

    def __init__(
        self,
        embedding_dim: int = 128,
        backbone_name: str = "efficientnet_b0",
        pretrained: bool = True,
        dropout: float = 0.1,
    ):
        super().__init__()
        self.embedding_dim = embedding_dim
        self.backbone_name = backbone_name
        self.pretrained = pretrained

        # Load backbone
        if backbone_name == "efficientnet_b0":
            weights = models.EfficientNet_B0_Weights.DEFAULT if pretrained else None
            base_model = models.efficientnet_b0(weights=weights)
            
            # Original conv: Conv2d(3, 32, kernel_size=(3, 3), stride=(2, 2), padding=(1, 1), bias=False)
            old_conv = base_model.features[0][0]
            new_conv = nn.Conv2d(
                in_channels=5,
                out_channels=old_conv.out_channels,
                kernel_size=old_conv.kernel_size,
                stride=old_conv.stride,
                padding=old_conv.padding,
                bias=old_conv.bias is not None,
            )

            with torch.no_grad():
                # Principled 5-channel weight adaptation
                # Channel 0 (B02 Blue)  <- old RGB Blue (index 2)
                # Channel 1 (B03 Green) <- old RGB Green (index 1)
                # Channel 2 (B04 Red)   <- old RGB Red (index 0)
                # Channel 3 (B11 SWIR1) <- old RGB Mean
                # Channel 4 (B12 SWIR2) <- old RGB Mean
                scale_factor = 3.0 / 5.0
                new_conv.weight[:, 0:1, :, :] = old_conv.weight[:, 2:3, :, :] * scale_factor
                new_conv.weight[:, 1:2, :, :] = old_conv.weight[:, 1:2, :, :] * scale_factor
                new_conv.weight[:, 2:3, :, :] = old_conv.weight[:, 0:1, :, :] * scale_factor
                mean_rgb = old_conv.weight.mean(dim=1, keepdim=True)
                new_conv.weight[:, 3:4, :, :] = mean_rgb * scale_factor
                new_conv.weight[:, 4:5, :, :] = mean_rgb * scale_factor

            base_model.features[0][0] = new_conv
            self.features = base_model.features
            in_features = 1280

        elif backbone_name == "resnet18":
            weights = models.ResNet18_Weights.DEFAULT if pretrained else None
            base_model = models.resnet18(weights=weights)
            
            old_conv = base_model.conv1
            new_conv = nn.Conv2d(
                in_channels=5,
                out_channels=old_conv.out_channels,
                kernel_size=old_conv.kernel_size,
                stride=old_conv.stride,
                padding=old_conv.padding,
                bias=old_conv.bias is not None,
            )

            with torch.no_grad():
                scale_factor = 3.0 / 5.0
                new_conv.weight[:, 0:1, :, :] = old_conv.weight[:, 2:3, :, :] * scale_factor
                new_conv.weight[:, 1:2, :, :] = old_conv.weight[:, 1:2, :, :] * scale_factor
                new_conv.weight[:, 2:3, :, :] = old_conv.weight[:, 0:1, :, :] * scale_factor
                mean_rgb = old_conv.weight.mean(dim=1, keepdim=True)
                new_conv.weight[:, 3:4, :, :] = mean_rgb * scale_factor
                new_conv.weight[:, 4:5, :, :] = mean_rgb * scale_factor

            base_model.conv1 = new_conv
            self.features = nn.Sequential(
                base_model.conv1,
                base_model.bn1,
                base_model.relu,
                base_model.maxpool,
                base_model.layer1,
                base_model.layer2,
                base_model.layer3,
                base_model.layer4,
            )
            in_features = 512
        else:
            raise ValueError(f"Unsupported backbone: {backbone_name}")

        self.pool = nn.AdaptiveAvgPool2d((1, 1))

        # 2-layer projection head to 128D
        self.projector = nn.Sequential(
            nn.Linear(in_features, 256),
            nn.BatchNorm1d(256),
            nn.ReLU(inplace=True),
            nn.Dropout(p=dropout),
            nn.Linear(256, embedding_dim),
        )

    def forward_features(self, x: torch.Tensor) -> torch.Tensor:
        """Extracts pooled spatial features before projection head."""
        feat = self.features(x)
        pooled = self.pool(feat).flatten(1)
        return pooled

    def forward(self, x: torch.Tensor, normalize: bool = True) -> torch.Tensor:
        """
        Forward pass.
        Args:
            x: Input tensor of shape [B, 5, 512, 512] in range [0, 1].
            normalize: Whether to L2-normalize output embeddings.
        Returns:
            z: Embedding tensor of shape [B, 128].
        """
        if x.shape[1] != 5:
            raise ValueError(f"Expected 5 channels (B02, B03, B04, B11, B12), got {x.shape[1]}")

        pooled = self.forward_features(x)
        z = self.projector(pooled)
        if normalize:
            z = F.normalize(z, p=2, dim=1)
        return z

    def save_checkpoint(self, path: Path, extra_metadata: Optional[dict] = None):
        """Saves deterministic model checkpoint."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        checkpoint = {
            "model_state_dict": self.state_dict(),
            "embedding_dim": self.embedding_dim,
            "backbone_name": self.backbone_name,
            "metadata": extra_metadata or {},
        }
        torch.save(checkpoint, str(path))

    @classmethod
    def load_checkpoint(cls, path: Path) -> "Sentinel2Encoder":
        """Loads model from checkpoint."""
        checkpoint = torch.load(str(path), map_location="cpu")
        model = cls(
            embedding_dim=checkpoint["embedding_dim"],
            backbone_name=checkpoint["backbone_name"],
            pretrained=False,
        )
        model.load_state_dict(checkpoint["model_state_dict"])
        model.eval()
        return model
