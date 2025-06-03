"""
Strategy Manager

Manages parsing, validation and execution of multiple backup strategies
"""

import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from ..interfaces.config_interface import BackupConfig, BackupStrategy, DatabaseConfig, StorageConfig, DatabaseType
from .uri_parser import MultiConfigParser, URIParseError
from .database_client_checker import DatabaseClientChecker
from .logger import LoggerMixin


class StrategyError(Exception):
    """Strategy error"""
    pass


@dataclass
class StrategyExecutionResult:
    """Strategy execution result"""
    strategy_id: str
    success: bool
    error_message: Optional[str] = None
    backup_files: Optional[Dict[str, str]] = None
    remote_paths: Optional[Dict[str, str]] = None
    duration_seconds: Optional[float] = None


class StrategyManager(LoggerMixin):
    """Strategy manager"""
    
    def __init__(self):
        self.parser = MultiConfigParser()
        self.client_checker = DatabaseClientChecker()
        self.logger.info("Strategy manager initialization completed")
    
    def parse_strategies_from_env(self) -> List[BackupStrategy]:
        """
        Parse backup strategies from environment variables

        Supports two formats:
        1. Single strategy shorthand: DATABASES, STORAGES
        2. Multi-strategy format: DATABASES_1, STORAGES_1, DATABASES_2, STORAGES_2...

        Returns:
            List[BackupStrategy]: List of parsed strategies
        """
        strategies = []

        # First check if there's a shorthand format single strategy configuration
        simple_db_config = os.getenv("DATABASES")
        simple_storage_config = os.getenv("STORAGES")

        if simple_db_config and simple_storage_config:
            # Use shorthand format
            strategy = self._parse_single_strategy(
                strategy_id="strategy_1",
                db_config_str=simple_db_config,
                storage_config_str=simple_storage_config,
                strategy_suffix=""  # Shorthand format doesn't use suffix
            )
            strategies.append(strategy)
            self.logger.info("Shorthand format strategy parsed successfully: 1 strategy")

            # Check database clients
            self._check_database_clients(strategies)

            return strategies

        # Check multi-strategy format
        strategy_index = 1
        while True:
            # Check if configuration exists for current index
            db_env_key = f"DATABASES_{strategy_index}"
            storage_env_key = f"STORAGES_{strategy_index}"

            db_config_str = os.getenv(db_env_key)
            storage_config_str = os.getenv(storage_env_key)

            # If both configurations don't exist, stop parsing
            if not db_config_str and not storage_config_str:
                break

            # At least one configuration must exist
            if not db_config_str or not storage_config_str:
                raise StrategyError(f"Strategy {strategy_index} configuration incomplete: need to set both {db_env_key} and {storage_env_key}")

            try:
                strategy = self._parse_single_strategy(
                    strategy_id=f"strategy_{strategy_index}",
                    db_config_str=db_config_str,
                    storage_config_str=storage_config_str,
                    strategy_suffix=f"_{strategy_index}"
                )
                strategies.append(strategy)

            except Exception as e:
                raise StrategyError(f"Failed to parse strategy {strategy_index}: {e}")

            strategy_index += 1

        if not strategies:
            raise StrategyError("No strategy configuration found, please set DATABASES and STORAGES environment variables (single strategy) or DATABASES_1 and STORAGES_1 environment variables (multi-strategy)")

        # Check database clients required by all strategies
        self._check_database_clients(strategies)

        return strategies

    def _parse_single_strategy(self, strategy_id: str, db_config_str: str,
                              storage_config_str: str, strategy_suffix: str) -> BackupStrategy:
        """
        Parse single strategy configuration

        Args:
            strategy_id: Strategy ID
            db_config_str: Database configuration string
            storage_config_str: Storage configuration string
            strategy_suffix: Environment variable suffix (e.g., "_1" or "")

        Returns:
            BackupStrategy: Parsed strategy
        """
        # Parse database configuration
        databases = self.parser.parse_databases_config(db_config_str)
        if not databases:
            raise StrategyError(f"Strategy {strategy_id} failed to parse valid database configuration")

        # Parse storage configuration
        storages = self.parser.parse_storages_config(storage_config_str)
        if not storages:
            raise StrategyError(f"Strategy {strategy_id} failed to parse valid storage configuration")

        # Create strategy
        strategy = BackupStrategy(
            strategy_id=strategy_id,
            databases=databases,
            storages=storages,
            backup_name_template=os.getenv(f"BACKUP_NAME_TEMPLATE{strategy_suffix}", "backup_{timestamp}"),
            compression=self._parse_bool_env(f"COMPRESSION{strategy_suffix}", True),
            retention_days=int(os.getenv(f"RETENTION_DAYS{strategy_suffix}", "30")),
            max_backup_size_mb=self._parse_int_env(f"MAX_BACKUP_SIZE_MB{strategy_suffix}"),
            backup_timeout_minutes=int(os.getenv(f"BACKUP_TIMEOUT{strategy_suffix}", "60")),
            verify_backup=self._parse_bool_env(f"VERIFY_BACKUP{strategy_suffix}", True)
        )

        self.logger.info(f"Strategy {strategy_id} parsed successfully: {len(databases)} databases -> {len(storages)} storages")
        return strategy

    def _check_database_clients(self, strategies: List[BackupStrategy]):
        """Check database clients required by all strategies"""
        # Collect all required database types
        required_db_types = []
        for strategy in strategies:
            for db_config in strategy.databases:
                required_db_types.append(db_config.database_type)

        if not required_db_types:
            return

        try:
            # Check client availability
            available_clients = self.client_checker.check_all_required_clients(required_db_types)

            # Log check results
            for db_type, client_type in available_clients.items():
                self.logger.info(f"Database client check passed: {db_type.value} ({client_type.value})")

        except RuntimeError as e:
            # Provide detailed installation suggestions
            suggestion = self.client_checker.suggest_installation_for_strategy(required_db_types)
            self.logger.error("Database client check failed")
            self.logger.error(suggestion)
            raise StrategyError(f"Database client check failed: {e}")

    def _parse_bool_env(self, env_key: str, default: bool = False) -> bool:
        """Parse boolean environment variable"""
        value = os.getenv(env_key)
        if value is None:
            return default
        return value.lower() in ('true', '1', 'yes', 'on')

    def _parse_int_env(self, env_key: str) -> Optional[int]:
        """Parse integer environment variable"""
        value = os.getenv(env_key)
        if value is None:
            return None
        try:
            return int(value)
        except ValueError:
            return None
    
    def validate_strategies(self, strategies: List[BackupStrategy]) -> bool:
        """
        Validate strategy configuration

        Args:
            strategies: Strategy list

        Returns:
            bool: Whether validation passed

        Raises:
            StrategyError: Validation failed
        """
        if not strategies:
            raise StrategyError("No backup strategies configured")

        strategy_ids = set()

        for strategy in strategies:
            # Check strategy ID uniqueness
            if strategy.strategy_id in strategy_ids:
                raise StrategyError(f"Duplicate strategy ID: {strategy.strategy_id}")
            strategy_ids.add(strategy.strategy_id)

            # Validate database configuration
            if not strategy.databases:
                raise StrategyError(f"Strategy {strategy.strategy_id} has no database configuration")

            for db_config in strategy.databases:
                if not db_config.database_names:
                    raise StrategyError(f"Strategy {strategy.strategy_id} database configuration missing database names")

                if not db_config.host or not db_config.username:
                    raise StrategyError(f"Strategy {strategy.strategy_id} database configuration incomplete")

            # Validate storage configuration
            if not strategy.storages:
                raise StrategyError(f"Strategy {strategy.strategy_id} has no storage configuration")

            for storage_config in strategy.storages:
                if not storage_config.bucket or not storage_config.access_key or not storage_config.secret_key:
                    raise StrategyError(f"Strategy {strategy.strategy_id} storage configuration incomplete")

            # Validate other parameters
            if strategy.retention_days <= 0:
                raise StrategyError(f"Strategy {strategy.strategy_id} retention days must be greater than 0")

            if strategy.backup_timeout_minutes <= 0:
                raise StrategyError(f"Strategy {strategy.strategy_id} backup timeout must be greater than 0")

        self.logger.info(f"Strategy validation passed, total {len(strategies)} strategies")
        return True
    
    def get_strategy_summary(self, strategies: List[BackupStrategy]) -> Dict[str, Any]:
        """
        Get strategy summary information

        Args:
            strategies: Strategy list

        Returns:
            Dict[str, Any]: Strategy summary
        """
        summary = {
            "total_strategies": len(strategies),
            "strategies": []
        }
        
        for strategy in strategies:
            strategy_info = {
                "strategy_id": strategy.strategy_id,
                "databases": [
                    {
                        "type": db.database_type.value,
                        "host": db.host,
                        "port": db.port,
                        "database_count": len(db.database_names),
                        "database_names": db.database_names
                    }
                    for db in strategy.databases
                ],
                "storages": [
                    {
                        "type": storage.storage_type.value,
                        "bucket": storage.bucket,
                        "region": storage.region,
                        "prefix": storage.prefix
                    }
                    for storage in strategy.storages
                ],
                "settings": {
                    "compression": strategy.compression,
                    "retention_days": strategy.retention_days,
                    "verify_backup": strategy.verify_backup
                }
            }
            summary["strategies"].append(strategy_info)
        
        return summary
    
    def create_backup_config(self, strategies: List[BackupStrategy]) -> BackupConfig:
        """
        Create backup configuration object

        Args:
            strategies: Strategy list

        Returns:
            BackupConfig: Backup configuration object
        """
        return BackupConfig(
            strategies=strategies,
            global_compression=None,  # Use strategy-level settings
            global_retention_days=None,  # Use strategy-level settings
            global_verify_backup=None  # Use strategy-level settings
        )
