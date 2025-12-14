from app.core.debt_analyzer import DebtAnalyzer
from app.clients.blob_singleton import BlobStorageClient
from app.config import Config
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class AnalyzeService:
    """Service for debt analysis operations"""

    _analyzer: Optional[DebtAnalyzer] = None
    _data_loaded: bool = False

    @classmethod
    def initialize(cls):
        """Initialize the service by loading data from Azure Storage"""
        if cls._data_loaded:
            return

        try:
            logger.info(
                "Initializing AnalyzeService and loading data from Azure Storage..."
            )

            # Get blob client
            blob_client = BlobStorageClient.get_instance()
            blob_client.initialize(
                str(Config.AZURE_STORAGE_ACCOUNT_NAME), Config.CONTAINER_NAME
            )

            # Download all files
            logger.info("Downloading CSV and JSON files from Azure Storage...")
            loans_stream = blob_client.download_csv_to_stream(
                Config.BLOB_NAMES["loans"]
            )
            cards_stream = blob_client.download_csv_to_stream(
                Config.BLOB_NAMES["cards"]
            )
            payments_stream = blob_client.download_csv_to_stream(
                Config.BLOB_NAMES["payments"]
            )
            credit_stream = blob_client.download_csv_to_stream(
                Config.BLOB_NAMES["credit"]
            )
            cashflow_stream = blob_client.download_csv_to_stream(
                Config.BLOB_NAMES["cashflow"]
            )
            offers_data = blob_client.download_json(Config.BLOB_NAMES["offers"])

            # Initialize analyzer and load data
            cls._analyzer = DebtAnalyzer()
            cls._analyzer.load_data_from_streams(
                loans_stream,
                cards_stream,
                payments_stream,
                credit_stream,
                cashflow_stream,
                offers_data,
            )

            cls._data_loaded = True
            logger.info("Data loaded successfully!")

        except FileNotFoundError as e:
            logger.error(f"File not found in Azure Storage: {e}")
            raise RuntimeError(f"Failed to load data: {e}") from e
        except ConnectionError as e:
            logger.error(f"Azure connection error: {e}")
            raise RuntimeError(f"Failed to connect to Azure Storage: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error during initialization: {e}")
            raise RuntimeError(f"Failed to initialize service: {e}") from e

    @classmethod
    def is_ready(cls) -> bool:
        """Check if the service is initialized and ready"""
        return cls._data_loaded and cls._analyzer is not None

    @classmethod
    def analyze_debt(cls, customer_id: str, product_type: str) -> Dict:
        """Perform debt analysis for a customer and product"""
        if not cls.is_ready():
            raise RuntimeError("Service not initialized")

        if cls._analyzer is None:
            raise RuntimeError("DebtAnalyzer is not initialized")
        
        return cls._analyzer.analyze(customer_id, product_type)
