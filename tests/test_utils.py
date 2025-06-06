"""
Unit tests for upnp_cli.utils module.
"""

import pytest
import socket
from unittest.mock import patch, MagicMock

from upnp_cli.utils import (
    get_local_ip, parse_device_description_xml, is_port_open,
    validate_ip_address, validate_port, expand_network_range
)


class TestNetworkUtils:
    """Test network utility functions."""
    
    def test_validate_ip_address_valid(self):
        """Test IP address validation with valid addresses."""
        assert validate_ip_address("192.168.1.1") is True
        assert validate_ip_address("10.0.0.1") is True
        assert validate_ip_address("127.0.0.1") is True
        assert validate_ip_address("::1") is True  # IPv6
    
    def test_validate_ip_address_invalid(self):
        """Test IP address validation with invalid addresses."""
        assert validate_ip_address("not.an.ip") is False
        assert validate_ip_address("192.168.1.256") is False
        assert validate_ip_address("192.168.1") is False
        assert validate_ip_address("") is False
    
    def test_validate_port_valid(self):
        """Test port validation with valid ports."""
        assert validate_port(80) is True
        assert validate_port(1400) is True
        assert validate_port(65535) is True
        assert validate_port(1) is True
    
    def test_validate_port_invalid(self):
        """Test port validation with invalid ports."""
        assert validate_port(0) is False
        assert validate_port(65536) is False
        assert validate_port(-1) is False
    
    def test_expand_network_range(self):
        """Test network range expansion."""
        # Test /30 network (should return host IPs)
        hosts = expand_network_range("192.168.1.0/30")
        assert len(hosts) == 2
        assert "192.168.1.1" in hosts
        assert "192.168.1.2" in hosts
        
        # Test invalid network
        hosts = expand_network_range("invalid")
        assert hosts == []
    
    @patch('socket.socket')
    def test_is_port_open_success(self, mock_socket):
        """Test port checking when port is open."""
        mock_sock = MagicMock()
        mock_socket.return_value.__enter__.return_value = mock_sock
        mock_sock.connect_ex.return_value = 0
        
        result = is_port_open("192.168.1.1", 80)
        assert result is True
        mock_sock.connect_ex.assert_called_once_with(("192.168.1.1", 80))
    
    @patch('socket.socket')
    def test_is_port_open_failure(self, mock_socket):
        """Test port checking when port is closed."""
        mock_sock = MagicMock()
        mock_socket.return_value.__enter__.return_value = mock_sock
        mock_sock.connect_ex.return_value = 1
        
        result = is_port_open("192.168.1.1", 80)
        assert result is False


class TestXMLParsing:
    """Test XML parsing utilities."""
    
    def test_parse_device_description_xml_valid(self):
        """Test parsing valid device description XML."""
        xml_content = """<?xml version="1.0"?>
        <root xmlns="urn:schemas-upnp-org:device-1-0">
            <device>
                <deviceType>urn:schemas-upnp-org:device:MediaRenderer:1</deviceType>
                <friendlyName>Test Device</friendlyName>
                <manufacturer>Test Manufacturer</manufacturer>
                <modelName>Test Model</modelName>
                <serviceList>
                    <service>
                        <serviceType>urn:schemas-upnp-org:service:AVTransport:1</serviceType>
                        <serviceId>urn:upnp-org:serviceId:AVTransport</serviceId>
                        <controlURL>/MediaRenderer/AVTransport/Control</controlURL>
                    </service>
                </serviceList>
            </device>
        </root>"""
        
        result = parse_device_description_xml(xml_content)
        
        assert result['deviceType'] == "urn:schemas-upnp-org:device:MediaRenderer:1"
        assert result['friendlyName'] == "Test Device"
        assert result['manufacturer'] == "Test Manufacturer"
        assert result['modelName'] == "Test Model"
        assert len(result['services']) == 1
        assert result['services'][0]['serviceType'] == "urn:schemas-upnp-org:service:AVTransport:1"
    
    def test_parse_device_description_xml_invalid(self):
        """Test parsing invalid XML."""
        with pytest.raises(ValueError, match="Invalid XML"):
            parse_device_description_xml("not valid xml")
    
    def test_parse_device_description_xml_no_device(self):
        """Test parsing XML without device element."""
        xml_content = """<?xml version="1.0"?>
        <root xmlns="urn:schemas-upnp-org:device-1-0">
            <notdevice>
                <friendlyName>Test</friendlyName>
            </notdevice>
        </root>"""
        
        with pytest.raises(ValueError, match="No device element found"):
            parse_device_description_xml(xml_content)


class TestLocalIPDetection:
    """Test local IP detection."""
    
    def test_get_local_ip_with_netifaces(self):
        """Test getting local IP with netifaces available."""
        # This test depends on the actual netifaces module being available
        # and working with real network interfaces. Since this is a basic test,
        # we'll just verify the function returns a valid IP address.
        result = get_local_ip()
        assert validate_ip_address(result)
    
    @patch('socket.socket')
    def test_get_local_ip_fallback(self, mock_socket):
        """Test getting local IP with fallback method."""
        mock_sock = MagicMock()
        mock_socket.return_value.__enter__.return_value = mock_sock
        mock_sock.getsockname.return_value = ('192.168.1.100', 12345)
        
        # Import after patching to avoid netifaces
        with patch.dict('sys.modules', {'netifaces': None}):
            result = get_local_ip()
            assert result == '192.168.1.100' 