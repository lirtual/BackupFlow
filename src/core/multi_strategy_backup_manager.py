"""
Multi-Strategy Backup Manager

Supports flexible backup strategy execution from multiple databases to multiple storages
"""

import os
import tempfile
import time
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


from ..interfaces.config_interface import BackupConfig, BackupStrategy, DatabaseConfig, StorageConfig
from ..interfaces.database_interface import DatabaseInterface
from ..interfaces.storage_interface import StorageInterface
from ..databases import create_database
from ..storages import create_storage
from .backup_manager import BackupSession
from .strategy_manager import StrategyExecutionResult
from .logger import LoggerMixin


@dataclass
class MultiStrategyBackupSession:
    """Multi-strategy backup session information"""
    session_id: str
    start_time: datetime
    config: BackupConfig
    strategy_results: List[StrategyExecutionResult]
    success: bool = False
    error_message: Optional[str] = None
    duration_seconds: Optional[float] = None
    total_databases: int = 0
    total_storages: int = 0
    total_backup_files: int = 0


class MultiStrategyBackupManager(LoggerMixin):
    """
    Multi-Strategy Backup Manager

    Executes multiple backup strategies sequentially
    """

    def __init__(self, config: BackupConfig, parallel_execution: bool = False):
        """
        Initialize multi-strategy backup manager

        Args:
            config: Backup configuration
            parallel_execution: Ignored, kept for compatibility
        """
        self.config = config
        self.logger.info("Multi-strategy backup manager initialized")
    
    def create_backup(self) -> MultiStrategyBackupSession:
        """
        Execute multi-strategy backup

        Returns:
            MultiStrategyBackupSession: Multi-strategy backup session information
        """
        session_id = f"multi_backup_{int(time.time())}"
        session = MultiStrategyBackupSession(
            session_id=session_id,
            start_time=datetime.now(),
            config=self.config,
            strategy_results=[]
        )

        self.logger.info(f"Starting multi-strategy backup session: {session_id}")

        try:
            if not self.config.strategies:
                raise Exception("No backup strategies configured")

            # Count totals
            session.total_databases = sum(len(strategy.databases) for strategy in self.config.strategies)
            session.total_storages = sum(len(strategy.storages) for strategy in self.config.strategies)

            self.logger.info(f"Total {len(self.config.strategies)} strategies, {session.total_databases} databases, {session.total_storages} storages")

            # Execute strategies sequentially
            self._execute_strategies_sequential(session)

            # Check execution results
            successful_strategies = [r for r in session.strategy_results if r.success]
            failed_strategies = [r for r in session.strategy_results if not r.success]

            session.total_backup_files = sum(
                len(r.backup_files) for r in successful_strategies
                if r.backup_files
            )

            if failed_strategies:
                error_messages = [f"{r.strategy_id}: {r.error_message}" for r in failed_strategies]
                session.error_message = f"Some strategies failed: {'; '.join(error_messages)}"
                session.success = len(successful_strategies) > 0  # Partial success if at least one succeeds
                self.logger.warning(f"Some strategies failed: {len(failed_strategies)}/{len(self.config.strategies)}")
            else:
                session.success = True
                self.logger.info("All strategies executed successfully")

            session.duration_seconds = (datetime.now() - session.start_time).total_seconds()

            self.logger.info(f"Multi-strategy backup session completed: {session_id}, duration: {session.duration_seconds:.2f}s")
            self.logger.info(f"Successful strategies: {len(successful_strategies)}/{len(self.config.strategies)}")
            self.logger.info(f"Total backup files: {session.total_backup_files}")

        except Exception as e:
            session.success = False
            session.error_message = str(e)
            session.duration_seconds = (datetime.now() - session.start_time).total_seconds()

            self.logger.error(f"Multi-strategy backup session failed: {session_id}, error: {e}")

        return session
    
    def _execute_strategies_sequential(self, session: MultiStrategyBackupSession):
        """Execute strategies sequentially"""
        self.logger.info("Executing backup strategies sequentially")

        for i, strategy in enumerate(self.config.strategies, 1):
            self.logger.info(f"Executing strategy {i}/{len(self.config.strategies)}: {strategy.strategy_id}")

            try:
                result = self._execute_single_strategy(strategy)
                session.strategy_results.append(result)

                if result.success:
                    self.logger.info(f"Strategy {strategy.strategy_id} executed successfully")
                else:
                    self.logger.error(f"Strategy {strategy.strategy_id} execution failed: {result.error_message}")

            except Exception as e:
                result = StrategyExecutionResult(
                    strategy_id=strategy.strategy_id,
                    success=False,
                    error_message=str(e)
                )
                session.strategy_results.append(result)
                self.logger.error(f"Strategy {strategy.strategy_id} execution exception: {e}")


    
    def _execute_single_strategy(self, strategy: BackupStrategy) -> StrategyExecutionResult:
        """
        Execute single strategy

        Args:
            strategy: Backup strategy

        Returns:
            StrategyExecutionResult: Strategy execution result
        """
        start_time = datetime.now()

        try:
            self.logger.info(f"Starting strategy execution: {strategy.strategy_id}")
            self.logger.info(f"Database count: {len(strategy.databases)}, Storage count: {len(strategy.storages)}")

            all_backup_files = {}
            all_remote_paths = {}

            # Execute backup for each database configuration
            for db_config in strategy.databases:
                self.logger.info(f"Processing database: {db_config.database_type.value}@{db_config.host}")

                # Create database instance
                database = self._create_database_instance(db_config)

                # Test database connection
                if not database.test_connection():
                    raise Exception(f"Database connection failed: {db_config.host}")

                # Create backup for each database name
                for db_name in db_config.database_names:
                    backup_files, remote_paths = self._backup_database_to_storages(
                        database, db_name, strategy
                    )

                    # Merge results
                    backup_key = f"{db_config.host}_{db_name}"
                    all_backup_files[backup_key] = backup_files
                    all_remote_paths[backup_key] = remote_paths
            
            duration = (datetime.now() - start_time).total_seconds()
            
            return StrategyExecutionResult(
                strategy_id=strategy.strategy_id,
                success=True,
                backup_files=all_backup_files,
                remote_paths=all_remote_paths,
                duration_seconds=duration
            )
            
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            return StrategyExecutionResult(
                strategy_id=strategy.strategy_id,
                success=False,
                error_message=str(e),
                duration_seconds=duration
            )
    
    def _backup_database_to_storages(self, database: DatabaseInterface, db_name: str,
                                   strategy: BackupStrategy) -> tuple:
        """
        Backup single database to multiple storages

        Args:
            database: Database instance
            db_name: Database name
            strategy: Backup strategy

        Returns:
            tuple: (backup_files, remote_paths)
        """
        # Create temporary directory
        temp_dir = tempfile.mkdtemp(prefix=f"backup_{strategy.strategy_id}_{db_name}_")

        try:
            # Generate backup filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            database_type = database.config.database_type.value
            backup_filename = f"{timestamp}_{database_type}_{db_name}"

            if strategy.compression:
                backup_filename += ".gz"
            else:
                backup_filename += ".sql"

            backup_file_path = os.path.join(temp_dir, backup_filename)

            # Execute database backup
            self.logger.info(f"Backing up database {db_name} to {backup_file_path}")
            backup_result = database.create_single_database_backup(db_name, backup_file_path)

            if not backup_result.success:
                raise Exception(f"Database backup failed: {backup_result.error_message}")

            # Validate backup file
            if strategy.verify_backup and not database.validate_backup(backup_file_path):
                raise Exception(f"Backup file validation failed: {backup_file_path}")

            backup_files = []
            remote_paths = []

            # Upload to all storages
            for storage_config in strategy.storages:
                self.logger.info(f"Uploading to storage: {storage_config.storage_type.value}/{storage_config.bucket}")

                # Create storage instance
                storage = self._create_storage_instance(storage_config)

                # Test storage connection
                if not storage.test_connection():
                    raise Exception(f"Storage connection failed: {storage_config.bucket}")

                # Generate remote path
                prefix = storage_config.prefix or ""
                # 规范化 prefix，移除前后的斜杠
                prefix = prefix.strip("/")
                if prefix:
                    remote_path = f"{prefix}/{backup_filename}"
                else:
                    remote_path = backup_filename
                self.logger.debug(f"Storage config prefix: '{storage_config.prefix}', normalized prefix: '{prefix}', final remote path: '{remote_path}'")

                # Prepare metadata
                metadata = {
                    "strategy_id": strategy.strategy_id,
                    "backup_time": datetime.now().isoformat(),
                    "database_type": database.config.database_type.value,
                    "database_name": db_name,
                    "compression": str(strategy.compression)
                }

                # Execute upload
                upload_result = storage.upload_file(backup_file_path, remote_path, metadata)

                if not upload_result.success:
                    raise Exception(f"Upload failed: {upload_result.error_message}")

                backup_files.append(backup_file_path)
                remote_paths.append(remote_path)

                self.logger.info(f"Upload successful: {remote_path}")

                # Cleanup old backups
                if strategy.retention_days > 0:
                    try:
                        deleted_files = storage.cleanup_old_files(
                            strategy.retention_days,
                            storage_config.prefix
                        )
                        if deleted_files:
                            self.logger.info(f"Cleaned up {len(deleted_files)} old backup files")
                    except Exception as e:
                        self.logger.warning(f"Old backup cleanup failed: {e}")

            return backup_files, remote_paths

        finally:
            # Cleanup temporary files
            try:
                import shutil
                shutil.rmtree(temp_dir)
            except Exception as e:
                self.logger.warning(f"Temporary directory cleanup failed: {e}")
    
    def _create_database_instance(self, db_config: DatabaseConfig) -> DatabaseInterface:
        """Create database instance"""
        config_dict = {
            'host': db_config.host,
            'port': db_config.port,
            'username': db_config.username,
            'password': db_config.password,
            'database_names': db_config.database_names,
            'connection_timeout': db_config.connection_timeout,
            'backup_options': db_config.backup_options or {}
        }
        return create_database(db_config.database_type, config_dict)

    def _create_storage_instance(self, storage_config: StorageConfig) -> StorageInterface:
        """Create storage instance"""
        config_dict = {
            'endpoint': storage_config.endpoint,
            'access_key': storage_config.access_key,
            'secret_key': storage_config.secret_key,
            'bucket': storage_config.bucket,
            'region': storage_config.region,
            'prefix': storage_config.prefix,
            'storage_options': storage_config.storage_options or {}
        }
        return create_storage(storage_config.storage_type, config_dict)
