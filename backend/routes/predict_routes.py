"""
Routes for uploading X-ray images and running predictions.
POST /api/upload  — save an image
POST /api/predict — upload + run the model + return results with Grad-CAM
"""

import os
from flask import Blueprint, request, jsonify
from utils.preprocessing import preprocess_image, validate_image
from utils.helpers import generate_unique_filename, format_prediction_response, image_to_base64
from services.prediction import predict
from services.gradcam import GradCAM
from config import UPLOAD_FOLDER

predict_bp = Blueprint("predict", __name__)


@predict_bp.route("/api/upload", methods=["POST"])
def upload_image():
    """Save an uploaded chest X-ray, validate it first."""
    if "file" not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    is_valid, error_msg = validate_image(file)
    if not is_valid:
        return jsonify({"error": error_msg}), 400

    unique_name = generate_unique_filename(file.filename)
    save_path = os.path.join(UPLOAD_FOLDER, unique_name)
    file.save(save_path)

    return jsonify({
        "message": "Image uploaded successfully",
        "filename": unique_name,
        "path": save_path
    }), 200


@predict_bp.route("/api/predict", methods=["POST"])
def predict_image():
    """
    Run the full pipeline: preprocess -> model inference -> Grad-CAM.
    Accepts either a direct file upload or a filename of a previously
    uploaded image.
    """
    image_path = None

    # direct file upload
    if "file" in request.files:
        file = request.files["file"]
        is_valid, error_msg = validate_image(file)
        if not is_valid:
            return jsonify({"error": error_msg}), 400
        
        unique_name = generate_unique_filename(file.filename)
        image_path = os.path.join(UPLOAD_FOLDER, unique_name)
        file.save(image_path)

    # or reference an already-uploaded file
    elif request.is_json and "filename" in request.json:
        filename = request.json["filename"]
        image_path = os.path.join(UPLOAD_FOLDER, filename)
        if not os.path.exists(image_path):
            return jsonify({"error": f"File '{filename}' not found"}), 404

    else:
        return jsonify({"error": "Provide a file upload or filename in JSON body"}), 400

    try:
        image_tensor, pil_image = preprocess_image(image_path)

        # validate that this is actually a chest X-ray before predicting
        from services.chest_xray_validator import validate_chest_xray
        validation = validate_chest_xray(image_tensor, pil_image)

        if not validation["is_chest_xray"]:
            return jsonify({
                "error": "Image validation failed",
                "is_chest_xray": False,
                "rejection_reason": validation["rejection_reason"],
                "validation_checks": validation["checks"],
                "num_checks_passed": validation["num_checks_passed"],
                "num_checks_total": validation["num_checks_total"]
            }), 400

        result = predict(image_tensor)

        # grab the shared GradCAM instance
        from app import get_gradcam
        gradcam = get_gradcam()
        overlay_img, heatmap_img = gradcam.generate_overlay(
            image_tensor, pil_image, target_class=result["predicted_index"]
        )

        response = format_prediction_response(
            prediction=result["predicted_class"],
            confidence=result["confidence"],
            needs_review=result["needs_review"],
            gradcam_b64=image_to_base64(overlay_img)
        )
        response["probabilities"] = result["probabilities"]
        response["original_image"] = image_to_base64(pil_image)
        response["heatmap_image"] = image_to_base64(heatmap_img)
        response["threshold"] = result["threshold"]
        response["is_chest_xray"] = True
        response["validation_checks"] = validation["checks"]

        return jsonify(response), 200

    except Exception as e:
        return jsonify({"error": f"Prediction failed: {str(e)}"}), 500

    finally:
        # clean up the temp file so uploads don't pile up on disk
        if image_path and os.path.exists(image_path):
            try:
                os.remove(image_path)
            except Exception as cleanup_err:
                print(f"Failed to clean up file {image_path}: {cleanup_err}")
