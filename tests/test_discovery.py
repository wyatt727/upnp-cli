"""Tests for upnp_cli.discovery module."""
import pytest
from unittest.mock import AsyncMock, patch
from upnp_cli.discovery import discover_ssdp_devices, discover_upnp_devices


class TestDiscoveryFunctions:
    """Test discovery functions."""
    
    @pytest.mark.asyncio
    async def test_discover_ssdp_devices(self):
        """Test SSDP discovery function."""
        devices = await discover_ssdp_devices(timeout=1)
        assert isinstance(devices, list)
    
    def test_discover_upnp_devices_sync(self):
        """Test synchronous UPnP discovery."""
        devices = discover_upnp_devices(timeout=1)
        assert isinstance(devices, list)


if __name__ == '__main__':
    pytest.main([__file__]) 