from azure.storage.blob import BlobServiceClient
from azure.identity import DefaultAzureCredential
from azure.core.exceptions import AzureError
import io
import json
from typing import Optional


class BlobStorageClient:
    """Singleton client for Azure Blob Storage with managed identity"""

    _instance: Optional["BlobStorageClient"] = None
    _blob_service_client: Optional[BlobServiceClient] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(BlobStorageClient, cls).__new__(cls)
        return cls._instance

    def initialize(self, storage_account_name: str, container_name: str):
        """Initialize the blob service client with managed identity"""
        if self._blob_service_client is not None:
            return  # Already initialized

        try:
            account_url = f"https://{storage_account_name}.blob.core.windows.net"
            credential = DefaultAzureCredential()
            self._blob_service_client = BlobServiceClient(
                account_url=account_url, credential=credential
            )
            self.container_name = container_name

            # Test connection
            container_client = self._blob_service_client.get_container_client(
                container_name
            )
            container_client.get_container_properties()

        except AzureError as e:
            raise ConnectionError(
                f"Failed to connect to Azure Storage: {str(e)}"
            ) from e
        except Exception as e:
            raise ConnectionError(
                f"Unexpected error connecting to Azure Storage: {str(e)}"
            ) from e

    def download_blob_to_bytes(self, blob_name: str) -> bytes:
        """Download a blob and return its contents as bytes"""
        if self._blob_service_client is None:
            raise RuntimeError("BlobStorageClient not initialized")

        try:
            blob_client = self._blob_service_client.get_blob_client(
                container=self.container_name, blob=blob_name
            )
            download_stream = blob_client.download_blob()
            return download_stream.readall()
        except AzureError as e:
            raise FileNotFoundError(
                f"Failed to download blob '{blob_name}': {str(e)}"
            ) from e

    def download_csv_to_stream(self, blob_name: str) -> io.StringIO:
        """Download a CSV blob and return as StringIO for pandas"""
        print("kevin1")
        content_bytes = self.download_blob_to_bytes(blob_name)
        print("kevin2")
        content_str = content_bytes.decode("utf-8")
        return io.StringIO(content_str)

    def download_json(self, blob_name: str) -> dict:
        """Download a JSON blob and parse it"""
        content_bytes = self.download_blob_to_bytes(blob_name)
        content_str = content_bytes.decode("utf-8")
        return json.loads(content_str)

    @classmethod
    def get_instance(cls) -> "BlobStorageClient":
        """Get the singleton instance"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
