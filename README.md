# BackupFlow

An extensible database backup system that supports multiple database types and storage backends. Supports flexible backup strategies from multiple databases to multiple storages, with each database backed up separately to generate independent backup files.

## System Requirements

- **Python**: 3.9 or higher
- **Operating System**: Linux, macOS, Windows
- **Database Clients**:
  - MySQL: `mysql-client` (system package) or `PyMySQL` (Python package)
  - PostgreSQL: `postgresql-client` (system package) or `psycopg2-binary` (Python package)
- **Memory**: Minimum 512MB RAM (more for large databases)
- **Storage**: Sufficient space for temporary backup files

## Features

- 🗄️ **Multi-Database Support**: MySQL, PostgreSQL (extensible)
- 📁 **Independent Backups**: Each database backed up separately, filename format: `{timestamp}_{database_type}_{database_name}`
- ☁️ **Multi-Storage Backends**: Cloudflare R2, AWS S3 (extensible)
- 🔧 **Plugin Architecture**: Easy to add new database types and storage services
- ⚙️ **Flexible Configuration**: Supports URI format configuration and environment variables
- 🎯 **Multi-Strategy Support**: Supports flexible backup strategies from single database to multiple storages, multiple databases to multiple storages

- 🔄 **Automatic Cleanup**: Configurable backup retention policies
- 📝 **Complete Logging**: Detailed operation logs and error reporting
- 🚀 **GitHub Actions**: Pre-configured CI/CD workflows

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Refer to the `config/multi-strategy.env.example` file, supports two configuration formats:

**Single Strategy Shorthand Format (Recommended):**
```bash
# Simple configuration, suitable for single strategy scenarios
export DATABASES="mysql://backup_user:mysql_password@localhost:3306/db1,db2"
export STORAGES="r2://r2_access_key:r2_secret_key@account.r2.cloudflarestorage.com/backup-bucket?prefix=backups|s3://aws_access_key:aws_secret_key@us-east-1/backup-bucket-s3?prefix=backups"
```

**Multi-Strategy Format:**
```bash
# Strategy 1: MySQL backup to R2 and S3
export DATABASES_1="mysql://backup_user:mysql_password@localhost:3306/db1,db2"
export STORAGES_1="r2://r2_access_key:r2_secret_key@account.r2.cloudflarestorage.com/backup-bucket-r2?prefix=backups|s3://aws_access_key:aws_secret_key@us-east-1/backup-bucket-s3?prefix=backups"

# Strategy 2: PostgreSQL backup to R2
export DATABASES_2="postgres://postgres_user:postgres_password@localhost:5432/db3,db4"
export STORAGES_2="r2://r2_access_key2:r2_secret_key2@account2.r2.cloudflarestorage.com/backup-bucket-r2-2?prefix=pg-backups"

```

### 3. Test Connections

```bash
python src/main.py --test-connections
```

### 4. Run Backup

```bash
# Basic run
python src/main.py

# Enable debug logging
python src/main.py --log-level DEBUG

# Show configuration information
python src/main.py --info
```

## Configuration Guide

### Multi-Strategy Configuration

Use URI format to configure multiple backup strategies, supporting complex backup requirements. For detailed configuration examples, please refer to the `config/multi-strategy.env.example` file.

#### URI Format Description

**Database URI Format:**
```
mysql://username:password@host:port/database1,database2
postgres://username:password@host:port/database1,database2
```

**Storage URI Format:**
```
r2://access_key:secret_key@account.r2.cloudflarestorage.com/bucket_name?prefix=prefix
s3://access_key:secret_key@region/bucket_name?prefix=prefix
s3://access_key:secret_key@custom_endpoint/bucket_name?prefix=prefix
```

**Multi-Configuration Separation:**
- Multiple database instances separated by `|`
- Multiple storages separated by `|`

#### Backup Strategy Examples

1. **Single Database to Multiple Storages (Shorthand Format)**:
   ```bash
   DATABASES="mysql://user:pass@host:3306/db1,db2"
   STORAGES="r2://key:secret@endpoint/bucket1|s3://key:secret@region/bucket2"
   ```

2. **Multiple Databases to Multiple Storages (Multi-Strategy Format)**:
   ```bash
   DATABASES_1="mysql://user:pass@host1:3306/db1|postgres://user:pass@host2:5432/db2"
   STORAGES_1="r2://key:secret@endpoint/bucket1|s3://key:secret@region/bucket2"
   ```



### Configuration Options

All configuration is done through environment variables using URI format. For complete configuration examples, please refer to the `config/multi-strategy.env.example` file.

**Optional Configuration:**
- `COMPRESSION` (default: true) - Enable/disable backup compression
- `RETENTION_DAYS` (default: 30) - Number of days to keep old backups
- `VERIFY_BACKUP` (default: true) - Enable/disable backup file verification
- `BACKUP_TIMEOUT` (default: 60) - Backup timeout in minutes
- `LOG_LEVEL` (default: INFO) - Logging level

## Command Line Options

```bash
python src/main.py [options]

Options:
  --config, -c          Configuration file path (optional, environment variables recommended)
  --log-level          Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
  --log-file           Log file path
  --test-connections   Test connections only, do not execute backup
  --info              Show configuration and system information
  --version           Show version information (BackupFlow v1.0.0)
```

## GitHub Actions Integration

The project includes pre-configured GitHub Actions workflows for automated database backups in CI/CD environments. The workflow supports both scheduled and manual execution with comprehensive error handling and automatic dependency management.

### Features

- **Automated Scheduling**: Daily backups at midnight UTC (customizable)
- **Manual Triggering**: On-demand backup execution via GitHub UI
- **Smart Dependency Management**: Automatically detects and installs required database clients
- **Secure Configuration**: Uses GitHub Secrets for sensitive data
- **Multi-Strategy Support**: Supports both single and multi-strategy configurations
- **Connection Validation**: Tests all connections before executing backups
- **Error Handling**: Comprehensive error reporting and logging

### Quick Setup Guide

#### 1. Fork or Clone the Repository

```bash
git clone https://github.com/your-username/backupflow.git
cd backupflow
```

#### 2. Configure GitHub Secrets

Navigate to your repository settings → Secrets and variables → Actions, then add the following secrets:

**Required Secrets (Single Strategy Format - Recommended):**
```
DATABASES=mysql://backup_user:mysql_password@your-host:3306/db1,db2
STORAGES=r2://access_key:secret_key@account.r2.cloudflarestorage.com/bucket?prefix=backups
```

**Optional Secrets (with default values):**
```
COMPRESSION=true
RETENTION_DAYS=30
VERIFY_BACKUP=true
BACKUP_TIMEOUT=60
LOG_LEVEL=INFO
```

**Multi-Strategy Format (for complex scenarios):**
```
# Strategy 1: MySQL to multiple storages
DATABASES_1=mysql://user:pass@host1:3306/db1,db2
STORAGES_1=r2://key:secret@endpoint/bucket1|s3://key:secret@region/bucket2

# Strategy 2: PostgreSQL to R2
DATABASES_2=postgres://user:pass@host2:5432/db3,db4
STORAGES_2=r2://key:secret@endpoint/bucket3?prefix=pg-backups

# Add more strategies as needed (up to DATABASES_5/STORAGES_5)
```

#### 3. Customize Workflow Schedule (Optional)

Edit `.github/workflows/database-backup.yml` to change the backup schedule:

```yaml
on:
  schedule:
    - cron: '0 2 * * *'  # Run daily at 2 AM UTC
    - cron: '0 14 * * 0' # Run weekly on Sunday at 2 PM UTC
  workflow_dispatch:      # Keep manual trigger
```

#### 4. Test the Setup

1. **Manual Test**: Go to Actions tab → BackupFlow → Run workflow
2. **Check Logs**: Monitor the workflow execution for any errors
3. **Verify Backups**: Check your storage buckets for backup files

## Extension Guide

### Adding New Database Types

1. Create a new database implementation file in the `src/databases/` directory
2. Inherit from the `DatabaseInterface` interface and implement all abstract methods
3. Register the new database type in `src/databases/__init__.py`

Example: Adding MongoDB support

```python
# src/databases/mongodb_database.py
from ..interfaces.database_interface import DatabaseInterface, BackupResult
from ..interfaces.config_interface import DatabaseConfig

class MongoDBDatabase(DatabaseInterface):
    def test_connection(self) -> bool:
        # Implement MongoDB connection test
        pass

    def create_backup(self, output_path: str) -> BackupResult:
        # Implement MongoDB backup logic
        pass

    def create_single_database_backup(self, database_name: str, output_path: str) -> BackupResult:
        # Implement single database backup
        pass

    def validate_backup(self, backup_path: str) -> bool:
        # Implement backup validation
        pass

    def get_database_info(self) -> dict:
        # Return database information
        pass

    def get_backup_command(self) -> list:
        # Return backup command for logging
        pass

# src/interfaces/config_interface.py
# Add new database type to enum
class DatabaseType(Enum):
    MYSQL = "mysql"
    POSTGRESQL = "postgresql"
    MONGODB = "mongodb"  # New addition

# src/databases/__init__.py
from .mongodb_database import MongoDBDatabase
from ..interfaces.config_interface import DatabaseType

# Register new database type
DATABASE_REGISTRY[DatabaseType.MONGODB] = MongoDBDatabase
```

### Adding New Storage Backends

1. Create a new storage implementation file in the `src/storages/` directory
2. Inherit from the `StorageInterface` interface and implement all abstract methods
3. Register the new storage type in `src/storages/__init__.py`

Example: Adding Google Cloud Storage support

```python
# src/storages/gcs_storage.py
from ..interfaces.storage_interface import StorageInterface, UploadResult, StorageObject
from ..interfaces.config_interface import StorageConfig
from typing import List, Optional, Dict

class GCSStorage(StorageInterface):
    def test_connection(self) -> bool:
        # Implement GCS connection test
        pass

    def upload_file(self, local_path: str, remote_path: str, metadata=None) -> UploadResult:
        # Implement GCS upload logic
        pass

    def download_file(self, remote_path: str, local_path: str) -> bool:
        # Implement GCS download logic
        pass

    def delete_file(self, remote_path: str) -> bool:
        # Implement GCS delete logic
        pass

    def list_files(self, prefix: Optional[str] = None, max_keys: Optional[int] = None) -> List[StorageObject]:
        # Implement GCS list files logic
        pass

    def cleanup_old_files(self, retention_days: int, prefix: Optional[str] = None) -> List[str]:
        # Implement GCS cleanup logic
        pass

# src/interfaces/config_interface.py
# Add new storage type to enum
class StorageType(Enum):
    R2 = "r2"
    S3 = "s3"
    GCS = "gcs"  # New addition

# src/storages/__init__.py
from .gcs_storage import GCSStorage
from ..interfaces.config_interface import StorageType

# Register new storage type
STORAGE_REGISTRY[StorageType.GCS] = GCSStorage
```

### Custom Backup Strategies

You can implement custom backup strategies by inheriting from the `MultiStrategyBackupManager` class:

```python
from src.core.multi_strategy_backup_manager import MultiStrategyBackupManager

class CustomBackupManager(MultiStrategyBackupManager):
    def execute_backup(self, config):
        # Add custom pre-backup processing
        self.logger.info("Executing custom pre-backup processing...")

        # Call parent class backup method
        result = super().execute_backup(config)

        # Add custom post-backup processing
        if result.overall_success:
            self.logger.info("Executing custom post-backup processing...")
            # For example: send notifications, update monitoring systems, etc.

        return result
```

## Troubleshooting

### Common Issues

1. **Database Connection Failure**
   - Check if database service is running
   - Verify connection parameters (host, port, username, password)
   - Ensure database user has sufficient permissions

2. **Storage Upload Failure**
   - Check if storage service credentials are correct
   - Verify if bucket/container exists
   - Check network connectivity

3. **Backup File Too Large**
   - Consider enabling compression (`COMPRESSION=true`)
   - Backup different databases separately
   - Use incremental backup strategies

4. **Permission Issues**
   - Ensure running user has permission to read configuration files
   - Check write permissions for temporary directories
   - Verify database user permissions

### Debug Mode

Enable debug mode to get detailed logs:

```bash
python src/main.py --log-level DEBUG
```

### Log Files

Output logs to file:

```bash
python src/main.py --log-file backup.log
```

## Performance Optimization

### Large Database Backups

For large databases, it is recommended to:

1. Use compression to reduce file size
2. Adjust backup timeout settings
3. Consider executing backups during off-peak hours
4. Use incremental backup strategies

### Network Optimization

For slow network environments:

1. Enable compression to reduce data transfer
2. Consider using nearby storage regions
3. Implement resumable uploads

## Security Considerations

### Credential Management

- Use environment variables instead of configuration files to store sensitive information
- Use Secrets in GitHub Actions
- Regularly rotate access keys
- Use principle of least privilege

### Backup Encryption

Consider encrypting backup files before upload:

```python
# Example: Adding encryption functionality
from cryptography.fernet import Fernet

def encrypt_backup(file_path: str, key: bytes) -> str:
    fernet = Fernet(key)
    with open(file_path, 'rb') as f:
        data = f.read()

    encrypted_data = fernet.encrypt(data)
    encrypted_path = f"{file_path}.encrypted"

    with open(encrypted_path, 'wb') as f:
        f.write(encrypted_data)

    return encrypted_path
```

## Monitoring and Alerting

### Integrating Monitoring Systems

You can integrate monitoring through the following methods:

1. **Log Monitoring**: Send logs to ELK Stack or similar systems
2. **Metrics Monitoring**: Export backup success rates, duration metrics to Prometheus
3. **Alert Notifications**: Integrate with Slack, email, or other notification systems

### Health Checks

Run connection tests regularly:

```bash
# Add to crontab
0 */6 * * * /usr/bin/python3 /path/to/backup/src/main.py --test-connections
```

## License

MIT License

## Contributing

Issues and Pull Requests are welcome!

### Development Environment Setup

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Install database clients (optional, for system-level backup tools):
   ```bash
   # Ubuntu/Debian
   sudo apt-get install mysql-client postgresql-client

   # macOS
   brew install mysql-client postgresql

   # Windows
   # Download and install from official websites
   ```
4. Set up environment variables using `config/multi-strategy.env.example` as reference

### Contribution Guidelines

- Follow existing code style and architecture patterns
- Update relevant documentation when adding new features
- Ensure compatibility with the plugin architecture
- Test with both URI configuration formats
