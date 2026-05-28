"""
Small helper functions used across the backend —
base64 encoding, unique filenames, formatting API responses, etc.
"""

import os
import io
import base64
import uuid
from PIL import Image
from datetime import datetime


def image_to_base64(pil_image, format="JPEG", quality=75):
    """
    Turn a PIL image into a base64 string with a data URI prefix
    so the frontend can display it directly in an <img> tag.
    """
    buffer = io.BytesIO()
    # JPEG can't handle transparency, so convert if needed
    if format.upper() == "JPEG" and pil_image.mode in ("RGBA", "P", "LA"):
        pil_image = pil_image.convert("RGB")
    save_kwargs = {"format": format}
    if format.upper() == "JPEG":
        save_kwargs["quality"] = quality
        save_kwargs["optimize"] = True
    pil_image.save(buffer, **save_kwargs)
    img_bytes = buffer.getvalue()
    b64_string = base64.b64encode(img_bytes).decode("utf-8")
    mime = f"image/{format.lower()}"
    return f"data:{mime};base64,{b64_string}"


def generate_unique_filename(original_filename):
    """Make a unique filename so uploads never overwrite each other."""
    ext = original_filename.rsplit(".", 1)[-1] if "." in original_filename else "png"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = uuid.uuid4().hex[:8]
    return f"xray_{timestamp}_{unique_id}.{ext}"


def format_prediction_response(prediction, confidence, needs_review, gradcam_b64=None):
    """
    Build a standardised JSON-friendly dict for prediction results.
    Used by the predict and gradcam routes.
    """
    response = {
        "prediction": prediction,
        "confidence": round(float(confidence) * 100, 2),
        "confidence_raw": round(float(confidence), 4),
        "needs_review": needs_review,
        "status": "needs_review" if needs_review else "confirmed",
        "timestamp": datetime.now().isoformat()
    }
    if gradcam_b64:
        response["gradcam_image"] = gradcam_b64
    return response
