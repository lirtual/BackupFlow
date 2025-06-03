"""
Logger Manager

Provides unified logging functionality
"""

import logging
import sys
from typing import Optional
from datetime import datetime
import os


class ColoredFormatter(logging.Formatter):
    """Colored log formatter"""

    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Purple
        'RESET': '\033[0m'      # Reset
    }

    def format(self, record):
        # Add color
        if record.levelname in self.COLORS:
            record.levelname = f"{self.COLORS[record.levelname]}{record.levelname}{self.COLORS['RESET']}"

        return super().format(record)


def setup_logger(name: str = "backup_system",
                level: str = "INFO",
                log_file: Optional[str] = None,
                enable_console: bool = True,
                enable_colors: bool = True) -> logging.Logger:
    """
    Setup logger

    Args:
        name: Logger name
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Log file path, if None then no file output
        enable_console: Whether to enable console output
        enable_colors: Whether to enable color output (console only)

    Returns:
        logging.Logger: Configured logger
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))

    # Clear existing handlers
    logger.handlers.clear()

    # Log format
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Console handler
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        if enable_colors and sys.stdout.isatty():
            console_formatter = ColoredFormatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            console_handler.setFormatter(console_formatter)
        else:
            console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # File handler
    if log_file:
        # Ensure log directory exists
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)

        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str = "backup_system") -> logging.Logger:
    """
    Get logger instance

    Args:
        name: Logger name

    Returns:
        logging.Logger: Logger instance
    """
    return logging.getLogger(name)


# Default logger
default_logger = setup_logger()


class LoggerMixin:
    """Logger mixin class"""

    @property
    def logger(self) -> logging.Logger:
        """Get logger for current class"""
        return get_logger(f"backup_system.{self.__class__.__name__}")
