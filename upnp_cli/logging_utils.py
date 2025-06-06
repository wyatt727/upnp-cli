"""
Logging utilities for UPnP CLI.

This module provides centralized logging setup with colored console output
and rotating file handlers.
"""

import logging
import logging.handlers
import sys
from typing import Optional

from . import config


class ColorFormatter(logging.Formatter):
    """Custom formatter with color support for console output."""
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[37m',      # White
        'INFO': '\033[36m',       # Cyan
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[41m',   # Red background
    }
    RESET = '\033[0m'

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with color for console output."""
        # Get the color for this log level
        color = self.COLORS.get(record.levelname, self.RESET)
        
        # Format the message
        message = super().format(record)
        
        # Apply color only if outputting to a terminal
        if hasattr(sys.stderr, 'isatty') and sys.stderr.isatty():
            return f"{color}{message}{self.RESET}"
        return message


def setup_logging(verbose: bool = False, log_file: Optional[str] = None) -> logging.Logger:
    """
    Set up logging with console and file handlers.
    
    Args:
        verbose: Enable debug logging if True
        log_file: Custom log file path (optional)
        
    Returns:
        Configured logger instance
    """
    # Determine log level
    if verbose:
        level = logging.DEBUG
    else:
        level_name = config.get_log_level()
        level = getattr(logging, level_name, logging.INFO)
    
    # Get or create the main logger
    logger = logging.getLogger('upnp_cli')
    logger.setLevel(level)
    
    # Clear existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Console handler with color formatting
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(level)
    
    console_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    console_formatter = ColorFormatter(console_format, datefmt="%H:%M:%S")
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # File handler with rotation
    log_file_path = log_file or config.get_log_file_path()
    try:
        file_handler = logging.handlers.RotatingFileHandler(
            log_file_path,
            maxBytes=config.LOG_FILE_MAX_SIZE,
            backupCount=config.LOG_FILE_BACKUP_COUNT,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)  # Always debug level for file
        
        file_format = "%(asctime)s [%(levelname)s] %(name)s:%(funcName)s:%(lineno)d - %(message)s"
        file_formatter = logging.Formatter(file_format, datefmt="%Y-%m-%d %H:%M:%S")
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
        
    except (OSError, PermissionError) as e:
        # If we can't write to the log file, log to stderr but continue
        logger.warning(f"Could not create log file {log_file_path}: {e}")
    
    # Prevent propagation to root logger
    logger.propagate = False
    
    return logger


def get_logger(name: str = 'upnp_cli') -> logging.Logger:
    """
    Get a logger instance with the specified name.
    
    Args:
        name: Logger name (defaults to 'upnp_cli')
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


def suppress_console_logging():
    """Temporarily suppress console logging (for JSON output mode)."""
    logger = logging.getLogger('upnp_cli')
    for handler in logger.handlers:
        if isinstance(handler, logging.StreamHandler) and handler.stream == sys.stderr:
            handler.setLevel(logging.CRITICAL + 1)  # Effectively disable


def restore_console_logging():
    """Restore console logging to previous level."""
    logger = logging.getLogger('upnp_cli')
    for handler in logger.handlers:
        if isinstance(handler, logging.StreamHandler) and handler.stream == sys.stderr:
            # Restore to logger's level
            handler.setLevel(logger.level)


def log_debug(message: str, logger_name: str = 'upnp_cli') -> None:
    """Log a debug message."""
    logger = get_logger(logger_name)
    logger.debug(message)


def log_info(message: str, logger_name: str = 'upnp_cli') -> None:
    """Log an info message."""
    logger = get_logger(logger_name)
    logger.info(message)


def log_warning(message: str, logger_name: str = 'upnp_cli') -> None:
    """Log a warning message."""
    logger = get_logger(logger_name)
    logger.warning(message)


def log_error(message: str, logger_name: str = 'upnp_cli') -> None:
    """Log an error message."""
    logger = get_logger(logger_name)
    logger.error(message)


def log_critical(message: str, logger_name: str = 'upnp_cli') -> None:
    """Log a critical message."""
    logger = get_logger(logger_name)
    logger.critical(message)


def log_exception(message: str, logger_name: str = 'upnp_cli') -> None:
    """Log an exception with traceback."""
    logger = get_logger(logger_name)
    logger.exception(message)


# Module-level logger for this package
logger = get_logger(__name__) 