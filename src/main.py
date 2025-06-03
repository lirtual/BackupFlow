#!/usr/bin/env python3
"""
BackupFlow Main Program

Provides command line interface and integrates all components
"""

import sys
import argparse
import os
from typing import Optional

# Add project root directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.config_manager import ConfigManager
from src.core.multi_strategy_backup_manager import MultiStrategyBackupManager
from src.core.logger import setup_logger, get_logger
from src.interfaces.config_interface import ConfigError
from src.databases import create_database
from src.storages import create_storage


def setup_logging(log_level: str = "INFO", log_file: Optional[str] = None):
    """Setup logging"""
    setup_logger(
        name="backup_system",
        level=log_level,
        log_file=log_file,
        enable_console=True,
        enable_colors=True
    )


def create_argument_parser() -> argparse.ArgumentParser:
    """Create command line argument parser"""
    parser = argparse.ArgumentParser(
        description="BackupFlow",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example usage:
  %(prog)s                                    # Use environment variable configuration
  %(prog)s --log-level DEBUG                  # Enable debug mode
  %(prog)s --log-file backup.log              # Output logs to file
  %(prog)s --test-connections                 # Test connections only

Environment variable configuration example:
  Refer to config/config.env.example file to set environment variables
        """
    )

    parser.add_argument(
        '--config', '-c',
        type=str,
        help='Configuration file path (YAML format, optional, environment variables recommended)'
    )

    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        default='INFO',
        help='Log level (default: INFO)'
    )

    parser.add_argument(
        '--log-file',
        type=str,
        help='Log file path'
    )

    parser.add_argument(
        '--test-connections',
        action='store_true',
        help='Test database and storage connections only, do not execute backup'
    )



    parser.add_argument(
        '--info',
        action='store_true',
        help='Show configuration and system information'
    )

    parser.add_argument(
        '--version',
        action='version',
        version='BackupFlow v1.0.0'
    )

    return parser


def test_connections(config_manager: ConfigManager, config_path: Optional[str]) -> bool:
    """Test database and storage connections"""
    logger = get_logger()

    try:
        # Load multi-strategy configuration
        config = config_manager.load_config(config_path)

        logger.info("Starting connection tests...")
        logger.info(f"Total {len(config.strategies)} strategies to test")

        all_success = True

        # Test connections for each strategy
        for i, strategy in enumerate(config.strategies, 1):
            logger.info(f"=== Testing Strategy {i}: {strategy.strategy_id} ===")

            # Test database connections
            logger.info(f"Testing {len(strategy.databases)} database connections...")
            for j, db_config in enumerate(strategy.databases, 1):
                logger.info(f"  Database {j}: {db_config.database_type.value}@{db_config.host}")

                # Convert configuration format
                db_config_dict = {
                    'host': db_config.host,
                    'port': db_config.port,
                    'username': db_config.username,
                    'password': db_config.password,
                    'database_names': db_config.database_names,
                    'connection_timeout': db_config.connection_timeout,
                    'backup_options': db_config.backup_options
                }

                database = create_database(db_config.database_type, db_config_dict)

                with database:
                    if database.test_connection():
                        logger.info(f"    ✓ Database connection test successful")
                    else:
                        logger.error(f"    ✗ Database connection test failed")
                        all_success = False

            # Test storage connections
            logger.info(f"Testing {len(strategy.storages)} storage connections...")
            for j, storage_config in enumerate(strategy.storages, 1):
                logger.info(f"  Storage {j}: {storage_config.storage_type.value}/{storage_config.bucket}")

                # Convert configuration format
                storage_config_dict = {
                    'bucket': storage_config.bucket,
                    'access_key': storage_config.access_key,
                    'secret_key': storage_config.secret_key,
                    'endpoint': storage_config.endpoint,
                    'region': storage_config.region,
                    'prefix': storage_config.prefix
                }

                storage = create_storage(storage_config.storage_type, storage_config_dict)

                with storage:
                    if storage.test_connection():
                        logger.info(f"    ✓ Storage connection test successful")
                    else:
                        logger.error(f"    ✗ Storage connection test failed")
                        all_success = False

        if all_success:
            logger.info("All connection tests passed")
        else:
            logger.error("Some connection tests failed")

        return all_success

    except Exception as e:
        logger.error(f"Connection test failed: {e}")
        return False


def show_info(config_manager: ConfigManager, config_path: Optional[str]):
    """Show configuration and system information"""
    logger = get_logger()

    try:
        # Load multi-strategy configuration
        config = config_manager.load_config(config_path)

        logger.info("=== System Information ===")
        logger.info(f"Python version: {sys.version}")
        logger.info(f"Configuration file: {config_path or 'Environment variables'}")
        logger.info(f"Number of strategies: {len(config.strategies)}")

        # Show configuration information for each strategy
        for i, strategy in enumerate(config.strategies, 1):
            logger.info(f"=== Strategy {i}: {strategy.strategy_id} ===")

            # Database information
            logger.info(f"Number of databases: {len(strategy.databases)}")
            for j, db_config in enumerate(strategy.databases, 1):
                logger.info(f"  Database {j}:")
                logger.info(f"    Type: {db_config.database_type.value}")
                logger.info(f"    Host: {db_config.host}:{db_config.port}")
                logger.info(f"    User: {db_config.username}")
                logger.info(f"    Databases: {', '.join(db_config.database_names)}")
                logger.info(f"    Connection timeout: {db_config.connection_timeout} seconds")

            # Storage information
            logger.info(f"Number of storages: {len(strategy.storages)}")
            for j, storage_config in enumerate(strategy.storages, 1):
                logger.info(f"  Storage {j}:")
                logger.info(f"    Type: {storage_config.storage_type.value}")
                logger.info(f"    Bucket: {storage_config.bucket}")
                logger.info(f"    Endpoint: {storage_config.endpoint or 'N/A'}")
                logger.info(f"    Region: {storage_config.region or 'N/A'}")
                logger.info(f"    Prefix: {storage_config.prefix or 'N/A'}")

            # Strategy configuration
            logger.info(f"Configuration options:")
            logger.info(f"    Compression: {strategy.compression}")
            logger.info(f"    Retention days: {strategy.retention_days}")
            logger.info(f"    Verify backup: {strategy.verify_backup}")
            logger.info(f"    Backup timeout: {strategy.backup_timeout_minutes} minutes")

    except Exception as e:
        logger.error(f"Failed to get system information: {e}")


def run_backup(config_manager: ConfigManager, config_path: Optional[str]) -> bool:
    """Execute backup"""
    logger = get_logger()

    try:
        # Load multi-strategy configuration
        config = config_manager.load_config(config_path)

        # Create multi-strategy backup manager (serial execution only)
        backup_manager = MultiStrategyBackupManager(config, parallel_execution=False)

        # Execute backup
        logger.info("Starting multi-strategy backup...")
        session = backup_manager.create_backup()

        if session.success:
            logger.info("Multi-strategy backup completed!")
            logger.info(f"Session ID: {session.session_id}")
            logger.info(f"Successful strategies: {len([r for r in session.strategy_results if r.success])}/{len(session.strategy_results)}")
            logger.info(f"Total backup files: {session.total_backup_files}")
            logger.info(f"Total duration: {session.duration_seconds:.2f} seconds")

            # Show detailed results for each strategy
            for result in session.strategy_results:
                if result.success:
                    logger.info(f"✓ {result.strategy_id}: Success ({result.duration_seconds:.2f}s)")
                else:
                    logger.error(f"✗ {result.strategy_id}: Failed - {result.error_message}")

            return True
        else:
            logger.error(f"Multi-strategy backup failed: {session.error_message}")
            return False

    except Exception as e:
        logger.error(f"Backup execution failed: {e}")
        return False





def main():
    """Main function"""
    # Parse command line arguments
    parser = create_argument_parser()
    args = parser.parse_args()

    # Get log configuration from environment variables (if command line arguments not specified)
    log_level = args.log_level
    if not log_level or log_level == 'INFO':  # If default value, check environment variables
        log_level = os.getenv('LOG_LEVEL', args.log_level)

    log_file = args.log_file
    if not log_file:  # If not specified in command line, check environment variables
        log_file = os.getenv('LOG_FILE')

    # Setup logging
    setup_logging(log_level, log_file)
    logger = get_logger()

    logger.info("BackupFlow started")

    try:
        # Create configuration manager
        config_manager = ConfigManager()

        # Execute different operations based on arguments
        if args.test_connections:
            success = test_connections(config_manager, args.config)
            sys.exit(0 if success else 1)

        elif args.info:
            show_info(config_manager, args.config)
            sys.exit(0)

        else:
            # Execute backup
            success = run_backup(config_manager, args.config)
            sys.exit(0 if success else 1)

    except ConfigError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)

    except KeyboardInterrupt:
        logger.info("User interrupted operation")
        sys.exit(1)

    except Exception as e:
        logger.error(f"Program execution failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
