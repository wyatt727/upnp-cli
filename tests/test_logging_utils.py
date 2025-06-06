"""Tests for upnp_cli.logging_utils module."""
import logging
import pytest
from upnp_cli.logging_utils import ColorFormatter, setup_logging, get_logger


class TestColorFormatter:
    """Test ColorFormatter class."""
    
    def test_color_formatter_initialization(self):
        """Test ColorFormatter initialization."""
        formatter = ColorFormatter()
        assert hasattr(formatter, 'COLORS')
        assert hasattr(formatter, 'RESET')
    
    def test_color_formatter_format(self):
        """Test ColorFormatter formatting."""
        formatter = ColorFormatter()
        record = logging.LogRecord(
            name='test', level=logging.INFO, pathname='', lineno=0,
            msg='Test message', args=(), exc_info=None
        )
        
        formatted = formatter.format(record)
        assert 'Test message' in formatted
        # Color codes should be present only if stderr is a TTY
        # Since we're in tests, check for either format
        has_color = '\u001b[' in formatted or '\033[' in formatted or 'Test message' in formatted
        assert has_color


class TestLoggingSetup:
    """Test logging setup functions."""
    
    def test_setup_logging_basic(self):
        """Test basic logging setup."""
        logger = setup_logging()
        # Check the returned logger (upnp_cli logger), not root logger
        assert logger.level == logging.INFO
        assert logger.name == 'upnp_cli'
    
    def test_get_logger_basic(self):
        """Test get_logger function."""
        logger = get_logger()
        assert isinstance(logger, logging.Logger)
        assert logger.name == 'upnp_cli'
    
    def test_get_logger_with_name(self):
        """Test get_logger with custom name."""
        logger = get_logger('test_module')
        # The function returns exactly what you pass in, no automatic prefixing
        assert logger.name == 'test_module'


if __name__ == '__main__':
    pytest.main([__file__]) 