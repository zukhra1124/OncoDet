"""
Image preprocessing pipeline for the DenseNet model.
Handles loading images from different sources (file path, bytes, PIL),
resizing to 224x224, converting to RGB, normalising with ImageNet
stats, and adding the batch dimension the model expects.

Includes phone image enhancement to handle domain shift from phone-captured X-rays.
"""

import io
import numpy as np
from PIL import Image, ImageOps, ImageEnhance
from torchvision import transforms
from config import IMAGE_SIZE, IMAGENET_MEAN, IMAGENET_STD


def enhance_phone_image(pil_image, is_phone_image=True):
    """
    Preprocessing step to improve phone-captured X-ray images.
    Handles common phone photography issues: low contrast, noise, lighting variation.
    
    Args:
        pil_image: PIL Image object
        is_phone_image: whether to apply aggressive enhancement (for phone photos)
    
    Returns improved PIL image.
    """
    if not is_phone_image:
        return pil_image
    
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
    
    return pil_image


def get_transform():
    """Standard transform chain — resize, tensor, normalise."""
    return transforms.Compose([
        transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
        transforms.ToTensor(),
        transforms.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD)
    ])


def preprocess_image(image_source, detect_phone_image=True):
    """
    Take an image (path, bytes, or PIL object), run it through the
    preprocessing pipeline, and return the tensor + original PIL image.
    The PIL image is kept around because Grad-CAM needs it for the overlay.
    
    Auto-detects phone-captured images and applies enhancement.
    """
    # figure out what we got and open it
    if isinstance(image_source, str):
        pil_image = Image.open(image_source)
    elif isinstance(image_source, bytes):
        pil_image = Image.open(io.BytesIO(image_source))
    elif isinstance(image_source, Image.Image):
        pil_image = image_source
    else:
        raise ValueError(f"Unsupported image source type: {type(image_source)}")

    # Detect if this is likely a phone-captured image
    # Simple heuristic: if resolution is unusual or metadata suggests phone
    is_phone_image = False
    if detect_phone_image:
        w, h = pil_image.size
        # Phone photos often have 16:9 or 4:3 aspect ratio and moderate resolution
        aspect_ratio = w / h if h > 0 else 1.0
        is_phone_image = (0.75 < aspect_ratio < 1.33) and (500 < w < 4000)
    
    # Apply phone image enhancement if detected
    if is_phone_image:
        pil_image = enhance_phone_image(pil_image, is_phone_image=True)
    
    # X-rays are often grayscale, model needs RGB
    pil_image = pil_image.convert("RGB")

    transform = get_transform()
    tensor = transform(pil_image)

    # model expects shape (batch, channels, h, w)
    tensor = tensor.unsqueeze(0)

    return tensor, pil_image


def validate_image(file):
    """
    Quick check that an uploaded file is actually a valid image
    in one of our supported formats.
    Returns (True, "") if ok, or (False, error_message) if not.
    """
    if file is None:
        return False, "No file provided."

    filename = file.filename.lower()
    allowed = {"png", "jpg", "jpeg", "bmp", "tiff"}
    ext = filename.rsplit(".", 1)[-1] if "." in filename else ""

    if ext not in allowed:
        return False, f"Invalid file type '.{ext}'. Allowed: {', '.join(allowed)}"

    try:
        img = Image.open(file.stream)
        img.verify()
        file.stream.seek(0)  # reset so Flask can read it again later
        return True, ""
    except Exception as e:
        return False, f"Invalid image file: {str(e)}"
