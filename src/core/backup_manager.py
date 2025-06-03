"""
Backup Manager

Coordinates database and storage components to implement complete backup workflow
"""

import os
import tempfile
import time
from datetime import datetime
from typing import Optional, Dict, Any
from dataclasses import dataclass

from ..interfaces.config_interface import BackupConfig
from ..interfaces.database_interface import DatabaseInterface
from ..interfaces.storage_interface import StorageInterface
from .logger import LoggerMixin


@dataclass
class BackupSession:
    """Backup session information"""
    session_id: str
    start_time: datetime
    config: BackupConfig
    database: DatabaseInterface
    storage: StorageInterface
    temp_dir: Optional[str] = None
    backup_files: Optional[Dict[str, str]] = None  # database name -> local file path
    remote_paths: Optional[Dict[str, str]] = None  # database name -> remote file path
    success: bool = False
    error_message: Optional[str] = None
    duration_seconds: Optional[float] = None


class BackupManager(LoggerMixin):
    """
    Backup Manager

    Responsible for coordinating the complete process of database backup and storage upload
    """

    def __init__(self, config: BackupConfig, database: DatabaseInterface,
                 storage: StorageInterface):
        """
        Initialize backup manager

        Args:
            config: Backup configuration
            database: Database interface instance
            storage: Storage interface instance
        """
        self.config = config
        self.database = database
        self.storage = storage
        self.logger.info("Backup manager initialization completed")
    
    def create_backup(self) -> BackupSession:
        """
        Execute complete backup process

        Returns:
            BackupSession: Backup session information
        """
        session_id = f"backup_{int(time.time())}"
        session = BackupSession(
            session_id=session_id,
            start_time=datetime.now(),
            config=self.config,
            database=self.database,
            storage=self.storage,
            backup_files={},
            remote_paths={}
        )
        
        self.logger.info(f"Starting backup session: {session_id}")

        try:
            # 1. Test connections
            self._test_connections(session)

            # 2. Create temporary directory
            self._setup_temp_directory(session)

            # 3. Perform database backup
            self._perform_database_backup(session)

            # 4. Verify backup files
            if self.config.verify_backup:
                self._verify_backup(session)

            # 5. Upload to storage
            self._upload_backup(session)

            # 6. Cleanup old backups
            self._cleanup_old_backups(session)

            # 7. Cleanup temporary files
            self._cleanup_temp_files(session)

            session.success = True
            session.duration_seconds = (datetime.now() - session.start_time).total_seconds()

            self.logger.info(f"Backup session completed: {session_id}, duration: {session.duration_seconds:.2f} seconds")

        except Exception as e:
            session.success = False
            session.error_message = str(e)
            session.duration_seconds = (datetime.now() - session.start_time).total_seconds()

            self.logger.error(f"Backup session failed: {session_id}, error: {e}")

            # Cleanup temporary files
            try:
                self._cleanup_temp_files(session)
            except Exception as cleanup_error:
                self.logger.warning(f"Failed to cleanup temporary files: {cleanup_error}")
        
        return session
    
    def _test_connections(self, session: BackupSession):
        """Test database and storage connections"""
        self.logger.info("Testing database connection...")
        if not self.database.test_connection():
            raise Exception("Database connection test failed")

        self.logger.info("Testing storage connection...")
        if not self.storage.test_connection():
            raise Exception("Storage connection test failed")

        self.logger.info("Connection tests passed")

    def _setup_temp_directory(self, session: BackupSession):
        """Setup temporary directory"""
        session.temp_dir = tempfile.mkdtemp(prefix=f"backup_{session.session_id}_")
        self.logger.debug(f"Created temporary directory: {session.temp_dir}")

    def _perform_database_backup(self, session: BackupSession):
        """Perform database backup"""
        self.logger.info("Starting database backup...")

        # Get database names list
        database_names = self.database.config.database_names
        if not database_names:
            raise Exception("No databases specified for backup")

        timestamp = session.start_time.strftime("%Y%m%d_%H%M%S")

        # Create separate backup for each database
        for db_name in database_names:
            self.logger.info(f"Backing up database: {db_name}")

            # Generate backup filename: {timestamp}_{database_type}_{database_name}
            database_type = self.database.config.database_type.value
            backup_filename = f"{timestamp}_{database_type}_{db_name}.sql"

            if self.config.compression:
                backup_filename += ".gz"

            backup_file_path = os.path.join(session.temp_dir, backup_filename)

            # Execute single database backup
            backup_result = self.database.create_single_database_backup(db_name, backup_file_path)

            if not backup_result.success:
                raise Exception(f"Database {db_name} backup failed: {backup_result.error_message}")

            # Record backup file information
            session.backup_files[db_name] = backup_file_path

            self.logger.info(f"Database {db_name} backup completed: {backup_file_path}")
            self.logger.info(f"Backup file size: {backup_result.backup_size} bytes")

        self.logger.info(f"All database backups completed, total {len(database_names)} databases")
    
    def _verify_backup(self, session: BackupSession):
        """Verify backup files"""
        self.logger.info("Verifying backup files...")

        for db_name, backup_file_path in session.backup_files.items():
            self.logger.info(f"Verifying backup file for database {db_name}...")

            if not os.path.exists(backup_file_path):
                raise Exception(f"Backup file for database {db_name} does not exist: {backup_file_path}")

            if not self.database.validate_backup(backup_file_path):
                raise Exception(f"Backup file validation failed for database {db_name}: {backup_file_path}")

            self.logger.info(f"Backup file verification passed for database {db_name}")

        self.logger.info("All backup files verified successfully")

    def _upload_backup(self, session: BackupSession):
        """Upload backup to storage"""
        self.logger.info("Uploading backup files...")

        prefix = self.storage.config.prefix or ""
        # 规范化 prefix，移除前后的斜杠
        prefix = prefix.strip("/")

        for db_name, backup_file_path in session.backup_files.items():
            self.logger.info(f"Uploading backup file for database {db_name}...")

            # Generate remote path
            backup_filename = os.path.basename(backup_file_path)
            if prefix:
                remote_path = f"{prefix}/{backup_filename}"
            else:
                remote_path = backup_filename
            self.logger.debug(f"Storage config prefix: '{self.storage.config.prefix}', normalized prefix: '{prefix}', final remote path: '{remote_path}'")

            # Prepare metadata
            metadata = {
                "session_id": session.session_id,
                "backup_time": session.start_time.isoformat(),
                "database_type": session.config.database_type.value,
                "database_name": db_name,
                "compression": str(session.config.compression)
            }

            # Execute upload
            upload_result = self.storage.upload_file(
                backup_file_path,
                remote_path,
                metadata
            )

            if not upload_result.success:
                raise Exception(f"Backup upload failed for database {db_name}: {upload_result.error_message}")

            # Record remote path
            session.remote_paths[db_name] = remote_path

            self.logger.info(f"Backup upload completed for database {db_name}: {remote_path}")

        self.logger.info(f"All backup files uploaded successfully, total {len(session.backup_files)} files")
    
    def _cleanup_old_backups(self, session: BackupSession):
        """Cleanup old backups"""
        if self.config.retention_days > 0:
            self.logger.info(f"Cleaning up old backups older than {self.config.retention_days} days...")

            deleted_files = self.storage.cleanup_old_files(
                self.config.retention_days,
                self.storage.config.prefix
            )

            if deleted_files:
                self.logger.info(f"Deleted {len(deleted_files)} old backup files")
                for file_path in deleted_files:
                    self.logger.debug(f"Deleted: {file_path}")
            else:
                self.logger.info("No old backups to cleanup")

    def _cleanup_temp_files(self, session: BackupSession):
        """Cleanup temporary files"""
        if session.temp_dir and os.path.exists(session.temp_dir):
            try:
                import shutil
                shutil.rmtree(session.temp_dir)
                self.logger.debug(f"Cleaned up temporary directory: {session.temp_dir}")
            except Exception as e:
                self.logger.warning(f"Failed to cleanup temporary directory: {e}")

    def get_backup_info(self) -> Dict[str, Any]:
        """Get backup related information"""
        return {
            "database_info": self.database.get_database_info(),
            "storage_config": {
                "type": self.config.storage_type.value,
                "bucket": self.storage.config.bucket,
                "prefix": self.storage.config.prefix
            },
            "backup_config": {
                "retention_days": self.config.retention_days,
                "compression": self.config.compression,
                "verify_backup": self.config.verify_backup
            }
        }
