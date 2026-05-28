"""
Route for running a federated learning simulation.
POST /api/federated-train
"""

from flask import Blueprint, request, jsonify
from services.federated import run_federated_simulation
from config import NUM_CLIENTS, FED_ROUNDS

federated_bp = Blueprint("federated", __name__)


@federated_bp.route("/api/federated-train", methods=["POST"])
def federated_train():
    """
    Kick off a federated learning simulation.
    The frontend can optionally pass num_clients and num_rounds
    in the JSON body; if not, we use the defaults from config.
    """
    num_clients = NUM_CLIENTS
    num_rounds = FED_ROUNDS

    if request.is_json:
        num_clients = request.json.get("num_clients", NUM_CLIENTS)
        num_rounds = request.json.get("num_rounds", FED_ROUNDS)

    # clamp to reasonable ranges
    num_clients = max(2, min(num_clients, 10))
    num_rounds = max(1, min(num_rounds, 20))

    try:
        training_log = run_federated_simulation(
            num_clients=num_clients,
            num_rounds=num_rounds
        )

        return jsonify({
            "status": "success",
            "message": f"Federated learning completed: {num_rounds} rounds, {num_clients} clients",
            "training_log": training_log
        }), 200

    except Exception as e:
        return jsonify({
            "status": "error",
            "error": f"Federated simulation failed: {str(e)}"
        }), 500
