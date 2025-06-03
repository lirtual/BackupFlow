"""
Storage implementation module

Provides backup implementations for various storage services
"""

from typing import Dict, Type
from ..interfaces.storage_interface import StorageInterface
from ..interfaces.config_interface import StorageType

# Import concrete implementations
from .r2_storage import R2Storage
from .s3_storage import S3Storage

# Storage type registry
STORAGE_REGISTRY: Dict[StorageType, Type[StorageInterface]] = {
    StorageType.R2: R2Storage,
    StorageType.S3: S3Storage,
}


def create_storage(storage_type: StorageType, config: dict) -> StorageInterface:
    """
    Factory function to create storage instance

    Args:
        storage_type: Storage type
        config: Storage configuration dictionary

    Returns:
        StorageInterface: Storage instance

    Raises:
        ValueError: Unsupported storage type
    """
    if storage_type not in STORAGE_REGISTRY:
        raise ValueError(f"Unsupported storage type: {storage_type}")

    storage_class = STORAGE_REGISTRY[storage_type]

    # Convert configuration format
    from ..interfaces.config_interface import StorageConfig
    storage_config = StorageConfig(
        storage_type=storage_type,
        endpoint=config.get('endpoint'),
        access_key=config.get('access_key'),
        secret_key=config.get('secret_key'),
        bucket=config.get('bucket'),
        region=config.get('region', 'auto'),
        prefix=config.get('prefix'),
        storage_options=config.get('storage_options', {})
    )

    return storage_class(storage_config)


def register_storage(storage_type: StorageType, storage_class: Type[StorageInterface]):
    """
    Register new storage type

    Args:
        storage_type: Storage type
        storage_class: Storage implementation class
    """
    STORAGE_REGISTRY[storage_type] = storage_class


def get_supported_storages() -> list:
    """
    Get list of supported storage types

    Returns:
        list: List of supported storage types
    """
    return list(STORAGE_REGISTRY.keys())


__all__ = [
    'StorageInterface',
    'R2Storage',
    'S3Storage',
    'create_storage',
    'register_storage',
    'get_supported_storages',
    'STORAGE_REGISTRY'
]
