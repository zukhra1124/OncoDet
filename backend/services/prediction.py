"""
Prediction service — takes a preprocessed image tensor, runs it through
the OncologyNet model, applies softmax, and returns NORMAL or CANCER + confidence.
Low-confidence predictions are flagged for mandatory physician review.

Temperature scaling calibrates overconfident softmax outputs, improving
reliability on domain-shifted inputs (phone-captured X-rays, older equipment).
"""

import torch
import torch.nn.functional as F
from models.model_loader import get_model, get_device
from config import CLASS_NAMES, CONFIDENCE_THRESHOLD


def predict(image_tensor, use_temperature_scaling=True, temperature=0.8):
    """
    Run inference on a preprocessed image.
    Returns a dict with the predicted class, confidence, per-class
    probabilities, and whether it needs human review.
    
    Args:
        image_tensor: input tensor (batch_size=1, 3, 224, 224)
        use_temperature_scaling: apply temperature scaling to reduce overconfidence
        temperature: scaling factor (higher = more conservative/lower confidence)
    
    Returns prediction dict with class, confidence, probabilities, needs_review
    """
    model = get_model()
    device = get_device()

    image_tensor = image_tensor.to(device)

    # no need to track gradients during inference
    with torch.no_grad():
        outputs = model(image_tensor)
        
        # Apply temperature scaling for better calibration
        if use_temperature_scaling:
            outputs = outputs / temperature
        
        probabilities = F.softmax(outputs, dim=1)

    confidence, predicted_idx = torch.max(probabilities, dim=1)
    confidence = confidence.item()
    predicted_idx = predicted_idx.item()
    predicted_class = CLASS_NAMES[predicted_idx]

    # per-class breakdown (as percentages)
    prob_dict = {
        CLASS_NAMES[i]: round(probabilities[0][i].item() * 100, 2)
        for i in range(len(CLASS_NAMES))
    }

    # flag low-confidence predictions
    needs_review = confidence < CONFIDENCE_THRESHOLD

    return {
        "predicted_class": predicted_class,
        "predicted_index": predicted_idx,
        "confidence": confidence,
        "probabilities": prob_dict,
        "needs_review": needs_review,
        "threshold": CONFIDENCE_THRESHOLD,
        "temperature_scaled": use_temperature_scaling
    }
