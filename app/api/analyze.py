from flask import Blueprint, request, jsonify
from app.services.analyze_service import AnalyzeService
import logging

logger = logging.getLogger(__name__)

analyze_bp = Blueprint("analyze", __name__)


@analyze_bp.route("/api/analyze", methods=["POST"])
def analyze_debt():
    """Analyze debt scenarios for a customer and product"""
    try:
        # Validate request
        if not request.is_json:
            return (
                jsonify(
                    {
                        "error": "Content-Type must be application/json",
                        "error_type": "VALIDATION_ERROR",
                    }
                ),
                400,
            )

        data = request.get_json()

        # Validate required fields
        validation_errors = []
        if not data.get("customer_id"):
            validation_errors.append("customer_id is required")
        if not data.get("product_type"):
            validation_errors.append("product_type is required")
        elif data.get("product_type") not in ["loan", "card"]:
            validation_errors.append("product_type must be 'loan' or 'card'")

        if validation_errors:
            return (
                jsonify(
                    {
                        "error": "Invalid request data",
                        "error_type": "VALIDATION_ERROR",
                        "details": {"validation_errors": validation_errors},
                    }
                ),
                400,
            )

        # Check if service is ready
        if not AnalyzeService.is_ready():
            return (
                jsonify(
                    {
                        "error": "Service not initialized. Data not loaded from Azure Storage.",
                        "error_type": "SERVICE_NOT_READY",
                    }
                ),
                503,
            )

        # Perform analysis
        customer_id = data["customer_id"]
        product_type = data["product_type"]

        logger.info(
            f"Analyzing debt for customer_id={customer_id}, product_type={product_type}"
        )
        result = AnalyzeService.analyze_debt(customer_id, product_type)

        # Check if analysis returned an error
        if "error" in result:
            return (
                jsonify({"error": result["error"], "error_type": "ANALYSIS_ERROR"}),
                404,
            )

        return jsonify(result), 200

    except RuntimeError as e:
        logger.error(f"Runtime error: {e}")
        return (
            jsonify({"error": str(e), "error_type": "SERVICE_NOT_READY"}),
            503,
        )
    except Exception as e:
        logger.error(f"Unexpected error in analyze endpoint: {e}")
        return (
            jsonify(
                {
                    "error": "An internal error occurred",
                    "error_type": "INTERNAL_ERROR",
                    "details": {"message": str(e)},
                }
            ),
            500,
        )
