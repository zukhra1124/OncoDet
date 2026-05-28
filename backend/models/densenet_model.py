"""
DenseNet121 wrapper for binary lung cancer / normal classification.
We use transfer learning — freeze the pretrained backbone and only
train a new classifier head on top.
"""

import torch
import torch.nn as nn
from torchvision import models


# Alias kept for backward-compat with saved checkpoints
PneumoniaNet = None   # defined below


class OncologyNet(nn.Module):
    """
    Binary classifier (NORMAL vs CANCER) built on top of DenseNet121.
    The feature layers stay frozen (ImageNet weights), and we swap
    the final layer for our own 2-class head.
    """

    def __init__(self, num_classes=2, pretrained=True):  # noqa
        super(PneumoniaNet, self).__init__()

        # load the pretrained DenseNet backbone
        self.densenet = models.densenet121(
            weights=models.DenseNet121_Weights.IMAGENET1K_V1 if pretrained else None
        )

        # freeze everything except the classifier
        for param in self.densenet.features.parameters():
            param.requires_grad = False

        # replace the default classifier with our own
        num_features = self.densenet.classifier.in_features
        self.densenet.classifier = nn.Sequential(
            nn.Dropout(p=0.3),
            nn.Linear(num_features, 512),
            nn.ReLU(inplace=True),
            nn.Dropout(p=0.2),
            nn.Linear(512, num_classes)
        )

    def forward(self, x):
        return self.densenet(x)

    def get_features_module(self):
        """Needed by Grad-CAM to hook into the feature extractor."""
        return self.densenet.features

    def get_last_conv_layer(self):
        """Returns denseblock4 — the layer Grad-CAM attaches to."""
        return self.densenet.features.denseblock4


# backward-compatibility alias
PneumoniaNet = OncologyNet
