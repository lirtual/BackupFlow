"""
PostgreSQL Database Backup Implementation

Uses pg_dump tool for backup
"""

import os
import subprocess
import tempfile
import time
import gzip
from typing import Dict, Any, List, Optional

from ..interfaces.database_interface import DatabaseInterface, DatabaseConfig, BackupResult
from ..core.logger import LoggerMixin


class PostgreSQLDatabase(DatabaseInterface, LoggerMixin):
    """
    PostgreSQL Database Backup Implementation

    Uses pg_dump tool for backup
    """

    def __init__(self, config: DatabaseConfig):
        """Initialize PostgreSQL database connection"""
        super().__init__(config)
        self.logger.info(f"Initializing PostgreSQL database connection: {config.host}:{config.port}")

        # Verify required tools
        self._check_required_tools()

    def _check_required_tools(self):
        """Check if required tools are available"""
        try:
            subprocess.run(['pg_dump', '--version'],
                         capture_output=True, check=True, timeout=10)
            self.logger.debug("pg_dump tool check passed")
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            raise RuntimeError("pg_dump tool not available, please ensure PostgreSQL client is installed")

        try:
            subprocess.run(['psql', '--version'],
                         capture_output=True, check=True, timeout=10)
            self.logger.debug("psql tool check passed")
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            raise RuntimeError("psql tool not available, please ensure PostgreSQL client is installed")
    
    def test_connection(self) -> bool:
        """Test database connection"""
        self.logger.info("Testing PostgreSQL database connection...")

        try:
            # Set environment variables
            env = self._get_pg_env()

            # Use the first database name from configuration for connection test
            # If no database names specified, try 'postgres' as fallback
            test_database = self.config.database_names[0] if self.config.database_names else 'postgres'

            # Test connection
            cmd = [
                'psql',
                '-h', self.config.host,
                '-p', str(self.config.port),
                '-U', self.config.username,
                '-d', test_database,
                '-c', 'SELECT 1',
                '--quiet'
            ]

            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=self.config.connection_timeout
            )

            if result.returncode == 0:
                self.logger.info("PostgreSQL database connection test successful")
                return True
            else:
                self.logger.error(f"PostgreSQL connection test failed: {result.stderr}")
                return False

        except Exception as e:
            self.logger.error(f"PostgreSQL connection test exception: {e}")
            return False
    
    def create_backup(self, output_path: str) -> BackupResult:
        """Create PostgreSQL database backup"""
        self.logger.info(f"Starting PostgreSQL backup creation: {output_path}")
        start_time = time.time()

        try:
            # Set environment variables
            env = self._get_pg_env()

            # Build pg_dump command
            cmd = self._build_backup_command()

            self.logger.debug(f"Executing backup command: {' '.join(cmd[:-1])} [password hidden]")

            # Execute backup
            if output_path.endswith('.gz'):
                # Compressed backup
                self._create_compressed_backup(cmd, output_path, env)
            else:
                # Uncompressed backup
                self._create_uncompressed_backup(cmd, output_path, env)

            # Check backup file
            if not os.path.exists(output_path):
                raise Exception("Backup file was not created")

            backup_size = os.path.getsize(output_path)
            duration = time.time() - start_time

            self.logger.info(f"PostgreSQL backup completed, file size: {backup_size} bytes, duration: {duration:.2f} seconds")

            return BackupResult(
                success=True,
                backup_file_path=output_path,
                backup_size=backup_size,
                duration_seconds=duration,
                metadata={
                    'database_type': 'postgresql',
                    'database_names': self.config.database_names,
                    'compressed': output_path.endswith('.gz')
                }
            )

        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"PostgreSQL backup failed: {e}"
            self.logger.error(error_msg)

            return BackupResult(
                success=False,
                duration_seconds=duration,
                error_message=error_msg
            )

    def create_single_database_backup(self, database_name: str, output_path: str) -> BackupResult:
        """Create single PostgreSQL database backup"""
        self.logger.info(f"Starting PostgreSQL database {database_name} backup creation: {output_path}")
        start_time = time.time()

        try:
            # Set environment variables
            env = self._get_pg_env()

            # Build pg_dump command (single database)
            cmd = self._build_single_database_backup_command(database_name)

            self.logger.debug(f"Executing backup command: {' '.join(cmd[:-1])} [password hidden]")

            # Execute backup
            if output_path.endswith('.gz'):
                # Compressed backup
                self._create_compressed_backup(cmd, output_path, env)
            else:
                # Uncompressed backup
                self._create_uncompressed_backup(cmd, output_path, env)

            # Check backup file
            if not os.path.exists(output_path):
                raise Exception("Backup file was not created")

            backup_size = os.path.getsize(output_path)
            duration = time.time() - start_time

            self.logger.info(f"PostgreSQL database {database_name} backup completed, file size: {backup_size} bytes, duration: {duration:.2f} seconds")

            return BackupResult(
                success=True,
                backup_file_path=output_path,
                backup_size=backup_size,
                duration_seconds=duration,
                metadata={
                    'database_type': 'postgresql',
                    'database_name': database_name,
                    'compressed': output_path.endswith('.gz')
                }
            )

        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"PostgreSQL database {database_name} backup failed: {e}"
            self.logger.error(error_msg)

            return BackupResult(
                success=False,
                duration_seconds=duration,
                error_message=error_msg
            )
    
    def _get_pg_env(self) -> Dict[str, str]:
        """Get PostgreSQL environment variables"""
        env = os.environ.copy()
        env['PGPASSWORD'] = self.config.password
        return env

    def _build_backup_command(self) -> List[str]:
        """Build pg_dump command"""
        cmd = [
            'pg_dump',
            '-h', self.config.host,
            '-p', str(self.config.port),
            '-U', self.config.username,
            '--verbose',
            '--clean',
            '--no-owner',
            '--no-privileges'
        ]

        # PostgreSQL supports multi-database backup using pg_dumpall or multiple pg_dump calls
        # Simplified handling here, assuming only backup the first database
        if self.config.database_names:
            cmd.extend(['-d', self.config.database_names[0]])

        # Add custom options
        if self.config.backup_options:
            for option, value in self.config.backup_options.items():
                if value is True:
                    cmd.append(f'--{option}')
                elif value is not False and value is not None:
                    cmd.append(f'--{option}={value}')

        return cmd

    def _build_single_database_backup_command(self, database_name: str) -> List[str]:
        """Build pg_dump command for single database"""
        cmd = [
            'pg_dump',
            '-h', self.config.host,
            '-p', str(self.config.port),
            '-U', self.config.username,
            '--verbose',
            '--clean',
            '--no-owner',
            '--no-privileges',
            '-d', database_name  # Specify database to backup
        ]

        # Add custom options
        if self.config.backup_options:
            for option, value in self.config.backup_options.items():
                if value is True:
                    cmd.append(f'--{option}')
                elif value is not False and value is not None:
                    cmd.append(f'--{option}={value}')

        return cmd
    
    def _create_compressed_backup(self, cmd: List[str], output_path: str, env: Dict[str, str]):
        """Create compressed backup"""
        # Execute pg_dump and pipe to gzip
        pg_dump_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            text=False
        )

        with open(output_path, 'wb') as f:
            with gzip.GzipFile(fileobj=f, mode='wb') as gz_file:
                while True:
                    chunk = pg_dump_process.stdout.read(8192)
                    if not chunk:
                        break
                    gz_file.write(chunk)

        # Wait for process to complete
        pg_dump_process.wait()

        if pg_dump_process.returncode != 0:
            stderr_output = pg_dump_process.stderr.read().decode('utf-8')
            raise Exception(f"pg_dump execution failed: {stderr_output}")

    def _create_uncompressed_backup(self, cmd: List[str], output_path: str, env: Dict[str, str]):
        """Create uncompressed backup"""
        with open(output_path, 'w', encoding='utf-8') as f:
            result = subprocess.run(
                cmd,
                stdout=f,
                stderr=subprocess.PIPE,
                env=env,
                text=True
            )

        if result.returncode != 0:
            raise Exception(f"pg_dump execution failed: {result.stderr}")

    def validate_backup(self, backup_path: str) -> bool:
        """Validate backup file integrity"""
        self.logger.info(f"Validating PostgreSQL backup file: {backup_path}")

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

                    if 'pg_dump' in line.lower() or 'postgresql' in line.lower():
                        found_dump_header = True
                        break

                if not found_dump_header:
                    self.logger.error("Backup file format incorrect, pg_dump identifier not found")
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

                    if 'pg_dump' in line.lower() or 'postgresql' in line.lower():
                        found_dump_header = True
                        break

                if not found_dump_header:
                    self.logger.error("Backup file format incorrect, pg_dump identifier not found")
                    return False

            self.logger.info("Uncompressed backup file validation passed")
            return True

        except Exception as e:
            self.logger.error(f"Uncompressed backup file validation failed: {e}")
            return False

    def get_database_info(self) -> Dict[str, Any]:
        """Get database information"""
        self.logger.debug("Getting PostgreSQL database information")

        try:
            env = self._get_pg_env()

            info = {
                'database_type': 'postgresql',
                'host': self.config.host,
                'port': self.config.port,
                'database_names': self.config.database_names,
                'version': self._get_postgresql_version(env),
                'total_size': self._get_databases_size(env)
            }

            return info

        except Exception as e:
            self.logger.warning(f"Failed to get database information: {e}")
            return {
                'database_type': 'postgresql',
                'host': self.config.host,
                'port': self.config.port,
                'database_names': self.config.database_names,
                'error': str(e)
            }

    def _get_postgresql_version(self, env: Dict[str, str]) -> Optional[str]:
        """Get PostgreSQL version"""
        try:
            # Use the first database name from configuration
            test_database = self.config.database_names[0] if self.config.database_names else 'postgres'

            cmd = [
                'psql',
                '-h', self.config.host,
                '-p', str(self.config.port),
                '-U', self.config.username,
                '-d', test_database,
                '-c', 'SELECT version()',
                '--tuples-only',
                '--quiet'
            ]

            result = subprocess.run(
                cmd,
                env=env,
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

    def _get_databases_size(self, env: Dict[str, str]) -> Optional[int]:
        """Get total database size (bytes)"""
        try:
            total_size = 0

            for db_name in self.config.database_names:
                cmd = [
                    'psql',
                    '-h', self.config.host,
                    '-p', str(self.config.port),
                    '-U', self.config.username,
                    '-d', db_name,
                    '-c', "SELECT pg_database_size(current_database())",
                    '--tuples-only',
                    '--quiet'
                ]

                result = subprocess.run(
                    cmd,
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=30
                )

                if result.returncode == 0:
                    size_str = result.stdout.strip()
                    if size_str and size_str.isdigit():
                        total_size += int(size_str)

            return total_size if total_size > 0 else None

        except Exception:
            return None

    def get_backup_command(self) -> List[str]:
        """Get backup command (for debugging and logging)"""
        # Return command without password
        cmd = [
            'pg_dump',
            '-h', self.config.host,
            '-p', str(self.config.port),
            '-U', self.config.username,
            '--verbose',
            '--clean',
            '--no-owner',
            '--no-privileges'
        ]

        if self.config.database_names:
            cmd.extend(['-d', self.config.database_names[0]])

        return cmd
