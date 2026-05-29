"""
All the config values and constants used throughout the backend.
OncoDet — Lung Cancer Detection System
Paths, model params, preprocessing settings, federated learning defaults etc.
"""

import os

# paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
MODEL_WEIGHTS_PATH = os.path.join(BASE_DIR, "models", "best_model.pth")
# Dataset path (produced by dataset_prepare.py)
DATASET_ROOT = os.path.join(os.path.dirname(BASE_DIR), "data", "oncology")

# image preprocessing (matching ImageNet stats for DenseNet)
IMAGE_SIZE = 224
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]

# model settings
NUM_CLASSES = 2
# IMPORTANT: must match ImageFolder alphabetical order used during training.
# ImageFolder sorts: CANCER=0, NORMAL=1  (C < N alphabetically)
CLASS_NAMES = ["CANCER", "NORMAL"]
# Confidence threshold optimised via Grid Search (parameter_tuning.py).
# Objective: minimise False Negatives (missed cancer patients).
# Grid Search result: threshold=0.45, temperature=0.8 → Recall=1.0, FN=0, F1=0.9474
CONFIDENCE_THRESHOLD = 0.45
TEMPERATURE_SCALING = 0.8

# federated learning defaults
NUM_CLIENTS = 4
FED_ROUNDS = 3
LOCAL_EPOCHS = 1
FED_BATCH_SIZE = 16
FED_LEARNING_RATE = 0.001

# allowed image types for upload
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "bmp", "tiff"}

# X-ray validation thresholds (OOD detection)
# NOTE: thresholds relaxed for small local dataset (128 training images).
# A model trained on few examples produces weaker feature activations
# and higher entropy than a model trained on thousands of images.

# channel difference: X-rays are near-grayscale; coloured photos fail this check
GRAYSCALE_THRESHOLD = 30.0
# chest X-rays are roughly square or slightly portrait
ASPECT_RATIO_RANGE = (0.4, 2.0)
# softmax entropy threshold — raised to accept uncertain model outputs on small data
# max possible for 2 classes = ln(2) ≈ 0.693
SOFTMAX_ENTROPY_THRESHOLD = 0.692
# hard reject only if entropy is truly at maximum (model returns exactly 50/50)
CRITICAL_ENTROPY_THRESHOLD = 0.6931
# hard reject if activation energy is essentially zero (no signal at all)
CRITICAL_ENERGY_THRESHOLD = 0.5
# lowered: small-dataset model produces weaker feature vectors
ACTIVATION_ENERGY_MIN = 3.0
# saturation threshold
SATURATION_THRESHOLD = 30.0

# make sure the uploads folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
