import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Application configuration"""

    # Azure Storage settings
    AZURE_STORAGE_ACCOUNT_NAME = os.getenv("AZURE_STORAGE_ACCOUNT_NAME")
    CONTAINER_NAME = os.getenv("CONTAINER_NAME", "files")

    # File names (hardcoded as per requirements)
    BLOB_NAMES = {
        "loans": "loans.csv",
        "cards": "cards.csv",
        "payments": "payments_history.csv",
        "credit": "credit_score_history.csv",
        "cashflow": "customer_cashflow.csv",
        "offers": "bank_offers.json",
    }

    @classmethod
    def validate(cls):
        """Validate required configuration"""
        if not cls.AZURE_STORAGE_ACCOUNT_NAME:
            raise ValueError(
                "AZURE_STORAGE_ACCOUNT_NAME environment variable is required"
            )
        if not cls.CONTAINER_NAME:
            raise ValueError("CONTAINER_NAME environment variable is required")
