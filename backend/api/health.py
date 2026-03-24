from flask import jsonify

from backend.api import api_bp


@api_bp.get("/health")
def health():
    return jsonify({"status": "ok"})
