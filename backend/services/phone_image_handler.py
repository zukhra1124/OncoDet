"""
Phone image robustness handler — addresses domain shift issues.
Applies preprocessing and post-processing techniques for phone-captured X-ray images.
"""

import torch
import numpy as np
from PIL import Image, ImageOps, ImageEnhance
from torchvision import transforms


def enhance_phone_image(pil_image):
    """
    Preprocessing step to improve phone-captured X-ray images.
    Handles common phone photography issues: low contrast, noise, lighting variation.
    
    Returns improved PIL image.
    """
    # Convert to grayscale first (X-rays are inherently grayscale)
    if pil_image.mode != 'L':
        pil_image = pil_image.convert('L')
    
    # Auto-contrast enhancement (especially good for low-contrast phone photos)
    pil_image = ImageOps.autocontrast(pil_image, cutoff=2)
    
    # Enhance contrast to make features more visible
    enhancer = ImageEnhance.Contrast(pil_image)
    pil_image = enhancer.enhance(1.5)
    
    # Slight sharpening to reduce phone camera blur
    enhancer = ImageEnhance.Sharpness(pil_image)
    pil_image = enhancer.enhance(1.2)
    
    # Convert back to RGB for model (DenseNet expects RGB)
    pil_image = pil_image.convert('RGB')
    
    return pil_image


def test_time_augmentation(image_tensor, model, device, num_augmentations=5):
    """
    Test-Time Augmentation (TTA) — run the same image through the model
    multiple times with different augmentations, then average predictions.
    More robust than single-pass prediction.
    
    Args:
        image_tensor: preprocessed image (batch_size=1)
        model: the neural network model
        device: torch device (cuda/cpu)
        num_augmentations: number of augmented versions to test
    
    Returns:
        averaged_probabilities (2,) - smoother predictions
        individual_preds (num_augmentations, 2) - raw per-augmentation predictions
    """
    augmentation_transforms = [
        transforms.Compose([
            transforms.RandomAffine(degrees=5, translate=(0.05, 0.05)),
            transforms.GaussianBlur(kernel_size=3, sigma=(0.1, 0.3))
        ]),
        transforms.Compose([
            transforms.RandomRotation(10)
        ]),
        transforms.Compose([
            transforms.ColorJitter(brightness=0.1, contrast=0.1)
        ]),
        transforms.Compose([
            transforms.RandomHorizontalFlip(p=1.0)
        ]),
        transforms.Compose([
            transforms.Identity()  # no augmentation, just the original
        ])
    ]
    
    all_probs = []
    model.eval()
    
    with torch.no_grad():
        for i in range(num_augmentations):
            # Get PIL image from tensor for augmentation
            # Note: this is a simplified version; in practice you'd keep the PIL
            # image around from preprocessing
            img_aug = augmentation_transforms[i % len(augmentation_transforms)](
                transforms.ToPILImage()(image_tensor[0].cpu())
            )
            tensor_aug = transforms.ToTensor()(img_aug).unsqueeze(0).to(device)
            tensor_aug = transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225]
            )(tensor_aug)
            
            output = model(tensor_aug)
            probs = torch.softmax(output, dim=1)
            all_probs.append(probs.cpu())
    
    # Average the probabilities across augmentations
    all_probs = torch.cat(all_probs, dim=0)
    averaged_probs = all_probs.mean(dim=0)
    
    return averaged_probs, all_probs


def apply_temperature_scaling(logits, temperature=1.3):
    """
    Temperature scaling — calibrate confidence by dividing logits by temperature.
    Reduces overconfidence, making predictions more reliable especially for OOD samples.
    
    Higher temperature = softer probabilities (lower confidence)
    This helps with domain shift where model is overconfident on phone images.
    
    Args:
        logits: raw model outputs (batch_size, num_classes)
        temperature: scaling factor (>1 = reduce confidence)
    
    Returns:
        calibrated_probabilities (batch_size, num_classes)
    """
    calibrated_logits = logits / temperature
    probs = torch.softmax(calibrated_logits, dim=1)
    return probs
