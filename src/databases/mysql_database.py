"""
MySQL Database Backup Implementation

Converts existing shell script logic to Python implementation
"""

import os
import subprocess
import tempfile
import time
import gzip
from typing import Dict, Any, List, Optional

from ..interfaces.database_interface import DatabaseInterface, DatabaseConfig, BackupResult
from ..core.logger import LoggerMixin


class MySQLDatabase(DatabaseInterface, LoggerMixin):
    """
    MySQL Database Backup Implementation

    Uses mysqldump tool for backup
    """

    def __init__(self, config: DatabaseConfig):
        """Initialize MySQL database connection"""
        super().__init__(config)
        self.logger.info(f"Initializing MySQL database connection: {config.host}:{config.port}")

        # Verify required tools
        self._check_required_tools()

    def _check_required_tools(self):
        """Check if required tools are available"""
        try:
            subprocess.run(['mysqldump', '--version'],
                         capture_output=True, check=True, timeout=10)
            self.logger.debug("mysqldump tool check passed")
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            raise RuntimeError("mysqldump tool not available, please ensure MySQL client is installed")

        try:
            subprocess.run(['mysql', '--version'],
                         capture_output=True, check=True, timeout=10)
            self.logger.debug("mysql tool check passed")
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            raise RuntimeError("mysql tool not available, please ensure MySQL client is installed")
    
    def test_connection(self) -> bool:
        """Test database connection"""
        self.logger.info("Testing MySQL database connection...")

        try:
            # Create temporary configuration file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.cnf', delete=False) as f:
                f.write(f"""[client]
host={self.config.host}
port={self.config.port}
user={self.config.username}
password={self.config.password}
""")
                config_file = f.name

            try:
                # Set configuration file permissions
                os.chmod(config_file, 0o600)

                # Test connection
                cmd = [
                    'mysql',
                    f'--defaults-file={config_file}',
                    '--connect-timeout=10',
                    '--execute=SELECT 1'
                ]

                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=self.config.connection_timeout
                )

                if result.returncode == 0:
                    self.logger.info("MySQL database connection test successful")
                    return True
                else:
                    self.logger.error(f"MySQL connection test failed: {result.stderr}")
                    return False

            finally:
                # Cleanup temporary configuration file
                try:
                    os.unlink(config_file)
                except Exception:
                    pass

        except Exception as e:
            self.logger.error(f"MySQL connection test exception: {e}")
            return False
    
    def create_backup(self, output_path: str) -> BackupResult:
        """Create MySQL database backup"""
        self.logger.info(f"Starting MySQL backup creation: {output_path}")
        start_time = time.time()

        try:
            # Create temporary configuration file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.cnf', delete=False) as f:
                f.write(f"""[client]
host={self.config.host}
port={self.config.port}
user={self.config.username}
password={self.config.password}
""")
                config_file = f.name

            try:
                # Set configuration file permissions
                os.chmod(config_file, 0o600)

                # Build mysqldump command
                cmd = self._build_backup_command(config_file)

                self.logger.debug(f"Executing backup command: {' '.join(cmd[:-1])} [password hidden]")

                # Execute backup
                if output_path.endswith('.gz'):
                    # Compressed backup
                    self._create_compressed_backup(cmd, output_path)
                else:
                    # Uncompressed backup
                    self._create_uncompressed_backup(cmd, output_path)

                # Check backup file
                if not os.path.exists(output_path):
                    raise Exception("Backup file was not created")

                backup_size = os.path.getsize(output_path)
                duration = time.time() - start_time

                self.logger.info(f"MySQL backup completed, file size: {backup_size} bytes, duration: {duration:.2f} seconds")

                return BackupResult(
                    success=True,
                    backup_file_path=output_path,
                    backup_size=backup_size,
                    duration_seconds=duration,
                    metadata={
                        'database_type': 'mysql',
                        'database_names': self.config.database_names,
                        'compressed': output_path.endswith('.gz')
                    }
                )

            finally:
                # Cleanup temporary configuration file
                try:
                    os.unlink(config_file)
                except Exception:
                    pass

        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"MySQL backup failed: {e}"
            self.logger.error(error_msg)

            return BackupResult(
                success=False,
                duration_seconds=duration,
                error_message=error_msg
            )

    def create_single_database_backup(self, database_name: str, output_path: str) -> BackupResult:
        """Create single MySQL database backup"""
        self.logger.info(f"Starting MySQL database {database_name} backup creation: {output_path}")
        start_time = time.time()

        try:
            # Create temporary configuration file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.cnf', delete=False) as f:
                f.write(f"""[client]
host={self.config.host}
port={self.config.port}
user={self.config.username}
password={self.config.password}
""")
                config_file = f.name

            try:
                # Set configuration file permissions
                os.chmod(config_file, 0o600)

                # Build mysqldump command (single database)
                cmd = self._build_single_database_backup_command(config_file, database_name)

                self.logger.debug(f"Executing backup command: {' '.join(cmd[:-1])} [password hidden]")

                # Execute backup
                if output_path.endswith('.gz'):
                    # Compressed backup
                    self._create_compressed_backup(cmd, output_path)
                else:
                    # Uncompressed backup
                    self._create_uncompressed_backup(cmd, output_path)

                # Check backup file
                if not os.path.exists(output_path):
                    raise Exception("Backup file was not created")

                backup_size = os.path.getsize(output_path)
                duration = time.time() - start_time

                self.logger.info(f"MySQL database {database_name} backup completed, file size: {backup_size} bytes, duration: {duration:.2f} seconds")

                return BackupResult(
                    success=True,
                    backup_file_path=output_path,
                    backup_size=backup_size,
                    duration_seconds=duration,
                    metadata={
                        'database_type': 'mysql',
                        'database_name': database_name,
                        'compressed': output_path.endswith('.gz')
                    }
                )

            finally:
                # Cleanup temporary configuration file
                try:
                    os.unlink(config_file)
                except Exception:
                    pass

        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"MySQL database {database_name} backup failed: {e}"
            self.logger.error(error_msg)

            return BackupResult(
                success=False,
                duration_seconds=duration,
                error_message=error_msg
            )
    
    def _build_backup_command(self, config_file: str) -> List[str]:
        """Build mysqldump command"""
        cmd = [
            'mysqldump',
            f'--defaults-file={config_file}',
            '--max-allowed-packet=1024M',
            '--quick',
            '--single-transaction',
            '--set-gtid-purged=OFF',
            '--triggers',
            '--routines',
            '--events',
            '--databases'
        ]

        # Add database names
        cmd.extend(self.config.database_names)

        # Add custom options
        if self.config.backup_options:
            for option, value in self.config.backup_options.items():
                if value is True:
                    cmd.append(f'--{option}')
                elif value is not False and value is not None:
                    cmd.append(f'--{option}={value}')

        return cmd

    def _build_single_database_backup_command(self, config_file: str, database_name: str) -> List[str]:
        """Build mysqldump command for single database"""
        cmd = [
            'mysqldump',
            f'--defaults-file={config_file}',
            '--max-allowed-packet=1024M',
            '--quick',
            '--single-transaction',
            '--set-gtid-purged=OFF',
            '--triggers',
            '--routines',
            '--events',
            database_name  # Only backup specified database
        ]

        # Add custom options
        if self.config.backup_options:
            for option, value in self.config.backup_options.items():
                if value is True:
                    cmd.append(f'--{option}')
                elif value is not False and value is not None:
                    cmd.append(f'--{option}={value}')

        return cmd
    
    def _create_compressed_backup(self, cmd: List[str], output_path: str):
        """Create compressed backup"""
        # Execute mysqldump and pipe to gzip
        mysqldump_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=False
        )

        with open(output_path, 'wb') as f:
            with gzip.GzipFile(fileobj=f, mode='wb') as gz_file:
                while True:
                    chunk = mysqldump_process.stdout.read(8192)
                    if not chunk:
                        break
                    gz_file.write(chunk)

        # Wait for process to complete
        mysqldump_process.wait()

        if mysqldump_process.returncode != 0:
            stderr_output = mysqldump_process.stderr.read().decode('utf-8')
            raise Exception(f"mysqldump execution failed: {stderr_output}")

    def _create_uncompressed_backup(self, cmd: List[str], output_path: str):
        """Create uncompressed backup"""
        with open(output_path, 'w', encoding='utf-8') as f:
            result = subprocess.run(
                cmd,
                stdout=f,
                stderr=subprocess.PIPE,
                text=True
            )

        if result.returncode != 0:
            raise Exception(f"mysqldump execution failed: {result.stderr}")

    def validate_backup(self, backup_path: str) -> bool:
        """Validate backup file integrity"""
        self.logger.info(f"Validating MySQL backup file: {backup_path}")

        try:
            if not os.path.exists(backup_path):
                self.logger.error("Backup file does not exist")
                return False

            # Check file size
            file_size = os.path.getsize(backup_path)
            if file_size == 0:
                self.logger.error("Backup file is empty")
                return False

            # Check file content
            if backup_path.endswith('.gz'):
                return self._validate_compressed_backup(backup_path)
            else:
                return self._validate_uncompressed_backup(backup_path)

        except Exception as e:
            self.logger.error(f"Backup file validation exception: {e}")
            return False

    def _validate_compressed_backup(self, backup_path: str) -> bool:
        """Validate compressed backup file"""
        try:
            with gzip.open(backup_path, 'rt', encoding='utf-8') as f:
                # Read first few lines to check format
                lines_read = 0
                found_dump_header = False

                for line in f:
                    lines_read += 1
                    if lines_read > 50:  # Only check first 50 lines
                        break

                    if 'mysqldump' in line.lower() or 'mysql dump' in line.lower():
                        found_dump_header = True
                        break

                if not found_dump_header:
                    self.logger.error("Backup file format incorrect, mysqldump identifier not found")
                    return False

            self.logger.info("Compressed backup file validation passed")
            return True

        except gzip.BadGzipFile:
            self.logger.error("Backup file is not a valid gzip file")
            return False
        except Exception as e:
            self.logger.error(f"Compressed backup file validation failed: {e}")
            return False

    def _validate_uncompressed_backup(self, backup_path: str) -> bool:
        """Validate uncompressed backup file"""
        try:
            with open(backup_path, 'r', encoding='utf-8') as f:
                # Read first few lines to check format
                lines_read = 0
                found_dump_header = False

                for line in f:
                    lines_read += 1
                    if lines_read > 50:  # Only check first 50 lines
                        break

                    if 'mysqldump' in line.lower() or 'mysql dump' in line.lower():
                        found_dump_header = True
                        break

                if not found_dump_header:
                    self.logger.error("Backup file format incorrect, mysqldump identifier not found")
                    return False

            self.logger.info("Uncompressed backup file validation passed")
            return True

        except Exception as e:
            self.logger.error(f"Uncompressed backup file validation failed: {e}")
            return False

    def get_database_info(self) -> Dict[str, Any]:
        """Get database information"""
        self.logger.debug("Getting MySQL database information")

        try:
            # Create temporary configuration file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.cnf', delete=False) as f:
                f.write(f"""[client]
host={self.config.host}
port={self.config.port}
user={self.config.username}
password={self.config.password}
""")
                config_file = f.name

            try:
                # Set configuration file permissions
                os.chmod(config_file, 0o600)

                info = {
                    'database_type': 'mysql',
                    'host': self.config.host,
                    'port': self.config.port,
                    'database_names': self.config.database_names,
                    'version': self._get_mysql_version(config_file),
                    'total_size': self._get_databases_size(config_file)
                }

                return info

            finally:
                # Cleanup temporary configuration file
                try:
                    os.unlink(config_file)
                except Exception:
                    pass

        except Exception as e:
            self.logger.warning(f"Failed to get database information: {e}")
            return {
                'database_type': 'mysql',
                'host': self.config.host,
                'port': self.config.port,
                'database_names': self.config.database_names,
                'error': str(e)
            }

    def _get_mysql_version(self, config_file: str) -> Optional[str]:
        """Get MySQL version"""
        try:
            cmd = [
                'mysql',
                f'--defaults-file={config_file}',
                '--execute=SELECT VERSION()',
                '--batch',
                '--skip-column-names'
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                return result.stdout.strip()
            else:
                return None

        except Exception:
            return None

    def _get_databases_size(self, config_file: str) -> Optional[int]:
        """Get total database size (bytes)"""
        try:
            # Build query statement
            db_list = "', '".join(self.config.database_names)
            query = f"""
            SELECT SUM(data_length + index_length) as total_size
            FROM information_schema.tables
            WHERE table_schema IN ('{db_list}')
            """

            cmd = [
                'mysql',
                f'--defaults-file={config_file}',
                f'--execute={query}',
                '--batch',
                '--skip-column-names'
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                size_str = result.stdout.strip()
                return int(size_str) if size_str and size_str != 'NULL' else 0
            else:
                return None

        except Exception:
            return None

    def get_backup_command(self) -> List[str]:
        """Get backup command (for debugging and logging)"""
        # Return command without password
        cmd = [
            'mysqldump',
            f'--host={self.config.host}',
            f'--port={self.config.port}',
            f'--user={self.config.username}',
            '--password=***',
            '--max-allowed-packet=1024M',
            '--quick',
            '--single-transaction',
            '--set-gtid-purged=OFF',
            '--triggers',
            '--routines',
            '--events',
            '--databases'
        ]

        cmd.extend(self.config.database_names)
        return cmd
