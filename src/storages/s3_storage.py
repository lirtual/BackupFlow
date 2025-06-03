"""
AWS S3 Storage Implementation

Uses boto3 to interact with AWS S3
"""

import os
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

import boto3
from botocore.exceptions import ClientError, NoCredentialsError

from ..interfaces.storage_interface import (
    StorageInterface, StorageConfig, UploadResult, StorageObject
)
from ..core.logger import LoggerMixin


class S3Storage(StorageInterface, LoggerMixin):
    """
    AWS S3 Storage Implementation

    Uses boto3 client to interact with AWS S3
    """

    def __init__(self, config: StorageConfig):
        """Initialize S3 storage connection"""
        super().__init__(config)
        self.logger.info(f"Initializing S3 storage connection: {config.bucket}")

        # Validate required configuration
        self._validate_config()

        # Initialize boto3 client
        self._client = None
        self._init_client()

    def _validate_config(self):
        """Validate configuration"""
        required_fields = ['access_key', 'secret_key', 'bucket']
        for field in required_fields:
            if not getattr(self.config, field):
                raise ValueError(f"S3 storage configuration missing required field: {field}")

    def _init_client(self):
        """Initialize boto3 client"""
        try:
            # S3 uses standard AWS endpoints
            client_args = {
                'service_name': 's3',
                'aws_access_key_id': self.config.access_key,
                'aws_secret_access_key': self.config.secret_key,
            }

            # If region is specified
            if self.config.region and self.config.region != 'auto':
                client_args['region_name'] = self.config.region

            # If custom endpoint is specified (for S3-compatible services)
            if self.config.endpoint:
                client_args['endpoint_url'] = self.config.endpoint

            self._client = boto3.client(**client_args)
            self.logger.debug("S3 client initialization successful")
        except Exception as e:
            raise RuntimeError(f"S3 client initialization failed: {e}")
    
    def test_connection(self) -> bool:
        """Test storage connection"""
        self.logger.info("Testing S3 storage connection...")

        try:
            # Try to list bucket contents (limit to 1 object)
            self._client.list_objects_v2(
                Bucket=self.config.bucket,
                MaxKeys=1
            )
            self.logger.info("S3 storage connection test successful")
            return True

        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchBucket':
                self.logger.error(f"S3 bucket does not exist: {self.config.bucket}")
            elif error_code == 'AccessDenied':
                self.logger.error("S3 access denied, please check access keys")
            else:
                self.logger.error(f"S3 connection test failed: {e}")
            return False

        except NoCredentialsError:
            self.logger.error("S3 credentials not configured")
            return False

        except Exception as e:
            self.logger.error(f"S3 connection test exception: {e}")
            return False

    def upload_file(self, local_path: str, remote_path: str,
                   metadata: Optional[Dict[str, str]] = None) -> UploadResult:
        """Upload file to S3 storage"""
        self.logger.info(f"Uploading file to S3: {local_path} -> {remote_path}")
        start_time = time.time()

        try:
            # Check local file
            if not os.path.exists(local_path):
                raise FileNotFoundError(f"Local file does not exist: {local_path}")

            file_size = os.path.getsize(local_path)

            # Prepare upload arguments
            upload_args = {
                'Bucket': self.config.bucket,
                'Key': remote_path,
                'Filename': local_path
            }

            # Add metadata
            if metadata:
                upload_args['ExtraArgs'] = {'Metadata': metadata}

            # Execute upload
            self._client.upload_file(**upload_args)

            duration = time.time() - start_time

            self.logger.info(f"File upload completed: {remote_path}, size: {file_size} bytes, duration: {duration:.2f} seconds")

            return UploadResult(
                success=True,
                remote_path=remote_path,
                upload_size=file_size,
                duration_seconds=duration,
                metadata={
                    'storage_type': 's3',
                    'bucket': self.config.bucket,
                    'original_metadata': metadata
                }
            )

        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"S3 file upload failed: {e}"
            self.logger.error(error_msg)

            return UploadResult(
                success=False,
                duration_seconds=duration,
                error_message=error_msg
            )
    
    def download_file(self, remote_path: str, local_path: str) -> bool:
        """Download file from S3 storage"""
        self.logger.info(f"Downloading file from S3: {remote_path} -> {local_path}")

        try:
            # Ensure local directory exists
            local_dir = os.path.dirname(local_path)
            if local_dir and not os.path.exists(local_dir):
                os.makedirs(local_dir, exist_ok=True)

            # Execute download
            self._client.download_file(
                Bucket=self.config.bucket,
                Key=remote_path,
                Filename=local_path
            )

            self.logger.info(f"File download completed: {local_path}")
            return True

        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchKey':
                self.logger.error(f"S3 file does not exist: {remote_path}")
            else:
                self.logger.error(f"S3 file download failed: {e}")
            return False

        except Exception as e:
            self.logger.error(f"S3 file download exception: {e}")
            return False

    def delete_file(self, remote_path: str) -> bool:
        """Delete file from S3 storage"""
        self.logger.info(f"Deleting S3 file: {remote_path}")

        try:
            self._client.delete_object(
                Bucket=self.config.bucket,
                Key=remote_path
            )

            self.logger.info(f"File deletion completed: {remote_path}")
            return True

        except Exception as e:
            self.logger.error(f"S3 file deletion failed: {e}")
            return False

    def list_files(self, prefix: Optional[str] = None,
                  max_keys: Optional[int] = None) -> List[StorageObject]:
        """List files in S3 storage"""
        self.logger.debug(f"Listing S3 files, prefix: {prefix}, max count: {max_keys}")

        try:
            # Build request parameters
            list_args = {'Bucket': self.config.bucket}

            if prefix:
                list_args['Prefix'] = prefix
            if max_keys:
                list_args['MaxKeys'] = max_keys

            # Execute list request
            response = self._client.list_objects_v2(**list_args)

            objects = []
            if 'Contents' in response:
                for obj in response['Contents']:
                    storage_obj = StorageObject(
                        key=obj['Key'],
                        size=obj['Size'],
                        last_modified=obj['LastModified'],
                        etag=obj.get('ETag', '').strip('"')
                    )
                    objects.append(storage_obj)

            self.logger.debug(f"Found {len(objects)} files")
            return objects

        except Exception as e:
            self.logger.error(f"S3 file list retrieval failed: {e}")
            return []

    def cleanup_old_files(self, retention_days: int,
                         prefix: Optional[str] = None) -> List[str]:
        """Clean up old files"""
        self.logger.info(f"Cleaning up S3 files older than {retention_days} days, prefix: {prefix}")

        try:
            # Calculate cutoff date
            cutoff_date = datetime.now() - timedelta(days=retention_days)

            # Get file list
            files = self.list_files(prefix=prefix)

            deleted_files = []
            for file_obj in files:
                # Check file modification time
                if file_obj.last_modified < cutoff_date:
                    if self.delete_file(file_obj.key):
                        deleted_files.append(file_obj.key)
                        self.logger.debug(f"Deleted old file: {file_obj.key}")

            self.logger.info(f"Cleanup completed, deleted {len(deleted_files)} old files")
            return deleted_files

        except Exception as e:
            self.logger.error(f"S3 file cleanup failed: {e}")
            return []

    def get_file_info(self, remote_path: str) -> Optional[StorageObject]:
        """Get file information"""
        self.logger.debug(f"Getting S3 file information: {remote_path}")

        try:
            response = self._client.head_object(
                Bucket=self.config.bucket,
                Key=remote_path
            )

            return StorageObject(
                key=remote_path,
                size=response['ContentLength'],
                last_modified=response['LastModified'],
                etag=response.get('ETag', '').strip('"'),
                metadata=response.get('Metadata', {})
            )

        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchKey':
                self.logger.debug(f"S3 file does not exist: {remote_path}")
                return None
            else:
                self.logger.error(f"S3 file information retrieval failed: {e}")
                return None

        except Exception as e:
            self.logger.error(f"S3 file information retrieval exception: {e}")
            return None

    def cleanup(self):
        """Clean up resources"""
        if self._client:
            try:
                # boto3 client doesn't need explicit closing
                self._client = None
                self.logger.debug("S3 client resources cleaned up")
            except Exception as e:
                self.logger.warning(f"S3 client cleanup failed: {e}")

    def get_storage_info(self) -> Dict[str, Any]:
        """Get storage information"""
        return {
            'storage_type': 's3',
            'endpoint': self.config.endpoint,
            'bucket': self.config.bucket,
            'region': self.config.region,
            'prefix': self.config.prefix
        }
