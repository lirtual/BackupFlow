"""
Configuration interface definition

Defines the abstract interface for configuration management
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum


class DatabaseType(Enum):
    """Supported database types"""
    MYSQL = "mysql"
    POSTGRESQL = "postgresql"


class StorageType(Enum):
    """Supported storage types"""
    R2 = "r2"
    S3 = "s3"


@dataclass
class DatabaseConfig:
    """Database configuration data class"""
    database_type: DatabaseType
    host: str
    port: int
    username: str
    password: str
    database_names: List[str]
    connection_timeout: int = 30
    backup_options: Optional[Dict[str, Any]] = None


@dataclass
class StorageConfig:
    """Storage configuration data class"""
    storage_type: StorageType
    endpoint: Optional[str]
    access_key: str
    secret_key: str
    bucket: str
    region: str = "auto"
    prefix: Optional[str] = None
    storage_options: Optional[Dict[str, Any]] = None


@dataclass
class BackupStrategy:
    """Single backup strategy configuration"""
    strategy_id: str
    databases: List[DatabaseConfig]
    storages: List[StorageConfig]

    # Backup settings
    backup_name_template: str = "backup_{timestamp}"
    compression: bool = True
    retention_days: int = 30

    # Advanced settings
    max_backup_size_mb: Optional[int] = None
    backup_timeout_minutes: int = 60
    verify_backup: bool = True


@dataclass
class BackupConfig:
    """Backup configuration data class - multi-strategy support"""
    strategies: List[BackupStrategy]

    # Global settings
    global_compression: Optional[bool] = None
    global_retention_days: Optional[int] = None
    global_verify_backup: Optional[bool] = None

    # Notification settings
    notification_config: Optional[Dict[str, Any]] = None


class ConfigInterface(ABC):
    """
    Configuration interface abstract base class

    Defines the standard interface for configuration loading, validation and management
    """

    @abstractmethod
    def load_config(self, config_path: Optional[str] = None) -> BackupConfig:
        """
        Load configuration

        Args:
            config_path: Configuration file path, if None load from environment variables

        Returns:
            BackupConfig: Backup configuration object

        Raises:
            ConfigError: Configuration loading or validation failed
        """
        pass

    @abstractmethod
    def validate_config(self, config: BackupConfig) -> bool:
        """
        Validate configuration validity

        Args:
            config: Configuration object to validate

        Returns:
            bool: Whether configuration is valid

        Raises:
            ConfigError: Configuration validation failed
        """
        pass

    @abstractmethod
    def get_default_config(self) -> BackupConfig:
        """
        Get default configuration

        Returns:
            BackupConfig: Default configuration object
        """
        pass




class ConfigError(Exception):
    """Configuration related exception"""
    pass
