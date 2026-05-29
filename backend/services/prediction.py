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
from config import CLASS_NAMES, CONFIDENCE_THRESHOLD, TEMPERATURE_SCALING


def predict(image_tensor, use_temperature_scaling=True, temperature=TEMPERATURE_SCALING):
    """
    Run inference on a preprocessed image.
    Returns a dict with the predicted class, confidence, per-class
    probabilities, and whether it needs human review.
    
    The tuned decision rule is:
      - apply temperature scaling to logits
      - compute softmax probabilities
      - classify as CANCER if P(cancer) >= CONFIDENCE_THRESHOLD
      - otherwise classify as NORMAL
    """
    model = get_model()
    device = get_device()

    image_tensor = image_tensor.to(device)

    with torch.no_grad():
        outputs = model(image_tensor)

        if use_temperature_scaling:
            outputs = outputs / temperature

        probabilities = F.softmax(outputs, dim=1)

    cancer_prob = probabilities[0][0].item()
    normal_prob = probabilities[0][1].item()
    predicted_idx = 0 if cancer_prob >= CONFIDENCE_THRESHOLD else 1
    predicted_class = CLASS_NAMES[predicted_idx]
    confidence = cancer_prob if predicted_idx == 0 else normal_prob

    prob_dict = {
        CLASS_NAMES[i]: round(probabilities[0][i].item() * 100, 2)
        for i in range(len(CLASS_NAMES))
    }

    needs_review = confidence < CONFIDENCE_THRESHOLD

    return {
        "predicted_class": predicted_class,
        "predicted_index": predicted_idx,
        "confidence": confidence,
        "probabilities": prob_dict,
        "needs_review": needs_review,
        "threshold": CONFIDENCE_THRESHOLD,
        "temperature": temperature,
        "temperature_scaled": use_temperature_scaling
    }
