"""
Database Client Checker

Intelligently check and manage the availability of various database client tools
"""

import subprocess
import sys
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum

from ..interfaces.config_interface import DatabaseType
from .logger import LoggerMixin


class ClientType(Enum):
    """Client type"""
    SYSTEM = "system"  # System-installed client tools
    PYTHON = "python"  # Python library clients


class DatabaseClientChecker(LoggerMixin):
    """Database client checker"""

    def __init__(self):
        self.available_clients = {}
        self.logger.info("Database client checker initialized")
    
    def check_all_required_clients(self, database_types: List[DatabaseType]) -> Dict[DatabaseType, ClientType]:
        """
        Check all required database clients

        Args:
            database_types: List of required database types

        Returns:
            Dict[DatabaseType, ClientType]: Available client type for each database type

        Raises:
            RuntimeError: If no available client for certain database type
        """
        result = {}
        missing_clients = []

        for db_type in set(database_types):  # Remove duplicates
            client_type = self.check_database_client(db_type)
            if client_type:
                result[db_type] = client_type
                self.logger.info(f"{db_type.value} database client available: {client_type.value}")
            else:
                missing_clients.append(db_type.value)

        if missing_clients:
            error_msg = f"Missing client tools for the following database types: {', '.join(missing_clients)}"
            self.logger.error(error_msg)
            self.logger.error("Please install corresponding system client tools or Python dependency packages")
            raise RuntimeError(error_msg)

        return result
    
    def check_database_client(self, db_type: DatabaseType) -> Optional[ClientType]:
        """
        Check client availability for a single database type

        Args:
            db_type: Database type

        Returns:
            Optional[ClientType]: Available client type, None if none available
        """
        if db_type == DatabaseType.MYSQL:
            return self._check_mysql_client()
        elif db_type == DatabaseType.POSTGRESQL:
            return self._check_postgresql_client()
        else:
            self.logger.warning(f"Unsupported database type: {db_type}")
            return None
    
    def _check_mysql_client(self) -> Optional[ClientType]:
        """Check MySQL client"""
        # Check system client first
        if self._check_system_mysql():
            return ClientType.SYSTEM

        # Check Python client
        if self._check_python_mysql():
            return ClientType.PYTHON

        return None

    def _check_postgresql_client(self) -> Optional[ClientType]:
        """Check PostgreSQL client"""
        # Check system client first
        if self._check_system_postgresql():
            return ClientType.SYSTEM

        # Check Python client
        if self._check_python_postgresql():
            return ClientType.PYTHON

        return None
    
    def _check_system_mysql(self) -> bool:
        """Check system MySQL client"""
        try:
            # Check mysqldump
            subprocess.run(['mysqldump', '--version'],
                         capture_output=True, check=True, timeout=5)

            # Check mysql
            subprocess.run(['mysql', '--version'],
                         capture_output=True, check=True, timeout=5)

            self.logger.debug("System MySQL client tools check passed")
            return True

        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            self.logger.debug("System MySQL client tools not available")
            return False

    def _check_system_postgresql(self) -> bool:
        """Check system PostgreSQL client"""
        try:
            # Check pg_dump
            subprocess.run(['pg_dump', '--version'],
                         capture_output=True, check=True, timeout=5)

            # Check psql
            subprocess.run(['psql', '--version'],
                         capture_output=True, check=True, timeout=5)

            self.logger.debug("System PostgreSQL client tools check passed")
            return True

        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            self.logger.debug("System PostgreSQL client tools not available")
            return False
    
    def _check_python_mysql(self) -> bool:
        """Check Python MySQL client"""
        try:
            import pymysql
            self.logger.debug("Python MySQL client (PyMySQL) available")
            return True
        except ImportError:
            self.logger.debug("Python MySQL client (PyMySQL) not available")
            return False

    def _check_python_postgresql(self) -> bool:
        """Check Python PostgreSQL client"""
        try:
            import psycopg2
            self.logger.debug("Python PostgreSQL client (psycopg2) available")
            return True
        except ImportError:
            self.logger.debug("Python PostgreSQL client (psycopg2) not available")
            return False
    
    def get_installation_instructions(self, db_type: DatabaseType) -> Dict[str, str]:
        """
        Get client installation instructions

        Args:
            db_type: Database type

        Returns:
            Dict[str, str]: Installation instructions, including system and Python methods
        """
        if db_type == DatabaseType.MYSQL:
            return {
                "system": {
                    "ubuntu/debian": "sudo apt-get install -y mysql-client",
                    "centos/rhel": "sudo yum install -y mysql",
                    "macos": "brew install mysql-client",
                    "windows": "Download and install MySQL Community Server"
                },
                "python": "pip install PyMySQL>=1.0.0"
            }
        elif db_type == DatabaseType.POSTGRESQL:
            return {
                "system": {
                    "ubuntu/debian": "sudo apt-get install -y postgresql-client",
                    "centos/rhel": "sudo yum install -y postgresql",
                    "macos": "brew install postgresql",
                    "windows": "Download and install PostgreSQL"
                },
                "python": "pip install psycopg2-binary>=2.9.0"
            }
        else:
            return {}
    
    def get_client_summary(self) -> Dict[str, Any]:
        """Get client check summary"""
        summary = {
            "mysql": {
                "system_available": self._check_system_mysql(),
                "python_available": self._check_python_mysql()
            },
            "postgresql": {
                "system_available": self._check_system_postgresql(),
                "python_available": self._check_python_postgresql()
            }
        }

        return summary

    def suggest_installation_for_strategy(self, database_types: List[DatabaseType]) -> str:
        """
        Suggest installation plan for strategy

        Args:
            database_types: Database types used in strategy

        Returns:
            str: Installation suggestions
        """
        unique_types = list(set(database_types))
        suggestions = []

        suggestions.append("=== Database Client Installation Suggestions ===")
        suggestions.append("")

        for db_type in unique_types:
            client_type = self.check_database_client(db_type)
            if not client_type:
                instructions = self.get_installation_instructions(db_type)
                suggestions.append(f"❌ {db_type.value.upper()} client missing")
                suggestions.append("Recommended installation methods:")
                suggestions.append(f"  Python method: {instructions.get('python', 'N/A')}")
                suggestions.append("  System method:")
                for os_name, cmd in instructions.get('system', {}).items():
                    suggestions.append(f"    {os_name}: {cmd}")
                suggestions.append("")
            else:
                suggestions.append(f"✅ {db_type.value.upper()} client available ({client_type.value})")
        
        if all(self.check_database_client(dt) for dt in unique_types):
            suggestions.append("")
            suggestions.append("🎉 All required database clients are available!")
        
        return "\n".join(suggestions)
