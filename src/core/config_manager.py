"""
Configuration Manager

Implements configuration loading, validation and management functionality
"""

import os
import yaml
from typing import Dict, Any, Optional
from dataclasses import asdict

from ..interfaces.config_interface import (
    ConfigInterface, BackupConfig, DatabaseType, StorageType, ConfigError
)
from .strategy_manager import StrategyManager, StrategyError
from .logger import LoggerMixin


class ConfigManager(ConfigInterface, LoggerMixin):
    """
    Configuration Manager Implementation

    Supports loading configuration from YAML files and environment variables
    """

    def __init__(self):
        """Initialize configuration manager"""
        self.strategy_manager = StrategyManager()
        self.logger.debug("Configuration manager initialized")

    def load_config(self, config_path: Optional[str] = None) -> BackupConfig:
        """
        Load multi-strategy configuration

        Priority: Environment variables > Configuration file
        """
        self.logger.info(f"Starting to load multi-strategy configuration, config file path: {config_path}")

        try:
            # Parse multi-strategy configuration
            strategies = self.strategy_manager.parse_strategies_from_env()
            self.strategy_manager.validate_strategies(strategies)
            config = self.strategy_manager.create_backup_config(strategies)
            self.logger.info(f"Multi-strategy configuration loaded successfully, total {len(strategies)} strategies")
            return config

        except Exception as e:
            self.logger.error(f"Configuration loading failed: {e}")
            raise ConfigError(f"Configuration loading failed: {e}")

    def validate_config(self, config: BackupConfig) -> bool:
        """Validate configuration validity"""
        try:
            # Validate multi-strategy configuration
            if not config.strategies:
                raise ConfigError("No backup strategies configured")

            self.strategy_manager.validate_strategies(config.strategies)
            return True

        except Exception as e:
            self.logger.error(f"Configuration validation failed: {e}")
            raise ConfigError(f"Configuration validation failed: {e}")

    def get_default_config(self) -> BackupConfig:
        """Get default configuration"""
        return BackupConfig(
            strategies=[]  # Empty strategy list, needs to be loaded from environment variables
        )
    

