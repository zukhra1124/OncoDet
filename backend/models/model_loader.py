"""
Loads the OncologyNet model once and keeps it cached.
If fine-tuned weights exist, load those; otherwise use ImageNet backbone.
"""

import os
import torch
from models.densenet_model import OncologyNet
from config import MODEL_WEIGHTS_PATH, NUM_CLASSES

_model = None
_device = None


def get_device():
    """Pick GPU if available, otherwise CPU."""
    global _device
    if _device is None:
        _device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    return _device


def load_model():
    """
    Load the model into memory (only runs once thanks to the global cache).
    Tries to load our own trained weights first, falls back to ImageNet.
    """
    global _model

    if _model is not None:
        return _model

    device = get_device()
    print(f"[Model Loader] Using device: {device}")

    _model = OncologyNet(num_classes=NUM_CLASSES, pretrained=True)

    # try loading fine-tuned weights if they exist
    if os.path.exists(MODEL_WEIGHTS_PATH):
        print(f"[Model Loader] Found trained weights at: {MODEL_WEIGHTS_PATH}")
        state_dict = torch.load(MODEL_WEIGHTS_PATH, map_location=device)
        _model.load_state_dict(state_dict)
        print("[Model Loader] Weights loaded successfully.")
    else:
        print("[Model Loader] No trained weights found, using ImageNet defaults.")
        print(f"[Model Loader] (looked in: {MODEL_WEIGHTS_PATH})")

    _model = _model.to(device)
    _model.eval()
    print("[Model Loader] Model is ready.")

    return _model


def get_model():
    """Shortcut to get the cached model."""
    return load_model()
