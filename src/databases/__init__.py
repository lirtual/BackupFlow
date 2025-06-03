"""
Database implementation module

Provides backup implementations for various databases
"""

from typing import Dict, Type
from ..interfaces.database_interface import DatabaseInterface
from ..interfaces.config_interface import DatabaseType

# Import concrete implementations
from .mysql_database import MySQLDatabase
from .postgresql_database import PostgreSQLDatabase

# Database type registry
DATABASE_REGISTRY: Dict[DatabaseType, Type[DatabaseInterface]] = {
    DatabaseType.MYSQL: MySQLDatabase,
    DatabaseType.POSTGRESQL: PostgreSQLDatabase,
}


def create_database(db_type: DatabaseType, config: dict) -> DatabaseInterface:
    """
    Factory function to create database instance

    Args:
        db_type: Database type
        config: Database configuration dictionary

    Returns:
        DatabaseInterface: Database instance

    Raises:
        ValueError: Unsupported database type
    """
    if db_type not in DATABASE_REGISTRY:
        raise ValueError(f"Unsupported database type: {db_type}")

    database_class = DATABASE_REGISTRY[db_type]

    # Convert configuration format
    from ..interfaces.config_interface import DatabaseConfig
    database_config = DatabaseConfig(
        database_type=db_type,
        host=config.get('host', 'localhost'),
        port=config.get('port', 3306 if db_type == DatabaseType.MYSQL else 5432),
        username=config.get('username', ''),
        password=config.get('password', ''),
        database_names=config.get('database_names', []),
        connection_timeout=config.get('connection_timeout', 30),
        backup_options=config.get('backup_options', {})
    )

    return database_class(database_config)


def register_database(db_type: DatabaseType, database_class: Type[DatabaseInterface]):
    """
    Register new database type

    Args:
        db_type: Database type
        database_class: Database implementation class
    """
    DATABASE_REGISTRY[db_type] = database_class


def get_supported_databases() -> list:
    """
    Get list of supported database types

    Returns:
        list: List of supported database types
    """
    return list(DATABASE_REGISTRY.keys())


__all__ = [
    'DatabaseInterface',
    'MySQLDatabase',
    'PostgreSQLDatabase',
    'create_database',
    'register_database',
    'get_supported_databases',
    'DATABASE_REGISTRY'
]
