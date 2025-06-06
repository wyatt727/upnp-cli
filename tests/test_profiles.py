"""
Tests for the profiles module.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from upnp_cli.profiles import (
    DeviceProfile, ProfileManager, get_profile_manager,
    find_device_profile, get_device_control_info, validate_profile
)


class TestDeviceProfile:
    """Test DeviceProfile functionality."""
    
    @pytest.fixture
    def sample_profile_data(self):
        """Sample profile data for testing."""
        return {
            "name": "Test Sonos",
            "match": {
                "manufacturer": ["Sonos, Inc."],
                "deviceType": ["MediaRenderer"],
                "server_header": ["Sonos"]
            },
            "upnp": {
                "avtransport": {
                    "serviceType": "urn:schemas-upnp-org:service:AVTransport:1",
                    "controlURL": "/MediaRenderer/AVTransport/Control"
                },
                "rendering": {
                    "serviceType": "urn:schemas-upnp-org:service:RenderingControl:1",
                    "controlURL": "/MediaRenderer/RenderingControl/Control"
                }
            },
            "notes": "Test Sonos profile"
        }
    
    @pytest.fixture
    def sample_device_info(self):
        """Sample device information for testing."""
        return {
            "friendlyName": "Kitchen Sonos",
            "manufacturer": "Sonos, Inc.",
            "deviceType": "urn:schemas-upnp-org:device:MediaRenderer:1",
            "modelName": "S23",
            "ssdp_server": "Linux/5.4 UPnP/1.0 Sonos/70.3",
            "services": [
                {
                    "serviceType": "urn:schemas-upnp-org:service:AVTransport:1",
                    "controlURL": "/MediaRenderer/AVTransport/Control"
                }
            ]
        }
    
    def test_profile_initialization(self, sample_profile_data):
        """Test profile initialization."""
        profile = DeviceProfile(sample_profile_data)
        
        assert profile.name == "Test Sonos"
        assert profile.match_criteria == sample_profile_data["match"]
        assert profile.upnp == sample_profile_data["upnp"]
        assert profile.notes == "Test Sonos profile"
    
    def test_matches_device_manufacturer(self, sample_profile_data, sample_device_info):
        """Test device matching by manufacturer."""
        profile = DeviceProfile(sample_profile_data)
        score = profile.matches_device(sample_device_info)
        
        # Should match on manufacturer, deviceType, and server_header
        assert score > 0.5
    
    def test_matches_device_no_match(self, sample_profile_data):
        """Test device matching with no match."""
        profile = DeviceProfile(sample_profile_data)
        
        different_device = {
            "friendlyName": "Some TV",
            "manufacturer": "Samsung",
            "deviceType": "urn:schemas-upnp-org:device:MediaServer:1",
            "ssdp_server": "Samsung TV"
        }
        
        score = profile.matches_device(different_device)
        assert score == 0.0
    
    def test_get_primary_protocol_upnp(self, sample_profile_data):
        """Test getting primary protocol for UPnP device."""
        profile = DeviceProfile(sample_profile_data)
        assert profile.get_primary_protocol() == "upnp"
    
    def test_get_primary_protocol_cast(self):
        """Test getting primary protocol for Cast device."""
        cast_profile_data = {
            "name": "Test Chromecast",
            "match": {"manufacturer": ["Google"]},
            "cast": {
                "port": 8008,
                "deviceDescURL": "/ssdp/device-desc.xml"
            }
        }
        
        profile = DeviceProfile(cast_profile_data)
        assert profile.get_primary_protocol() == "cast"
    
    def test_get_control_urls_upnp(self, sample_profile_data):
        """Test getting control URLs for UPnP."""
        profile = DeviceProfile(sample_profile_data)
        urls = profile.get_control_urls("upnp")
        
        assert "avtransport" in urls
        assert urls["avtransport"] == "/MediaRenderer/AVTransport/Control"
        assert "rendering" in urls
        assert urls["rendering"] == "/MediaRenderer/RenderingControl/Control"
    
    def test_get_control_urls_ecp(self):
        """Test getting control URLs for ECP (Roku)."""
        ecp_profile_data = {
            "name": "Test Roku",
            "match": {"manufacturer": ["Roku"]},
            "ecp": {
                "port": 8060,
                "launchURL": "/launch/2213",
                "inputURL": "/input"
            }
        }
        
        profile = DeviceProfile(ecp_profile_data)
        urls = profile.get_control_urls("ecp")
        
        assert urls["launch"] == "/launch/2213"
        assert urls["input"] == "/input"
    
    def test_get_default_port_upnp(self, sample_profile_data):
        """Test getting default port for UPnP."""
        profile = DeviceProfile(sample_profile_data)
        assert profile.get_default_port("upnp") == 1400
    
    def test_get_default_port_cast(self):
        """Test getting default port for Cast."""
        cast_profile_data = {
            "name": "Test Chromecast",
            "match": {"manufacturer": ["Google"]},
            "cast": {"port": 8008}
        }
        
        profile = DeviceProfile(cast_profile_data)
        assert profile.get_default_port("cast") == 8008


class TestProfileManager:
    """Test ProfileManager functionality."""
    
    @pytest.fixture
    def temp_profile_dir(self):
        """Create temporary profile directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            profile_dir = Path(temp_dir)
            
            # Create test profiles.json
            profiles_data = {
                "device_profiles": [
                    {
                        "name": "Test Sonos",
                        "match": {
                            "manufacturer": ["Sonos, Inc."],
                            "deviceType": ["MediaRenderer"]
                        },
                        "upnp": {
                            "avtransport": {
                                "serviceType": "urn:schemas-upnp-org:service:AVTransport:1",
                                "controlURL": "/MediaRenderer/AVTransport/Control"
                            }
                        }
                    },
                    {
                        "name": "Test Roku",
                        "match": {
                            "manufacturer": ["Roku"],
                            "server_header": ["Roku"]
                        },
                        "ecp": {
                            "port": 8060,
                            "launchURL": "/launch/2213"
                        }
                    }
                ]
            }
            
            profiles_file = profile_dir / "profiles.json"
            with open(profiles_file, 'w') as f:
                json.dump(profiles_data, f)
            
            yield profile_dir
    
    def test_profile_manager_initialization(self, temp_profile_dir):
        """Test profile manager initialization."""
        manager = ProfileManager([temp_profile_dir])
        
        assert len(manager.profiles) == 2
        profile_names = [p.name for p in manager.profiles]
        assert "Test Sonos" in profile_names
        assert "Test Roku" in profile_names
    
    def test_find_matching_profiles(self, temp_profile_dir):
        """Test finding matching profiles."""
        manager = ProfileManager([temp_profile_dir])
        
        sonos_device = {
            "manufacturer": "Sonos, Inc.",
            "deviceType": "urn:schemas-upnp-org:device:MediaRenderer:1",
            "friendlyName": "Kitchen Sonos"
        }
        
        matches = manager.find_matching_profiles(sonos_device)
        
        assert len(matches) >= 1
        best_profile, score = matches[0]
        assert best_profile.name == "Test Sonos"
        assert score > 0.0
    
    def test_get_best_profile(self, temp_profile_dir):
        """Test getting best matching profile."""
        manager = ProfileManager([temp_profile_dir])
        
        roku_device = {
            "manufacturer": "Roku, Inc.",
            "ssdp_server": "Roku/9.4.0 UPnP/1.0",
            "friendlyName": "Living Room Roku"
        }
        
        profile = manager.get_best_profile(roku_device)
        
        assert profile is not None
        assert profile.name == "Test Roku"
    
    def test_get_profile_by_name(self, temp_profile_dir):
        """Test getting profile by name."""
        manager = ProfileManager([temp_profile_dir])
        
        profile = manager.get_profile_by_name("Test Sonos")
        assert profile is not None
        assert profile.name == "Test Sonos"
        
        # Test case insensitive
        profile = manager.get_profile_by_name("test sonos")
        assert profile is not None
        assert profile.name == "Test Sonos"
        
        # Test non-existent
        profile = manager.get_profile_by_name("Non-existent")
        assert profile is None
    
    def test_list_profiles(self, temp_profile_dir):
        """Test listing all profiles."""
        manager = ProfileManager([temp_profile_dir])
        
        profile_names = manager.list_profiles()
        
        assert len(profile_names) == 2
        assert "Test Sonos" in profile_names
        assert "Test Roku" in profile_names
    
    def test_reload_profiles(self, temp_profile_dir):
        """Test reloading profiles."""
        manager = ProfileManager([temp_profile_dir])
        
        initial_count = len(manager.profiles)
        
        # Add a new profile file
        new_profile = {
            "name": "Test Samsung",
            "match": {"manufacturer": ["Samsung"]},
            "samsung_wam": {"port": 55001}
        }
        
        new_profile_file = temp_profile_dir / "samsung.json"
        with open(new_profile_file, 'w') as f:
            json.dump(new_profile, f)
        
        # Reload and check
        manager.reload_profiles()
        
        assert len(manager.profiles) == initial_count + 1
        
        samsung_profile = manager.get_profile_by_name("Test Samsung")
        assert samsung_profile is not None


class TestGlobalFunctions:
    """Test global profile functions."""
    
    def test_get_profile_manager_singleton(self):
        """Test that get_profile_manager returns singleton instance."""
        manager1 = get_profile_manager()
        manager2 = get_profile_manager()
        assert manager1 is manager2
    
    @patch('upnp_cli.profiles.get_profile_manager')
    def test_find_device_profile(self, mock_get_manager):
        """Test find_device_profile function."""
        mock_manager = mock_get_manager.return_value
        mock_profile = DeviceProfile({
            "name": "Test Profile",
            "match": {"manufacturer": ["Test"]},
            "upnp": {}
        })
        mock_manager.get_best_profile.return_value = mock_profile
        
        device_info = {"manufacturer": "Test Corp"}
        result = find_device_profile(device_info)
        
        assert result == mock_profile
        mock_manager.get_best_profile.assert_called_once_with(device_info)
    
    @patch('upnp_cli.profiles.find_device_profile')
    def test_get_device_control_info_with_profile(self, mock_find_profile):
        """Test get_device_control_info with matching profile."""
        mock_profile = DeviceProfile({
            "name": "Test Sonos",
            "match": {"manufacturer": ["Sonos"]},
            "upnp": {
                "avtransport": {
                    "controlURL": "/MediaRenderer/AVTransport/Control"
                }
            }
        })
        mock_find_profile.return_value = mock_profile
        
        device_info = {"manufacturer": "Sonos, Inc.", "port": 1400}
        result = get_device_control_info(device_info)
        
        assert result["profile_name"] == "Test Sonos"
        assert result["protocol"] == "upnp"
        assert result["port"] == 1400
        assert "avtransport" in result["control_urls"]
    
    @patch('upnp_cli.profiles.find_device_profile')
    def test_get_device_control_info_no_profile(self, mock_find_profile):
        """Test get_device_control_info with no matching profile."""
        mock_find_profile.return_value = None
        
        device_info = {"manufacturer": "Unknown", "port": 8080}
        result = get_device_control_info(device_info)
        
        assert result["profile_name"] == "Generic UPnP"
        assert result["protocol"] == "upnp"
        assert result["port"] == 8080
        assert result["capabilities"] == ["basic_upnp"]


class TestProfileValidation:
    """Test profile validation."""
    
    def test_validate_profile_valid(self):
        """Test validation of valid profile."""
        valid_profile = {
            "name": "Test Profile",
            "match": {"manufacturer": ["Test"]},
            "upnp": {
                "avtransport": {
                    "controlURL": "/control"
                }
            }
        }
        
        errors = validate_profile(valid_profile)
        assert len(errors) == 0
    
    def test_validate_profile_missing_name(self):
        """Test validation with missing name."""
        invalid_profile = {
            "match": {"manufacturer": ["Test"]},
            "upnp": {}
        }
        
        errors = validate_profile(invalid_profile)
        assert "Missing required field: name" in errors
    
    def test_validate_profile_missing_match(self):
        """Test validation with missing match criteria."""
        invalid_profile = {
            "name": "Test Profile",
            "upnp": {}
        }
        
        errors = validate_profile(invalid_profile)
        assert "Missing required field: match" in errors
    
    def test_validate_profile_no_protocol(self):
        """Test validation with no protocol defined."""
        invalid_profile = {
            "name": "Test Profile",
            "match": {"manufacturer": ["Test"]},
            "notes": "This has no protocol"
        }
        
        errors = validate_profile(invalid_profile)
        assert "At least one protocol must be defined" in errors


if __name__ == "__main__":
    pytest.main([__file__]) 