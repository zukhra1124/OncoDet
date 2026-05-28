"""
Grad-CAM route — generates heatmap visualisations for uploaded X-rays.
POST /api/gradcam
"""

import os
from flask import Blueprint, request, jsonify
from utils.preprocessing import preprocess_image, validate_image
from utils.helpers import image_to_base64, generate_unique_filename
from services.gradcam import GradCAM
from services.prediction import predict
from config import UPLOAD_FOLDER

gradcam_bp = Blueprint("gradcam", __name__)


@gradcam_bp.route("/api/gradcam", methods=["POST"])
def generate_gradcam():
    """
    Generate a Grad-CAM heatmap for a given X-ray.
    Returns the original image, the overlay, and the raw heatmap,
    all as base64. Also includes the prediction + confidence.
    """
    image_path = None

    if "file" in request.files:
        file = request.files["file"]
        is_valid, error_msg = validate_image(file)
        if not is_valid:
            return jsonify({"error": error_msg}), 400
        
        unique_name = generate_unique_filename(file.filename)
        image_path = os.path.join(UPLOAD_FOLDER, unique_name)
        file.save(image_path)

    elif request.is_json and "filename" in request.json:
        filename = request.json["filename"]
        image_path = os.path.join(UPLOAD_FOLDER, filename)
        if not os.path.exists(image_path):
            return jsonify({"error": f"File '{filename}' not found"}), 404
    else:
        return jsonify({"error": "Provide a file or filename"}), 400

    try:
        image_tensor, pil_image = preprocess_image(image_path)

        # validate that this is actually a chest X-ray
        from services.chest_xray_validator import validate_chest_xray
        validation = validate_chest_xray(image_tensor, pil_image)

        if not validation["is_chest_xray"]:
            return jsonify({
                "error": "Image validation failed",
                "is_chest_xray": False,
                "rejection_reason": validation["rejection_reason"],
                "validation_checks": validation["checks"]
            }), 400

        result = predict(image_tensor)

        from app import get_gradcam
        gradcam = get_gradcam()
        overlay_img, heatmap_img = gradcam.generate_overlay(
            image_tensor, pil_image, target_class=result["predicted_index"]
        )

        return jsonify({
            "original_image": image_to_base64(pil_image),
            "gradcam_overlay": image_to_base64(overlay_img),
            "heatmap_image": image_to_base64(heatmap_img),
            "prediction": result["predicted_class"],
            "confidence": round(result["confidence"] * 100, 2),
            "target_class": result["predicted_class"],
            "is_chest_xray": True
        }), 200

    except Exception as e:
        return jsonify({"error": f"Grad-CAM generation failed: {str(e)}"}), 500

    finally:
        # delete the uploaded file after we're done
        if image_path and os.path.exists(image_path):
            try:
                os.remove(image_path)
            except Exception as cleanup_err:
                print(f"Failed to clean up file {image_path}: {cleanup_err}")
