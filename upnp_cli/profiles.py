"""
Device profile management for UPnP CLI.

This module provides device profile loading, matching, and protocol selection
for different manufacturer devices and their specific control methods.
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
import re

from . import config
from .logging_utils import get_logger

logger = get_logger(__name__)


class DeviceProfile:
    """
    Represents a device profile with matching criteria and control methods.
    """
    
    def __init__(self, profile_data: Dict[str, Any]):
        """
        Initialize device profile from profile data.
        
        Args:
            profile_data: Profile dictionary from JSON
        """
        self.name = profile_data.get('name', 'Unknown')
        self.match_criteria = profile_data.get('match', {})
        self.upnp = profile_data.get('upnp', {})
        self.ecp = profile_data.get('ecp', {})
        self.samsung_wam = profile_data.get('samsung_wam', {})
        self.heos_api = profile_data.get('heos_api', {})
        self.musiccast_api = profile_data.get('musiccast_api', {})
        self.soundtouch_api = profile_data.get('soundtouch_api', {})
        self.cast = profile_data.get('cast', {})
        self.denon_api = profile_data.get('denon_api', {})
        self.onkyo_api = profile_data.get('onkyo_api', {})
        self.pioneer_api = profile_data.get('pioneer_api', {})
        self.squeezebox_api = profile_data.get('squeezebox_api', {})
        self.plex_api = profile_data.get('plex_api', {})
        self.jsonrpc_api = profile_data.get('jsonrpc_api', {})
        self.http_interface = profile_data.get('http_interface', {})
        self.openwebnet_api = profile_data.get('openwebnet_api', {})
        self.bluesound_api = profile_data.get('bluesound_api', {})
        self.notes = profile_data.get('notes', '')
        
        logger.debug(f"Loaded profile: {self.name}")
    
    def matches_device(self, device_info: Dict[str, Any]) -> float:
        """
        Calculate match score for a device.
        
        Args:
            device_info: Device information from discovery
            
        Returns:
            Match score (0.0 to 1.0, higher is better match)
        """
        score = 0.0
        total_checks = 0
        
        # Check manufacturer
        if 'manufacturer' in self.match_criteria:
            total_checks += 1
            device_manufacturer = device_info.get('manufacturer', '').lower()
            for match_manufacturer in self.match_criteria['manufacturer']:
                if match_manufacturer.lower() in device_manufacturer:
                    score += 1.0
                    break
        
        # Check device type
        if 'deviceType' in self.match_criteria:
            total_checks += 1
            device_type = device_info.get('deviceType', '').lower()
            for match_type in self.match_criteria['deviceType']:
                if match_type.lower() in device_type:
                    score += 1.0
                    break
        
        # Check model name
        if 'modelName' in self.match_criteria:
            total_checks += 1
            device_model = device_info.get('modelName', '').lower()
            for match_model in self.match_criteria['modelName']:
                if match_model.lower() in device_model:
                    score += 1.0
                    break
        
        # Check server header (from SSDP)
        if 'server_header' in self.match_criteria:
            total_checks += 1
            device_server = device_info.get('ssdp_server', '').lower()
            for match_server in self.match_criteria['server_header']:
                if match_server.lower() in device_server:
                    score += 1.0
                    break
        
        # Check friendly name
        if 'friendlyName' in self.match_criteria:
            total_checks += 1
            device_name = device_info.get('friendlyName', '').lower()
            for match_name in self.match_criteria['friendlyName']:
                if match_name.lower() in device_name:
                    score += 1.0
                    break
        
        # Check services
        if 'services' in self.match_criteria:
            device_services = device_info.get('services', [])
            device_service_types = [s.get('serviceType', '') for s in device_services]
            
            for required_service in self.match_criteria['services']:
                total_checks += 1
                if any(required_service in stype for stype in device_service_types):
                    score += 1.0
        
        # Return normalized score
        if total_checks == 0:
            return 0.0
        
        match_score = score / total_checks
        
        if match_score > 0:
            logger.debug(f"Profile {self.name} matches device with score {match_score:.2f}")
        
        return match_score
    
    def get_primary_protocol(self) -> str:
        """
        Get the primary protocol for this device profile.
        
        Returns:
            Protocol name (upnp, ecp, cast, etc.)
        """
        # Priority order for protocol selection
        if self.cast:
            return 'cast'
        elif self.ecp:
            return 'ecp'
        elif self.samsung_wam:
            return 'samsung_wam'
        elif self.heos_api:
            return 'heos_api'
        elif self.musiccast_api:
            return 'musiccast_api'
        elif self.soundtouch_api:
            return 'soundtouch_api'
        elif self.denon_api:
            return 'denon_api'
        elif self.onkyo_api:
            return 'onkyo_api'
        elif self.pioneer_api:
            return 'pioneer_api'
        elif self.squeezebox_api:
            return 'squeezebox_api'
        elif self.plex_api:
            return 'plex_api'
        elif self.jsonrpc_api:
            return 'jsonrpc_api'
        elif self.http_interface:
            return 'http_interface'
        elif self.openwebnet_api:
            return 'openwebnet_api'
        elif self.bluesound_api:
            return 'bluesound_api'
        elif self.upnp:
            return 'upnp'
        else:
            return 'generic'
    
    def get_control_urls(self, protocol: Optional[str] = None) -> Dict[str, str]:
        """
        Get control URLs for the specified protocol.
        
        Args:
            protocol: Protocol name (defaults to primary protocol)
            
        Returns:
            Dictionary of control URLs
        """
        if protocol is None:
            protocol = self.get_primary_protocol()
        
        if protocol == 'upnp' and self.upnp:
            urls = {}
            for service_name, service_info in self.upnp.items():
                if isinstance(service_info, dict) and 'controlURL' in service_info:
                    urls[service_name] = service_info['controlURL']
            return urls
        
        elif protocol == 'ecp' and self.ecp:
            return {
                'launch': self.ecp.get('launchURL', '/launch/2213'),
                'input': self.ecp.get('inputURL', '/input')
            }
        
        elif protocol == 'samsung_wam' and self.samsung_wam:
            return {
                'setUrlPlayback': self.samsung_wam.get('setUrlPlayback', {}).get('endpoint', '/UIC?cmd={CMD_ENCODED}')
            }
        
        return {}
    
    def get_default_port(self, protocol: Optional[str] = None) -> int:
        """
        Get default port for the specified protocol.
        
        Args:
            protocol: Protocol name (defaults to primary protocol)
            
        Returns:
            Default port number
        """
        if protocol is None:
            protocol = self.get_primary_protocol()
        
        port_map = {
            'upnp': 1400,
            'ecp': 8060,
            'samsung_wam': 55001,
            'cast': 8008,
            'heos_api': 1255,
            'musiccast_api': 5005,
            'soundtouch_api': 8090,
            'denon_api': 80,
            'onkyo_api': 60128,
            'pioneer_api': 8102,
            'squeezebox_api': 9000,
            'plex_api': 32400,
            'jsonrpc_api': 8080,
            'http_interface': 8080,
            'openwebnet_api': 20000,
            'bluesound_api': 11000
        }
        
        # Check if profile specifies a port
        if protocol == 'ecp' and self.ecp and 'port' in self.ecp:
            return self.ecp['port']
        elif protocol == 'samsung_wam' and self.samsung_wam and 'port' in self.samsung_wam:
            return self.samsung_wam['port']
        elif protocol == 'cast' and self.cast and 'port' in self.cast:
            return self.cast['port']
        elif hasattr(self, f'{protocol}_api'):
            api_info = getattr(self, f'{protocol}_api')
            if isinstance(api_info, dict) and 'port' in api_info:
                return api_info['port']
        
        return port_map.get(protocol, 1400)


class ProfileManager:
    """
    Manages device profiles and matching.
    """
    
    def __init__(self, profile_paths: Optional[List[Path]] = None):
        """
        Initialize profile manager.
        
        Args:
            profile_paths: List of paths to search for profiles
        """
        if profile_paths is None:
            profile_paths = self._get_default_profile_paths()
        
        self.profile_paths = profile_paths
        self.profiles: List[DeviceProfile] = []
        self._load_profiles()
    
    def _get_default_profile_paths(self) -> List[Path]:
        """Get default profile search paths."""
        paths = []
        
        # Built-in profiles (in package)
        package_dir = Path(__file__).parent.parent
        builtin_profiles = package_dir / 'profiles'
        if builtin_profiles.exists():
            paths.append(builtin_profiles)
        
        # User profiles
        user_profiles = Path.home() / '.upnp_cli' / 'profiles'
        paths.append(user_profiles)
        
        # Current directory profiles
        current_profiles = Path.cwd() / 'profiles'
        if current_profiles.exists():
            paths.append(current_profiles)
        
        return paths
    
    def _load_profiles(self) -> None:
        """Load all profiles from search paths."""
        self.profiles = []
        
        for profile_path in self.profile_paths:
            if not profile_path.exists():
                logger.debug(f"Profile path does not exist: {profile_path}")
                continue
            
            try:
                # Load profiles.json if it exists
                profiles_file = profile_path / 'profiles.json'
                if profiles_file.exists():
                    with open(profiles_file, 'r') as f:
                        data = json.load(f)
                        
                    # Handle both direct list and nested structure
                    if 'device_profiles' in data:
                        profile_list = data['device_profiles']
                    elif isinstance(data, list):
                        profile_list = data
                    else:
                        logger.warning(f"Invalid profiles format in {profiles_file}")
                        continue
                    
                    for profile_data in profile_list:
                        profile = DeviceProfile(profile_data)
                        self.profiles.append(profile)
                    
                    logger.info(f"Loaded {len(profile_list)} profiles from {profiles_file}")
                
                # Load individual JSON files
                for json_file in profile_path.glob('*.json'):
                    if json_file.name == 'profiles.json':
                        continue  # Already handled above
                    
                    try:
                        with open(json_file, 'r') as f:
                            profile_data = json.load(f)
                        
                        profile = DeviceProfile(profile_data)
                        self.profiles.append(profile)
                        
                        logger.debug(f"Loaded profile from {json_file}")
                    
                    except Exception as e:
                        logger.warning(f"Failed to load profile from {json_file}: {e}")
            
            except Exception as e:
                logger.error(f"Failed to load profiles from {profile_path}: {e}")
        
        logger.info(f"Total profiles loaded: {len(self.profiles)}")
    
    def find_matching_profiles(self, device_info: Dict[str, Any], 
                             min_score: float = 0.1) -> List[tuple[DeviceProfile, float]]:
        """
        Find profiles that match a device.
        
        Args:
            device_info: Device information from discovery
            min_score: Minimum match score to include
            
        Returns:
            List of (profile, score) tuples sorted by score (highest first)
        """
        matches = []
        
        for profile in self.profiles:
            score = profile.matches_device(device_info)
            if score >= min_score:
                matches.append((profile, score))
        
        # Sort by score (highest first)
        matches.sort(key=lambda x: x[1], reverse=True)
        
        logger.debug(f"Found {len(matches)} matching profiles for device {device_info.get('friendlyName', 'Unknown')}")
        return matches
    
    def get_best_profile(self, device_info: Dict[str, Any]) -> Optional[DeviceProfile]:
        """
        Get the best matching profile for a device.
        
        Args:
            device_info: Device information from discovery
            
        Returns:
            Best matching profile or None
        """
        matches = self.find_matching_profiles(device_info)
        
        if matches:
            best_profile, score = matches[0]
            logger.info(f"Best profile for device {device_info.get('friendlyName', 'Unknown')}: {best_profile.name} (score: {score:.2f})")
            return best_profile
        
        logger.debug(f"No matching profile found for device {device_info.get('friendlyName', 'Unknown')}")
        return None
    
    def get_profile_by_name(self, name: str) -> Optional[DeviceProfile]:
        """
        Get profile by name.
        
        Args:
            name: Profile name
            
        Returns:
            Profile or None if not found
        """
        for profile in self.profiles:
            if profile.name.lower() == name.lower():
                return profile
        
        return None
    
    def list_profiles(self) -> List[str]:
        """
        List all available profile names.
        
        Returns:
            List of profile names
        """
        return [profile.name for profile in self.profiles]
    
    def reload_profiles(self) -> None:
        """Reload all profiles from disk."""
        logger.info("Reloading device profiles")
        self._load_profiles()


# Global profile manager instance
_profile_manager: Optional[ProfileManager] = None


def get_profile_manager() -> ProfileManager:
    """Get global profile manager instance."""
    global _profile_manager
    if _profile_manager is None:
        _profile_manager = ProfileManager()
    return _profile_manager


def find_device_profile(device_info: Dict[str, Any]) -> Optional[DeviceProfile]:
    """
    Find the best matching profile for a device.
    
    Args:
        device_info: Device information from discovery
        
    Returns:
        Best matching profile or None
    """
    manager = get_profile_manager()
    return manager.get_best_profile(device_info)


def get_device_control_info(device_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get complete control information for a device.
    
    Args:
        device_info: Device information from discovery
        
    Returns:
        Dictionary with control information including profile, protocol, URLs, etc.
    """
    profile = find_device_profile(device_info)
    
    if profile is None:
        # Return generic UPnP control info
        return {
            'profile_name': 'Generic UPnP',
            'protocol': 'upnp',
            'port': device_info.get('port', 1400),
            'control_urls': {},
            'capabilities': ['basic_upnp']
        }
    
    protocol = profile.get_primary_protocol()
    control_urls = profile.get_control_urls(protocol)
    port = profile.get_default_port(protocol)
    
    # Override port if device provides it
    if 'port' in device_info:
        port = device_info['port']
    
    return {
        'profile_name': profile.name,
        'protocol': protocol,
        'port': port,
        'control_urls': control_urls,
        'capabilities': [protocol],
        'notes': profile.notes
    }


def validate_profile(profile_data: Dict[str, Any]) -> List[str]:
    """
    Validate a profile data structure.
    
    Args:
        profile_data: Profile dictionary
        
    Returns:
        List of validation errors (empty if valid)
    """
    errors = []
    
    # Required fields
    if 'name' not in profile_data:
        errors.append("Missing required field: name")
    
    if 'match' not in profile_data:
        errors.append("Missing required field: match")
    
    # At least one protocol must be defined
    protocols = ['upnp', 'ecp', 'samsung_wam', 'cast', 'heos_api', 'musiccast_api', 
                'soundtouch_api', 'denon_api', 'onkyo_api', 'pioneer_api', 
                'squeezebox_api', 'plex_api', 'jsonrpc_api', 'http_interface',
                'openwebnet_api', 'bluesound_api']
    
    if not any(protocol in profile_data for protocol in protocols):
        errors.append("At least one protocol must be defined")
    
    return errors 