"""
Storage interface definition

Defines the abstract interface that all storage implementations must follow
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime


@dataclass
class UploadResult:
    """Upload result data class"""
    success: bool
    remote_path: Optional[str] = None
    upload_size: Optional[int] = None
    duration_seconds: Optional[float] = None
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


# Import StorageConfig from config_interface
from .config_interface import StorageConfig


@dataclass
class StorageObject:
    """Storage object information"""
    key: str
    size: int
    last_modified: datetime
    etag: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class StorageInterface(ABC):
    """
    Storage interface abstract base class

    All storage implementations must inherit from this interface and implement all abstract methods
    """

    def __init__(self, config: StorageConfig):
        """
        Initialize storage connection

        Args:
            config: Storage configuration object
        """
        self.config = config
        self._client = None

    @abstractmethod
    def test_connection(self) -> bool:
        """
        Test storage connection

        Returns:
            bool: Whether connection is successful
        """
        pass

    @abstractmethod
    def upload_file(self, local_path: str, remote_path: str,
                   metadata: Optional[Dict[str, str]] = None) -> UploadResult:
        """
        Upload file to storage

        Args:
            local_path: Local file path
            remote_path: Remote file path
            metadata: Optional file metadata

        Returns:
            UploadResult: Upload result object
        """
        pass

    @abstractmethod
    def download_file(self, remote_path: str, local_path: str) -> bool:
        """
        Download file from storage

        Args:
            remote_path: Remote file path
            local_path: Local file path

        Returns:
            bool: Whether download is successful
        """
        pass

    @abstractmethod
    def delete_file(self, remote_path: str) -> bool:
        """
        Delete file from storage

        Args:
            remote_path: Remote file path

        Returns:
            bool: Whether deletion is successful
        """
        pass

    @abstractmethod
    def list_files(self, prefix: Optional[str] = None,
                  max_keys: Optional[int] = None) -> List[StorageObject]:
        """
        List files in storage

        Args:
            prefix: File prefix filter
            max_keys: Maximum number of results to return

        Returns:
            List[StorageObject]: List of storage objects
        """
        pass

    @abstractmethod
    def cleanup_old_files(self, retention_days: int,
                         prefix: Optional[str] = None) -> List[str]:
        """
        Cleanup old files

        Args:
            retention_days: Number of days to retain
            prefix: File prefix filter

        Returns:
            List[str]: List of deleted file paths
        """
        pass

    @abstractmethod
    def get_file_info(self, remote_path: str) -> Optional[StorageObject]:
        """
        Get file information

        Args:
            remote_path: Remote file path

        Returns:
            Optional[StorageObject]: File information, None if file doesn't exist
        """
        pass

    @abstractmethod
    def get_storage_info(self) -> Dict[str, Any]:
        """
        Get storage information

        Returns:
            Dict[str, Any]: Dictionary containing storage configuration and status information
        """
        pass

    def cleanup(self):
        """
        Cleanup resources (optional implementation)
        """
        if self._client:
            try:
                self._client.close()
            except Exception:
                pass
            finally:
                self._client = None

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.cleanup()
