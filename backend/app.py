"""
Flask backend for OncoDet — Lung Cancer Detection System.
Sets up routes, CORS, and handles model loading.
"""

from flask import Flask, jsonify
from flask_cors import CORS
from config import UPLOAD_FOLDER

from routes.predict_routes import predict_bp
from routes.gradcam_routes import gradcam_bp
from routes.federated_routes import federated_bp
from routes.stats_routes import stats_bp

# keep one GradCAM object alive so we don't reload the model every request
_gradcam_instance = None


def get_gradcam():
    """Return the shared GradCAM instance, creating it on first call."""
    global _gradcam_instance
    if _gradcam_instance is None:
        from services.gradcam import GradCAM
        _gradcam_instance = GradCAM()
        print("[App] GradCAM ready.")
    return _gradcam_instance


def create_app():
    """Build and configure the Flask app."""
    app = Flask(__name__)
    
    app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB limit
    
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    
    # register route blueprints
    app.register_blueprint(predict_bp)
    app.register_blueprint(gradcam_bp)
    app.register_blueprint(federated_bp)
    app.register_blueprint(stats_bp)
    
    # lazy-load model + gradcam on the very first request so gunicorn
    # doesn't time out during boot on Render free tier
    _preloaded = {"done": False}
    
    @app.before_request
    def preload_model():
        if not _preloaded["done"]:
            try:
                from models.model_loader import get_model
                print("[App] Loading DenseNet model...")
                get_model()
                print("[App] Model loaded.")
                
                print("[App] Setting up GradCAM...")
                get_gradcam()
                print("[App] GradCAM set up.")
            except Exception as e:
                print(f"[App] Warning: preload failed: {e}")
            _preloaded["done"] = True
    
    @app.route("/api/health", methods=["GET"])
    def health_check():
        return jsonify({
            "status": "healthy",
            "service": "OncoDet — Lung Cancer Detection System",
            "version": "1.0.0"
        }), 200
    
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Endpoint not found"}), 404
    
    @app.errorhandler(413)
    def too_large(e):
        return jsonify({"error": "File too large. Maximum size: 16MB"}), 413
    
    @app.errorhandler(500)
    def internal_error(e):
        return jsonify({"error": "Internal server error"}), 500
    
    return app


if __name__ == "__main__":
    app = create_app()
    
    print("\n" + "=" * 60)
    print("  OncoDet — Lung Cancer Detection System — Backend Server")
    print("  " + "-" * 54)
    print("  Endpoints:")
    print("    POST /api/upload           — Upload X-ray image")
    print("    POST /api/predict          — Run inference")
    print("    POST /api/gradcam          — Generate Grad-CAM")
    print("    POST /api/federated-train  — Federated learning")
    print("    GET  /api/model-stats      — Performance metrics")
    print("    GET  /api/health           — Health check")
    print("=" * 60 + "\n")
    
    app.run(host="0.0.0.0", port=5001, debug=True)
