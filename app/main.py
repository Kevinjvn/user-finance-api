from flask import Flask, jsonify
from app.config import Config
from app.services.analyze_service import AnalyzeService
from app.api.health import health_bp
from app.api.analyze import analyze_bp
import logging
import sys


def create_app():
    """Application factory pattern"""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    logger = logging.getLogger(__name__)

    app = Flask(__name__)

    # Validate configuration
    try:
        Config.validate()
        logger.info("Configuration validated successfully")
    except ValueError as e:
        logger.error(f"Configuration validation failed: {e}")
        sys.exit(1)

    # Initialize service and load data from Azure Storage
    try:
        logger.info("Initializing AnalyzeService...")
        AnalyzeService.initialize()
        logger.info("Service initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize service: {e}")
        logger.error("Application will not start without data loaded")
        sys.exit(1)

    # Register blueprints
    app.register_blueprint(health_bp)
    app.register_blueprint(analyze_bp)

    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return (
            jsonify(
                {
                    "error": "Endpoint not found",
                    "error_type": "NOT_FOUND",
                }
            ),
            404,
        )

    @app.errorhandler(405)
    def method_not_allowed(error):
        return (
            jsonify(
                {
                    "error": "Method not allowed",
                    "error_type": "METHOD_NOT_ALLOWED",
                }
            ),
            405,
        )

    @app.errorhandler(500)
    def internal_error(error):
        return (
            jsonify(
                {
                    "error": "Internal server error",
                    "error_type": "INTERNAL_ERROR",
                }
            ),
            500,
        )

    logger.info("Flask application created successfully")
    return app
