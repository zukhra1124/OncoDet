"""
Professional loss functions for medical image classification.
Includes Focal Loss for handling class imbalance effectively.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


class FocalLoss(nn.Module):
    """
    Focal Loss for addressing class imbalance.
    Reference: "Focal Loss for Dense Object Detection" (Lin et al., 2017)
    
    Reduces weight of easy examples and focuses on hard negative examples.
    Particularly effective for binary classification with imbalanced datasets.
    
    Args:
        alpha (float or list): Weighting factor in [0, 1] to balance
            positive/negative examples. Can be a list [alpha_0, alpha_1] for binary.
        gamma (float): Exponent of the modulating factor (1 - p_t)^gamma.
                      Higher gamma = more focus on hard examples.
        reduction (str): 'mean', 'sum', or 'none'
    """
    
    def __init__(self, alpha=None, gamma=2.0, reduction='mean'):
        super(FocalLoss, self).__init__()
        self.alpha = alpha
        self.gamma = gamma
        self.reduction = reduction
    
    def forward(self, inputs, targets):
        """
        Args:
            inputs: (N, C) logits from model
            targets: (N,) class indices (0 or 1)
        
        Returns:
            Loss scalar or per-sample losses
        """
        # Get cross entropy loss (no reduction yet)
        ce_loss = F.cross_entropy(inputs, targets, reduction='none')
        
        # Get probabilities
        p = torch.exp(-ce_loss)
        
        # Apply focal term: (1 - p_t)^gamma
        focal_loss = (1 - p) ** self.gamma * ce_loss
        
        # Apply alpha weighting if provided
        if self.alpha is not None:
            if isinstance(self.alpha, (list, tuple)):
                # Per-class alpha
                alpha_t = torch.tensor(
                    [self.alpha[t] for t in targets.cpu().tolist()],
                    device=targets.device,
                    dtype=torch.float32
                )
            else:
                # Single alpha for binary case
                alpha_t = torch.where(
                    targets == 1,
                    torch.tensor(self.alpha, dtype=torch.float32, device=targets.device),
                    torch.tensor(1.0 - self.alpha, dtype=torch.float32, device=targets.device)
                )
            focal_loss = alpha_t * focal_loss
        
        # Apply reduction
        if self.reduction == 'mean':
            return focal_loss.mean()
        elif self.reduction == 'sum':
            return focal_loss.sum()
        else:
            return focal_loss


class WeightedFocalLoss(nn.Module):
    """
    Weighted Focal Loss combining class weights and focal loss.
    Best for imbalanced medical imaging tasks.
    """
    
    def __init__(self, class_weights, gamma=2.0, reduction='mean'):
        super(WeightedFocalLoss, self).__init__()
        self.class_weights = class_weights
        self.gamma = gamma
        self.reduction = reduction
        self.focal_loss = FocalLoss(alpha=0.25, gamma=gamma, reduction='none')
    
    def forward(self, inputs, targets):
        # Compute focal loss
        focal = self.focal_loss(inputs, targets)
        
        # Apply class weights
        weights = torch.tensor(
            [self.class_weights[t] for t in targets.cpu().tolist()],
            device=targets.device,
            dtype=torch.float32
        )
        weighted_focal = weights * focal
        
        # Apply reduction
        if self.reduction == 'mean':
            return weighted_focal.mean()
        elif self.reduction == 'sum':
            return weighted_focal.sum()
        else:
            return weighted_focal
