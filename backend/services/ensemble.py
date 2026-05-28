"""
Ensemble prediction utilities for robust medical image classification.
Combines multiple models or augmentations for more reliable diagnostics.
"""

import torch
import torch.nn.functional as F
import numpy as np
from torchvision import transforms
from PIL import Image

from models.model_loader import get_model, get_device


class EnsemblePredictor:
    """
    Ensemble multiple predictions for robustness.
    
    Methods:
    1. Horizontal flip ensemble - same model, flipped input
    2. Augmentation ensemble - same model, different augmentations  
    3. Multi-model ensemble - different architectures (if available)
    """
    
    def __init__(self, temperature=1.4):
        self.device = get_device()
        self.model = get_model()
        self.temperature = temperature
    
    def get_augmentation_transforms(self):
        """Get diverse augmentations for ensemble."""
        return [
            # Original (no augmentation)
            transforms.Compose([
                transforms.Resize((224, 224)),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                   std=[0.229, 0.224, 0.225])
            ]),
            # Horizontal flip
            transforms.Compose([
                transforms.Resize((224, 224)),
                transforms.RandomHorizontalFlip(p=1.0),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                   std=[0.229, 0.224, 0.225])
            ]),
            # Rotation
            transforms.Compose([
                transforms.Resize((224, 224)),
                transforms.RandomRotation(10),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                   std=[0.229, 0.224, 0.225])
            ]),
            # Brightness/contrast
            transforms.Compose([
                transforms.Resize((224, 224)),
                transforms.ColorJitter(brightness=0.2, contrast=0.2),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                   std=[0.229, 0.224, 0.225])
            ]),
            # Slight crop
            transforms.Compose([
                transforms.Resize((240, 240)),
                transforms.CenterCrop((224, 224)),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                   std=[0.229, 0.224, 0.225])
            ])
        ]
    
    def predict_tta(self, pil_image, num_augmentations=5):
        """
        Test-Time Augmentation (TTA) prediction.
        
        Args:
            pil_image: PIL Image object
            num_augmentations: number of augmented versions to test
        
        Returns:
            dict with ensemble predictions and confidence
        """
        augmentations = self.get_augmentation_transforms()
        
        all_probs = []
        self.model.eval()
        
        with torch.no_grad():
            for i in range(min(num_augmentations, len(augmentations))):
                # Apply augmentation
                img_aug = augmentations[i](pil_image)
                img_aug = img_aug.unsqueeze(0).to(self.device)
                
                # Predict
                output = self.model(img_aug)
                output = output / self.temperature  # Temperature scaling
                probs = F.softmax(output, dim=1)
                all_probs.append(probs.cpu())
        
        # Average probabilities across augmentations
        ensemble_probs = torch.stack(all_probs).mean(dim=0)[0]
        confidence, pred_idx = torch.max(ensemble_probs, dim=0)
        
        return {
            'predicted_class': pred_idx.item(),
            'confidence': confidence.item(),
            'probabilities': ensemble_probs.tolist(),
            'ensemble_size': len(all_probs),
            'method': 'tta'
        }
    
    def predict_with_uncertainty(self, pil_image, num_samples=10):
        """
        Predict with uncertainty estimation using dropout sampling.
        
        Requires model to have dropout enabled during inference.
        """
        self.model.train()  # Enable dropout
        
        predictions = []
        with torch.no_grad():
            for _ in range(num_samples):
                # Preprocess
                transform = transforms.Compose([
                    transforms.Resize((224, 224)),
                    transforms.ToTensor(),
                    transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                       std=[0.229, 0.224, 0.225])
                ])
                img_tensor = transform(pil_image).unsqueeze(0).to(self.device)
                
                # Predict
                output = self.model(img_tensor)
                output = output / self.temperature
                probs = F.softmax(output, dim=1)
                predictions.append(probs.cpu())
        
        self.model.eval()  # Disable dropout
        
        # Ensemble predictions
        ensemble_probs = torch.stack(predictions).mean(dim=0)[0]
        
        # Uncertainty (std of predictions)
        pred_std = torch.stack(predictions).std(dim=0)[0]
        
        confidence, pred_idx = torch.max(ensemble_probs, dim=0)
        
        return {
            'predicted_class': pred_idx.item(),
            'confidence': confidence.item(),
            'uncertainty': pred_std[pred_idx].item(),
            'probabilities': ensemble_probs.tolist(),
            'prob_std': pred_std.tolist(),
            'num_samples': num_samples,
            'method': 'uncertainty_sampling'
        }


class VotingEnsemble:
    """
    Majority voting ensemble for multiple models.
    
    Use when you have trained multiple model architectures.
    """
    
    def __init__(self, models, device=None):
        """
        Args:
            models: list of loaded model instances
            device: torch device
        """
        self.models = models
        self.device = device or get_device()
        for model in self.models:
            model.to(self.device)
            model.eval()
    
    def predict(self, image_tensor):
        """
        Voting ensemble prediction.
        
        Args:
            image_tensor: (1, 3, 224, 224) input tensor
        
        Returns:
            Ensemble prediction dict
        """
        image_tensor = image_tensor.to(self.device)
        
        votes = []
        confidences = []
        
        with torch.no_grad():
            for model in self.models:
                outputs = model(image_tensor)
                probs = F.softmax(outputs, dim=1)
                confidence, pred_idx = torch.max(probs, dim=1)
                
                votes.append(pred_idx.item())
                confidences.append(confidence.item())
        
        # Majority vote
        final_pred = max(set(votes), key=votes.count)
        vote_strength = votes.count(final_pred) / len(votes)
        avg_confidence = np.mean(confidences)
        
        return {
            'predicted_class': final_pred,
            'vote_strength': vote_strength,  # how many models agreed
            'average_confidence': avg_confidence,
            'individual_votes': votes,
            'individual_confidences': confidences,
            'num_models': len(self.models),
            'method': 'voting_ensemble'
        }


def create_tta_predictor(temperature=1.4):
    """Convenience function to create TTA predictor."""
    return EnsemblePredictor(temperature=temperature)
