"""
URI Parser

Supports URI format configuration parsing for databases and storages
"""

import re
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse, parse_qs

from ..interfaces.config_interface import DatabaseType, StorageType, DatabaseConfig, StorageConfig
from .logger import LoggerMixin


class URIParseError(Exception):
    """URI parsing error"""
    pass


class DatabaseURIParser(LoggerMixin):
    """Database URI parser"""

    def parse_database_uri(self, uri: str) -> DatabaseConfig:
        """
        Parse database URI

        Format: mysql://user:password@host:port/database1,database2?param=value
        Or: mysql://user:password@host:port?databases=db1,db2&param=value

        Args:
            uri: Database URI string

        Returns:
            DatabaseConfig: Parsed database configuration

        Raises:
            URIParseError: URI format error
        """
        try:
            parsed = urlparse(uri)

            # Parse database type
            if parsed.scheme == 'mysql':
                db_type = DatabaseType.MYSQL
                default_port = 3306
            elif parsed.scheme in ['postgresql', 'postgres']:
                db_type = DatabaseType.POSTGRESQL
                default_port = 5432
            else:
                raise URIParseError(f"Unsupported database type: {parsed.scheme}")

            # Parse host and port
            host = parsed.hostname or 'localhost'
            port = parsed.port or default_port

            # Parse username and password
            username = parsed.username or ''
            password = parsed.password or ''

            # Parse database names
            database_names = []

            # Method 1: Parse from path /database1,database2
            if parsed.path and parsed.path != '/':
                path_dbs = parsed.path.lstrip('/').split(',')
                database_names.extend([db.strip() for db in path_dbs if db.strip()])
            
            # Method 2: Parse from query parameters ?databases=db1,db2
            if parsed.query:
                query_params = parse_qs(parsed.query)
                if 'databases' in query_params:
                    query_dbs = query_params['databases'][0].split(',')
                    database_names.extend([db.strip() for db in query_dbs if db.strip()])

            if not database_names:
                raise URIParseError("No database names specified in URI")

            # Parse other parameters
            connection_timeout = 30
            backup_options = {}
            
            if parsed.query:
                query_params = parse_qs(parsed.query)
                if 'timeout' in query_params:
                    connection_timeout = int(query_params['timeout'][0])
                
                # Other backup options
                for key, values in query_params.items():
                    if key not in ['databases', 'timeout']:
                        backup_options[key] = values[0] if len(values) == 1 else values
            
            return DatabaseConfig(
                database_type=db_type,
                host=host,
                port=port,
                username=username,
                password=password,
                database_names=database_names,
                connection_timeout=connection_timeout,
                backup_options=backup_options
            )
            
        except Exception as e:
            if isinstance(e, URIParseError):
                raise
            raise URIParseError(f"Database URI parsing failed: {e}")


class StorageURIParser(LoggerMixin):
    """Storage URI parser"""

    def parse_storage_uri(self, uri: str) -> StorageConfig:
        """
        Parse storage URI

        Format: r2://access_key:secret_key@account.r2.cloudflarestorage.com/bucket?prefix=backups/
        Or: s3://access_key:secret_key@region/bucket?prefix=backups/

        Args:
            uri: Storage URI string

        Returns:
            StorageConfig: Parsed storage configuration

        Raises:
            URIParseError: URI format error
        """
        try:
            parsed = urlparse(uri)
            
            # Parse storage type
            if parsed.scheme == 'r2':
                storage_type = StorageType.R2
            elif parsed.scheme == 's3':
                storage_type = StorageType.S3
            else:
                raise URIParseError(f"Unsupported storage type: {parsed.scheme}")

            # Parse access credentials
            access_key = parsed.username or ''
            secret_key = parsed.password or ''

            if not access_key or not secret_key:
                raise URIParseError("Missing access credentials in storage URI")

            # Parse hostname and path
            hostname = parsed.hostname or ''
            path = parsed.path.lstrip('/') if parsed.path else ''

            # Parse configuration based on storage type
            if storage_type == StorageType.R2:
                # R2 format: r2://key:secret@account.r2.cloudflarestorage.com/bucket
                if not hostname:
                    raise URIParseError("Missing endpoint in R2 URI")

                endpoint = f"https://{hostname}"
                bucket = path.split('/')[0] if path else ''
                region = "auto"

            elif storage_type == StorageType.S3:
                # S3 format: s3://key:secret@region/bucket or s3://key:secret@endpoint/bucket
                if not hostname:
                    raise URIParseError("Missing region or endpoint in S3 URI")

                bucket = path.split('/')[0] if path else ''

                # Check if it's a standard AWS region
                aws_regions = [
                    'us-east-1', 'us-east-2', 'us-west-1', 'us-west-2',
                    'eu-west-1', 'eu-west-2', 'eu-west-3', 'eu-central-1',
                    'ap-southeast-1', 'ap-southeast-2', 'ap-northeast-1'
                ]

                if hostname in aws_regions:
                    # Standard AWS region
                    region = hostname
                    endpoint = None
                else:
                    # Custom endpoint
                    region = "us-east-1"  # Default region
                    endpoint = f"https://{hostname}"

            if not bucket:
                raise URIParseError("Missing bucket name in storage URI")
            
            # Parse query parameters
            prefix = None
            storage_options = {}

            if parsed.query:
                query_params = parse_qs(parsed.query)
                self.logger.debug(f"Parsed query parameters: {query_params}")
                if 'prefix' in query_params and query_params['prefix']:
                    prefix = query_params['prefix'][0]
                    self.logger.debug(f"Found prefix parameter: {prefix}")
                elif 'prefix' in query_params:
                    # prefix 参数存在但为空
                    prefix = ""
                    self.logger.debug("Found empty prefix parameter")

                # Other storage options
                for key, values in query_params.items():
                    if key != 'prefix':
                        storage_options[key] = values[0] if len(values) == 1 else values
            
            return StorageConfig(
                storage_type=storage_type,
                endpoint=endpoint,
                access_key=access_key,
                secret_key=secret_key,
                bucket=bucket,
                region=region,
                prefix=prefix,
                storage_options=storage_options
            )
            
        except Exception as e:
            if isinstance(e, URIParseError):
                raise
            raise URIParseError(f"Storage URI parsing failed: {e}")


class LegacyFormatParser(LoggerMixin):
    """Legacy format parser"""

    def parse_legacy_storage_format(self, config_str: str) -> StorageConfig:
        """
        Parse legacy storage format

        Format: type:access_key:secret_key:bucket:region_or_endpoint:prefix

        Args:
            config_str: Legacy format configuration string

        Returns:
            StorageConfig: Parsed storage configuration
        """
        try:
            parts = config_str.split(':')
            if len(parts) < 4:
                raise URIParseError("Insufficient legacy format configuration items")

            storage_type_str = parts[0]
            access_key = parts[1]
            secret_key = parts[2]
            bucket = parts[3]
            region_or_endpoint = parts[4] if len(parts) > 4 else ''
            prefix = parts[5] if len(parts) > 5 else None

            # Parse storage type
            if storage_type_str == 'r2':
                storage_type = StorageType.R2
                endpoint = region_or_endpoint if region_or_endpoint.startswith('http') else None
                region = "auto"
            elif storage_type_str == 's3':
                storage_type = StorageType.S3
                if region_or_endpoint.startswith('http'):
                    endpoint = region_or_endpoint
                    region = "us-east-1"
                else:
                    endpoint = None
                    region = region_or_endpoint or "us-east-1"
            else:
                raise URIParseError(f"Unsupported storage type: {storage_type_str}")
            
            return StorageConfig(
                storage_type=storage_type,
                endpoint=endpoint,
                access_key=access_key,
                secret_key=secret_key,
                bucket=bucket,
                region=region,
                prefix=prefix
            )
            
        except Exception as e:
            if isinstance(e, URIParseError):
                raise
            raise URIParseError(f"Legacy format parsing failed: {e}")


class MultiConfigParser(LoggerMixin):
    """Multi-configuration parser"""
    
    def __init__(self):
        self.db_parser = DatabaseURIParser()
        self.storage_parser = StorageURIParser()
        self.legacy_parser = LegacyFormatParser()
    
    def parse_databases_config(self, config_str: str) -> List[DatabaseConfig]:
        """
        Parse multi-database configuration

        Args:
            config_str: Database configuration string, multiple URIs separated by |

        Returns:
            List[DatabaseConfig]: Database configuration list
        """
        databases = []

        if not config_str:
            return databases

        # Split multiple database URIs by |
        uri_list = [uri.strip() for uri in config_str.split('|') if uri.strip()]
        
        for uri in uri_list:
            try:
                db_config = self.db_parser.parse_database_uri(uri)
                databases.append(db_config)
                self.logger.debug(f"Database URI parsed successfully: {uri}")
            except Exception as e:
                self.logger.error(f"Failed to parse database URI: {uri}, error: {e}")
                raise

        return databases

    def parse_storages_config(self, config_str: str) -> List[StorageConfig]:
        """
        Parse multi-storage configuration

        Args:
            config_str: Storage configuration string, multiple URIs separated by |

        Returns:
            List[StorageConfig]: Storage configuration list
        """
        storages = []

        if not config_str:
            return storages

        # Split multiple storage URIs by |
        uri_list = [uri.strip() for uri in config_str.split('|') if uri.strip()]

        for uri in uri_list:
            try:
                if '://' in uri:
                    # URI format
                    storage_config = self.storage_parser.parse_storage_uri(uri)
                else:
                    # Legacy format
                    storage_config = self.legacy_parser.parse_legacy_storage_format(uri)

                storages.append(storage_config)
                self.logger.debug(f"Storage URI parsed successfully: {uri}")
            except Exception as e:
                self.logger.error(f"Failed to parse storage URI: {uri}, error: {e}")
                raise

        return storages
