"""
Configuration management for UPnP CLI.

This module provides global configuration constants and environment variable support.
"""

import os
from pathlib import Path
from typing import Optional

# Version info
VERSION = "0.1.0"

# Default ports for various UPnP services
DEFAULT_HTTP_PORT = 1400
DEFAULT_HTTPS_PORT = 1443
DEFAULT_RTSP_PORT = 7000

# Common UPnP ports to scan
UPNP_SCAN_PORTS = [
    80, 443, 1400, 1443, 7000, 8008, 8009, 8060, 8080, 8090, 
    8200, 8443, 9000, 9080, 9090, 49152, 49200, 55001, 56001
]

# Network settings
DEFAULT_SSDP_TIMEOUT = 5
DEFAULT_HTTP_TIMEOUT = 10
DEFAULT_NETWORK_SCAN_TIMEOUT = 30

# Stealth mode settings
STEALTH_MODE = False
STEALTH_MIN_DELAY = 0.1
STEALTH_MAX_DELAY = 0.5

# SSL/TLS settings
VALIDATE_SSL_CERTS = True
SSL_VERIFY_HOSTNAME = True

# Cache settings
CACHE_PATH = Path.home() / '.upnp_cli' / 'devices_cache.db'
CACHE_TTL_HOURS = 24
CACHE_MAX_ENTRIES = 10000

# Logging settings
LOG_LEVEL = "INFO"
LOG_FILE_PATH = Path.home() / '.upnp_cli' / 'upnp_cli.log'
LOG_FILE_MAX_SIZE = 10 * 1024 * 1024  # 10MB
LOG_FILE_BACKUP_COUNT = 5

# User agent strings for stealth mode
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:89.0) Gecko/20100101 Firefox/89.0",
]

# Device-specific retry intervals for fart loop
DEVICE_RETRY_INTERVALS = {
    "Samsung": 25,
    "LG": 35,
    "Sony": 28,
    "Philips": 30,
    "Panasonic": 32,
    "Generic": 30,
}


def get_config_value(key: str, default: Optional[str] = None) -> Optional[str]:
    """
    Get configuration value from environment variable with fallback to default.
    
    Args:
        key: Configuration key (will be prefixed with UPNPC_CLI_)
        default: Default value if environment variable is not set
        
    Returns:
        Configuration value or default
    """
    env_key = f"UPNPC_CLI_{key.upper()}"
    return os.getenv(env_key, default)


def get_cache_path() -> Path:
    """Get cache file path from config or environment."""
    cache_path_str = get_config_value("CACHE_PATH")
    if cache_path_str:
        return Path(cache_path_str).expanduser()
    return CACHE_PATH


def get_log_level() -> str:
    """Get log level from config or environment."""
    return get_config_value("LOG_LEVEL", LOG_LEVEL).upper()


def get_log_file_path() -> Path:
    """Get log file path from config or environment."""
    log_path_str = get_config_value("LOG_FILE_PATH")
    if log_path_str:
        return Path(log_path_str).expanduser()
    return LOG_FILE_PATH


def is_stealth_mode() -> bool:
    """Check if stealth mode is enabled."""
    stealth_env = get_config_value("STEALTH_MODE")
    if stealth_env:
        return stealth_env.lower() in ("true", "1", "yes", "on")
    return STEALTH_MODE


def get_ssl_verify() -> bool:
    """Check if SSL verification is enabled."""
    ssl_verify_env = get_config_value("SSL_VERIFY")
    if ssl_verify_env:
        return ssl_verify_env.lower() in ("true", "1", "yes", "on")
    return VALIDATE_SSL_CERTS


def get_http_timeout() -> int:
    """Get HTTP timeout from config."""
    timeout_str = get_config_value("HTTP_TIMEOUT", str(DEFAULT_HTTP_TIMEOUT))
    try:
        return int(timeout_str)
    except ValueError:
        return DEFAULT_HTTP_TIMEOUT


def ensure_config_dirs() -> None:
    """Ensure configuration directories exist."""
    get_cache_path().parent.mkdir(parents=True, exist_ok=True)
    get_log_file_path().parent.mkdir(parents=True, exist_ok=True)


# Initialize configuration directories on import
ensure_config_dirs() 