"""
Core interface definitions for BackupFlow
"""

from .database_interface import DatabaseInterface
from .storage_interface import StorageInterface
from .config_interface import ConfigInterface

__all__ = [
    'DatabaseInterface',
    'StorageInterface', 
    'ConfigInterface'
]
