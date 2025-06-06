"""Tests for upnp_cli.config module."""
import os
import pytest
from unittest.mock import patch
import upnp_cli.config as config


class TestConfigModule:
    """Test config module constants and functions."""
    
    def test_config_constants_defaults(self):
        """Test config module default constants."""
        assert config.LOG_LEVEL == "INFO"
        assert config.STEALTH_MODE is False
        assert config.VALIDATE_SSL_CERTS is True
        assert config.DEFAULT_HTTP_TIMEOUT == 10
        assert config.CACHE_TTL_HOURS == 24
        
        # Check port defaults
        assert config.DEFAULT_HTTP_PORT == 1400
        assert config.DEFAULT_HTTPS_PORT == 1443
        assert config.DEFAULT_RTSP_PORT == 7000


class TestConfigFunctions:
    """Test config utility functions."""
    
    def test_get_config_value_default(self):
        """Test get_config_value with default."""
        value = config.get_config_value("NONEXISTENT", "default_value")
        assert value == "default_value"
    
    def test_get_log_level_default(self):
        """Test get_log_level returns default."""
        level = config.get_log_level()
        assert level == "INFO"
    
    def test_is_stealth_mode_default(self):
        """Test is_stealth_mode returns default."""
        assert config.is_stealth_mode() is False


if __name__ == '__main__':
    pytest.main([__file__]) 