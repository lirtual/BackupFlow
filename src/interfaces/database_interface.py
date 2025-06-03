"""
Database interface definition

Defines the abstract interface that all database implementations must follow
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime


@dataclass
class BackupResult:
    """Backup result data class"""
    success: bool
    backup_file_path: Optional[str] = None
    backup_size: Optional[int] = None
    duration_seconds: Optional[float] = None
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


# Import DatabaseConfig from config_interface
from .config_interface import DatabaseConfig


class DatabaseInterface(ABC):
    """
    Database interface abstract base class

    All database implementations must inherit from this interface and implement all abstract methods
    """

    def __init__(self, config: DatabaseConfig):
        """
        Initialize database connection

        Args:
            config: Database configuration object
        """
        self.config = config
        self._connection = None

    @abstractmethod
    def test_connection(self) -> bool:
        """
        Test database connection

        Returns:
            bool: Whether connection is successful
        """
        pass

    @abstractmethod
    def create_backup(self, output_path: str) -> BackupResult:
        """
        Create database backup

        Args:
            output_path: Backup file output path

        Returns:
            BackupResult: Backup result object
        """
        pass

    @abstractmethod
    def create_single_database_backup(self, database_name: str, output_path: str) -> BackupResult:
        """
        Create backup for a single database

        Args:
            database_name: Name of the database to backup
            output_path: Backup file output path

        Returns:
            BackupResult: Backup result object
        """
        pass

    @abstractmethod
    def validate_backup(self, backup_path: str) -> bool:
        """
        Validate backup file integrity

        Args:
            backup_path: Backup file path

        Returns:
            bool: Whether backup file is valid
        """
        pass

    @abstractmethod
    def get_database_info(self) -> Dict[str, Any]:
        """
        Get database information

        Returns:
            Dict[str, Any]: Dictionary containing database version, size and other information
        """
        pass

    @abstractmethod
    def get_backup_command(self) -> List[str]:
        """
        Get backup command (for debugging and logging)

        Returns:
            List[str]: Backup command list
        """
        pass

    def cleanup(self):
        """
        Cleanup resources (optional implementation)
        """
        if self._connection:
            try:
                self._connection.close()
            except Exception:
                pass
            finally:
                self._connection = None

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.cleanup()
