"""
Chest X-ray validation gate — checks whether an uploaded image
is actually a chest X-ray before we let the model classify it.

Uses three heuristics:
1. Grayscale dominance — real X-rays are almost always grayscale
2. Aspect ratio — chest X-rays are roughly square or portrait
3. DenseNet feature confidence — if the model is extremely confused
   (softmax near 50/50 AND low activation energy), the image is
   probably not a chest X-ray at all

This acts as a basic OOD (out-of-distribution) filter so we don't
give meaningless predictions on random images like dog photos,
selfies, or memes.
"""

import torch
import torch.nn.functional as F
import numpy as np
from PIL import Image
from models.model_loader import get_model, get_device
from config import (
    GRAYSCALE_THRESHOLD,
    ASPECT_RATIO_RANGE,
    SOFTMAX_ENTROPY_THRESHOLD,
    CRITICAL_ENTROPY_THRESHOLD,
    CRITICAL_ENERGY_THRESHOLD,
    ACTIVATION_ENERGY_MIN
)


def _check_grayscale(pil_image):
    """
    Check if the image is mostly grayscale.
    X-rays are inherently grayscale — a colour photo of food or
    a landscape will fail this check.
    Returns (passed: bool, detail: str)
    """
    img_array = np.array(pil_image.convert("RGB"))

    # measure how close R, G, B channels are to each other
    r, g, b = img_array[:, :, 0], img_array[:, :, 1], img_array[:, :, 2]

    # average absolute difference between channels
    rg_diff = np.mean(np.abs(r.astype(float) - g.astype(float)))
    rb_diff = np.mean(np.abs(r.astype(float) - b.astype(float)))
    gb_diff = np.mean(np.abs(g.astype(float) - b.astype(float)))

    avg_channel_diff = (rg_diff + rb_diff + gb_diff) / 3.0

    passed = bool(avg_channel_diff < GRAYSCALE_THRESHOLD)
    detail = f"Channel difference: {avg_channel_diff:.1f} (threshold: {GRAYSCALE_THRESHOLD})"

    return passed, detail


def _check_aspect_ratio(pil_image):
    """
    Chest X-rays are typically square-ish or slightly portrait.
    Extremely wide panoramic images or very tall strips are suspicious.
    Returns (passed: bool, detail: str)
    """
    w, h = pil_image.size
    ratio = w / h if h > 0 else 999

    min_ratio, max_ratio = ASPECT_RATIO_RANGE
    passed = bool(min_ratio <= ratio <= max_ratio)
    detail = f"Aspect ratio: {ratio:.2f} (expected: {min_ratio}-{max_ratio})"

    return passed, detail


def _check_model_confidence(image_tensor):
    """
    Run the image through DenseNet and check if the model's prediction
    pattern looks like it saw a chest X-ray.

    Two signals:
    - Softmax entropy: real chest X-rays produce a clear lean towards
      one class. Random images often give ~50/50 with high entropy.
    - Activation energy: the L2 norm of the pre-classifier features.
      Chest X-rays that DenseNet was trained on produce feature vectors
      with energy in a recognisable range.

    Returns (passed: bool, detail: str, extra_info: dict)
    """
    model = get_model()
    device = get_device()
    image_tensor = image_tensor.to(device)

    # hook to grab features right before the classifier
    features_captured = {}

    def hook_fn(module, input, output):
        features_captured["feats"] = output.detach()

    # DenseNet has: features -> ReLU -> AdaptiveAvgPool -> classifier
    # we hook the adaptive avg pool to get the feature vector
    hook = model.densenet.features.register_forward_hook(hook_fn)

    with torch.no_grad():
        outputs = model(image_tensor)
        probabilities = F.softmax(outputs, dim=1)

    hook.remove()

    # --- softmax entropy check ---
    # entropy = -sum(p * log(p)), for 2 classes max is ln(2) ≈ 0.693
    entropy = -torch.sum(probabilities * torch.log(probabilities + 1e-8), dim=1).item()

    # --- activation energy check ---
    if "feats" in features_captured:
        feats = features_captured["feats"]
        # global average pool to get a 1D feature vector
        feat_vector = F.adaptive_avg_pool2d(feats, (1, 1)).squeeze()
        activation_energy = torch.norm(feat_vector, p=2).item()
    else:
        activation_energy = 0.0

    entropy_ok = bool(entropy < SOFTMAX_ENTROPY_THRESHOLD)
    energy_ok = bool(activation_energy > ACTIVATION_ENERGY_MIN)

    # both signals must look normal for this check to pass —
    # high entropy alone (confused model) is enough to fail
    passed = bool(entropy_ok and energy_ok)

    detail = (
        f"Entropy: {entropy:.3f} (threshold: {SOFTMAX_ENTROPY_THRESHOLD}), "
        f"Activation energy: {activation_energy:.1f} (min: {ACTIVATION_ENERGY_MIN})"
    )

    extra_info = {
        "entropy": round(entropy, 4),
        "activation_energy": round(activation_energy, 2),
        "entropy_ok": entropy_ok,
        "energy_ok": energy_ok
    }

    return passed, detail, extra_info


def validate_chest_xray(image_tensor, pil_image):
    """
    Run all validation checks on an image.
    Returns a dict with:
      - is_chest_xray: bool
      - checks: list of individual check results
      - rejection_reason: str (only if is_chest_xray is False)
    """
    checks = []
    failed_reasons = []

    # 1. grayscale check
    gs_passed, gs_detail = _check_grayscale(pil_image)
    checks.append({
        "name": "Grayscale Analysis",
        "passed": gs_passed,
        "detail": gs_detail
    })
    if not gs_passed:
        failed_reasons.append(
            "Image appears to be a colour photograph, not a medical X-ray"
        )

    # 2. aspect ratio check
    ar_passed, ar_detail = _check_aspect_ratio(pil_image)
    checks.append({
        "name": "Aspect Ratio",
        "passed": ar_passed,
        "detail": ar_detail
    })
    if not ar_passed:
        failed_reasons.append(
            "Image dimensions are unusual for a chest X-ray"
        )

    # 3. Diagnostic Confidence (Entropy)
    mc_passed, mc_detail, mc_extra = _check_model_confidence(image_tensor)
    
    entropy_ok = mc_extra.get("entropy_ok", False)
    checks.append({
        "name": "Diagnostic Confidence",
        "passed": entropy_ok,
        "detail": f"Entropy: {mc_extra.get('entropy', 0)} (max expected: {SOFTMAX_ENTROPY_THRESHOLD})"
    })
    if not entropy_ok:
        failed_reasons.append("Model is unusually uncertain about this image")

    # 4. Anatomical Recognition (Activation Energy)
    energy_ok = mc_extra.get("energy_ok", False)
    checks.append({
        "name": "Anatomical Recognition",
        "passed": energy_ok,
        "detail": f"Activation energy: {mc_extra.get('activation_energy', 0)} (min expected: {ACTIVATION_ENERGY_MIN})"
    })
    if not energy_ok:
        failed_reasons.append("Model does not recognize typical human chest anatomy")

    # Require at least 3 checks to fail before rejecting.
    # With a small local dataset the model-confidence checks are less reliable,
    # so we only reject when there is strong multi-signal evidence.
    num_failed = len(failed_reasons)
    is_chest_xray = num_failed < 3

    # HARD REJECT 1: if activation energy is critically low,
    # the model sees absolutely no recognizable chest structures.
    # This catches animal X-rays that are grayscale and square-ish.
    if mc_extra.get("activation_energy", 999) < CRITICAL_ENERGY_THRESHOLD:
        is_chest_xray = False
        if "Model's internal features suggest this is not a chest X-ray" not in failed_reasons:
            failed_reasons.append(
                "Model's internal features suggest this is not a chest X-ray"
            )

    # HARD REJECT 2: if entropy is at/near maximum (~0.693 for 2 classes),
    # the model is purely guessing — no real chest anatomy was detected.
    # Real chest X-rays always produce entropy ≤ 0.682.
    if mc_extra.get("entropy", 0) > CRITICAL_ENTROPY_THRESHOLD:
        is_chest_xray = False
        if "Model is completely uncertain — not a recognizable chest X-ray" not in failed_reasons:
            failed_reasons.append(
                "Model is completely uncertain — not a recognizable chest X-ray"
            )

    result = {
        "is_chest_xray": is_chest_xray,
        "checks": checks,
        "num_checks_passed": len(checks) - num_failed,
        "num_checks_total": len(checks)
    }

    if not is_chest_xray:
        result["rejection_reason"] = (
            "This image does not appear to be a valid chest X-ray. "
            + " | ".join(failed_reasons)
        )

    return result
