from flask import Blueprint, jsonify
from app.services.analyze_service import AnalyzeService

health_bp = Blueprint("health", __name__)


@health_bp.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "data_loaded": AnalyzeService.is_ready()}), 200
