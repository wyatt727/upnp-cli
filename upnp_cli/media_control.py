"""
Universal Media Control Engine for UPnP CLI.

This module provides standardized media control operations that work across
different device types and protocols (UPnP, ECP, Cast, Samsung WAM, etc.).
"""

import asyncio
import json
import time
from typing import Dict, List, Any, Optional, Union, Tuple
from urllib.parse import urljoin
import xml.etree.ElementTree as ET

import aiohttp
import requests

from . import config
from .logging_utils import get_logger
from .soap_client import SOAPClient, SOAPError
from .profiles import get_device_control_info
from .utils import validate_ip_address, validate_port

logger = get_logger(__name__)


class MediaControlError(Exception):
    """Exception raised for media control operations."""
    
    def __init__(self, message: str, error_code: Optional[int] = None, device_info: Optional[Dict] = None):
        self.message = message
        self.error_code = error_code
        self.device_info = device_info
        super().__init__(self.message)


class MediaController:
    """
    Universal media controller supporting multiple protocols.
    
    Provides a standardized interface for controlling different types of media devices
    through UPnP SOAP, ECP, Cast, and other proprietary protocols.
    """
    
    def __init__(self, stealth_mode: bool = False):
        """
        Initialize media controller.
        
        Args:
            stealth_mode: Enable stealth mode for SOAP operations
        """
        self.soap_client = SOAPClient(stealth_mode=stealth_mode)
        self.stealth_mode = stealth_mode
        
        logger.debug(f"MediaController initialized (stealth_mode: {stealth_mode})")
    
    # === PLAYBACK CONTROLS ===
    
    async def play(self, 
                   host: str, 
                   port: int,
                   device_info: Optional[Dict[str, Any]] = None,
                   **kwargs) -> Dict[str, Any]:
        """
        Start playback on device.
        
        Args:
            host: Device IP address
            port: Device port
            device_info: Device information for protocol selection
            **kwargs: Additional protocol-specific parameters
            
        Returns:
            Control operation result
        """
        try:
            control_info = get_device_control_info(device_info or {})
            protocol = control_info.get('protocol', 'upnp')
            
            if protocol == 'upnp':
                return await self._upnp_play(host, port, control_info, **kwargs)
            elif protocol == 'ecp':
                return await self._ecp_play(host, port, control_info, **kwargs)
            elif protocol == 'samsung_wam':
                return await self._samsung_wam_play(host, port, control_info, **kwargs)
            elif protocol == 'cast':
                return await self._cast_play(host, port, control_info, **kwargs)
            else:
                # Try UPnP as fallback
                return await self._upnp_play(host, port, control_info, **kwargs)
                
        except Exception as e:
            logger.error(f"Play operation failed on {host}:{port}: {e}")
            raise MediaControlError(f"Play failed: {e}")
    
    async def pause(self, 
                    host: str, 
                    port: int,
                    device_info: Optional[Dict[str, Any]] = None,
                    **kwargs) -> Dict[str, Any]:
        """
        Pause playback on device.
        
        Args:
            host: Device IP address
            port: Device port
            device_info: Device information for protocol selection
            **kwargs: Additional protocol-specific parameters
            
        Returns:
            Control operation result
        """
        try:
            control_info = get_device_control_info(device_info or {})
            protocol = control_info.get('protocol', 'upnp')
            
            if protocol == 'upnp':
                return await self._upnp_pause(host, port, control_info, **kwargs)
            elif protocol == 'ecp':
                return await self._ecp_pause(host, port, control_info, **kwargs)
            elif protocol == 'samsung_wam':
                return await self._samsung_wam_pause(host, port, control_info, **kwargs)
            elif protocol == 'cast':
                return await self._cast_pause(host, port, control_info, **kwargs)
            else:
                # Try UPnP as fallback
                return await self._upnp_pause(host, port, control_info, **kwargs)
                
        except Exception as e:
            logger.error(f"Pause operation failed on {host}:{port}: {e}")
            raise MediaControlError(f"Pause failed: {e}")
    
    async def stop(self, 
                   host: str, 
                   port: int,
                   device_info: Optional[Dict[str, Any]] = None,
                   **kwargs) -> Dict[str, Any]:
        """
        Stop playback on device.
        
        Args:
            host: Device IP address
            port: Device port
            device_info: Device information for protocol selection
            **kwargs: Additional protocol-specific parameters
            
        Returns:
            Control operation result
        """
        try:
            control_info = get_device_control_info(device_info or {})
            protocol = control_info.get('protocol', 'upnp')
            
            if protocol == 'upnp':
                return await self._upnp_stop(host, port, control_info, **kwargs)
            elif protocol == 'ecp':
                return await self._ecp_stop(host, port, control_info, **kwargs)
            elif protocol == 'samsung_wam':
                return await self._samsung_wam_stop(host, port, control_info, **kwargs)
            elif protocol == 'cast':
                return await self._cast_stop(host, port, control_info, **kwargs)
            else:
                # Try UPnP as fallback
                return await self._upnp_stop(host, port, control_info, **kwargs)
                
        except Exception as e:
            logger.error(f"Stop operation failed on {host}:{port}: {e}")
            raise MediaControlError(f"Stop failed: {e}")
    
    async def next_track(self, 
                         host: str, 
                         port: int,
                         device_info: Optional[Dict[str, Any]] = None,
                         **kwargs) -> Dict[str, Any]:
        """
        Skip to next track.
        
        Args:
            host: Device IP address
            port: Device port
            device_info: Device information for protocol selection
            **kwargs: Additional protocol-specific parameters
            
        Returns:
            Control operation result
        """
        try:
            control_info = get_device_control_info(device_info or {})
            protocol = control_info.get('protocol', 'upnp')
            
            if protocol == 'upnp':
                return await self._upnp_next(host, port, control_info, **kwargs)
            else:
                # Most protocols don't support next/previous
                return {"status": "not_supported", "protocol": protocol}
                
        except Exception as e:
            logger.error(f"Next track operation failed on {host}:{port}: {e}")
            raise MediaControlError(f"Next track failed: {e}")
    
    async def previous_track(self, 
                             host: str, 
                             port: int,
                             device_info: Optional[Dict[str, Any]] = None,
                             **kwargs) -> Dict[str, Any]:
        """
        Skip to previous track.
        
        Args:
            host: Device IP address
            port: Device port
            device_info: Device information for protocol selection
            **kwargs: Additional protocol-specific parameters
            
        Returns:
            Control operation result
        """
        try:
            control_info = get_device_control_info(device_info or {})
            protocol = control_info.get('protocol', 'upnp')
            
            if protocol == 'upnp':
                return await self._upnp_previous(host, port, control_info, **kwargs)
            else:
                # Most protocols don't support next/previous
                return {"status": "not_supported", "protocol": protocol}
                
        except Exception as e:
            logger.error(f"Previous track operation failed on {host}:{port}: {e}")
            raise MediaControlError(f"Previous track failed: {e}")
    
    async def seek(self, 
                   host: str, 
                   port: int,
                   position: str,
                   device_info: Optional[Dict[str, Any]] = None,
                   **kwargs) -> Dict[str, Any]:
        """
        Seek to position in current track.
        
        Args:
            host: Device IP address
            port: Device port
            position: Position in format "HH:MM:SS" or seconds
            device_info: Device information for protocol selection
            **kwargs: Additional protocol-specific parameters
            
        Returns:
            Control operation result
        """
        try:
            control_info = get_device_control_info(device_info or {})
            protocol = control_info.get('protocol', 'upnp')
            
            if protocol == 'upnp':
                return await self._upnp_seek(host, port, control_info, position, **kwargs)
            else:
                # Most protocols don't support seeking
                return {"status": "not_supported", "protocol": protocol}
                
        except Exception as e:
            logger.error(f"Seek operation failed on {host}:{port}: {e}")
            raise MediaControlError(f"Seek failed: {e}")
    
    async def set_uri(self, 
                      host: str, 
                      port: int,
                      uri: str,
                      metadata: Optional[str] = None,
                      device_info: Optional[Dict[str, Any]] = None,
                      **kwargs) -> Dict[str, Any]:
        """
        Set media URI for playback.
        
        Args:
            host: Device IP address
            port: Device port
            uri: Media URI to play
            metadata: DIDL metadata (for UPnP)
            device_info: Device information for protocol selection
            **kwargs: Additional protocol-specific parameters
            
        Returns:
            Control operation result
        """
        try:
            control_info = get_device_control_info(device_info or {})
            protocol = control_info.get('protocol', 'upnp')
            
            if protocol == 'upnp':
                return await self._upnp_set_uri(host, port, control_info, uri, metadata, **kwargs)
            elif protocol == 'ecp':
                return await self._ecp_set_uri(host, port, control_info, uri, **kwargs)
            elif protocol == 'samsung_wam':
                return await self._samsung_wam_set_uri(host, port, control_info, uri, **kwargs)
            elif protocol == 'cast':
                return await self._cast_set_uri(host, port, control_info, uri, **kwargs)
            else:
                # Try UPnP as fallback
                return await self._upnp_set_uri(host, port, control_info, uri, metadata, **kwargs)
                
        except Exception as e:
            logger.error(f"Set URI operation failed on {host}:{port}: {e}")
            raise MediaControlError(f"Set URI failed: {e}")
    
    # === VOLUME CONTROLS ===
    
    async def get_volume(self, 
                         host: str, 
                         port: int,
                         device_info: Optional[Dict[str, Any]] = None,
                         **kwargs) -> Dict[str, Any]:
        """
        Get current volume level.
        
        Args:
            host: Device IP address
            port: Device port
            device_info: Device information for protocol selection
            **kwargs: Additional protocol-specific parameters
            
        Returns:
            Volume information
        """
        try:
            control_info = get_device_control_info(device_info or {})
            protocol = control_info.get('protocol', 'upnp')
            
            if protocol == 'upnp':
                return await self._upnp_get_volume(host, port, control_info, **kwargs)
            elif protocol == 'samsung_wam':
                return await self._samsung_wam_get_volume(host, port, control_info, **kwargs)
            else:
                # Many protocols don't support volume query
                return {"status": "not_supported", "protocol": protocol}
                
        except Exception as e:
            logger.error(f"Get volume operation failed on {host}:{port}: {e}")
            raise MediaControlError(f"Get volume failed: {e}")
    
    async def set_volume(self, 
                         host: str, 
                         port: int,
                         level: int,
                         device_info: Optional[Dict[str, Any]] = None,
                         **kwargs) -> Dict[str, Any]:
        """
        Set volume level.
        
        Args:
            host: Device IP address
            port: Device port
            level: Volume level (0-100)
            device_info: Device information for protocol selection
            **kwargs: Additional protocol-specific parameters
            
        Returns:
            Control operation result
        """
        try:
            # Validate volume level
            if not 0 <= level <= 100:
                raise MediaControlError(f"Volume level must be 0-100, got {level}")
            
            control_info = get_device_control_info(device_info or {})
            protocol = control_info.get('protocol', 'upnp')
            
            if protocol == 'upnp':
                return await self._upnp_set_volume(host, port, control_info, level, **kwargs)
            elif protocol == 'samsung_wam':
                return await self._samsung_wam_set_volume(host, port, control_info, level, **kwargs)
            else:
                # Many protocols don't support volume control
                return {"status": "not_supported", "protocol": protocol}
                
        except Exception as e:
            logger.error(f"Set volume operation failed on {host}:{port}: {e}")
            raise MediaControlError(f"Set volume failed: {e}")
    
    async def get_mute(self, 
                       host: str, 
                       port: int,
                       device_info: Optional[Dict[str, Any]] = None,
                       **kwargs) -> Dict[str, Any]:
        """
        Get mute status.
        
        Args:
            host: Device IP address
            port: Device port
            device_info: Device information for protocol selection
            **kwargs: Additional protocol-specific parameters
            
        Returns:
            Mute status information
        """
        try:
            control_info = get_device_control_info(device_info or {})
            protocol = control_info.get('protocol', 'upnp')
            
            if protocol == 'upnp':
                return await self._upnp_get_mute(host, port, control_info, **kwargs)
            else:
                # Many protocols don't support mute query
                return {"status": "not_supported", "protocol": protocol}
                
        except Exception as e:
            logger.error(f"Get mute operation failed on {host}:{port}: {e}")
            raise MediaControlError(f"Get mute failed: {e}")
    
    async def set_mute(self, 
                       host: str, 
                       port: int,
                       muted: bool,
                       device_info: Optional[Dict[str, Any]] = None,
                       **kwargs) -> Dict[str, Any]:
        """
        Set mute status.
        
        Args:
            host: Device IP address
            port: Device port
            muted: True to mute, False to unmute
            device_info: Device information for protocol selection
            **kwargs: Additional protocol-specific parameters
            
        Returns:
            Control operation result
        """
        try:
            control_info = get_device_control_info(device_info or {})
            protocol = control_info.get('protocol', 'upnp')
            
            if protocol == 'upnp':
                return await self._upnp_set_mute(host, port, control_info, muted, **kwargs)
            else:
                # Many protocols don't support mute control
                return {"status": "not_supported", "protocol": protocol}
                
        except Exception as e:
            logger.error(f"Set mute operation failed on {host}:{port}: {e}")
            raise MediaControlError(f"Set mute failed: {e}")
    
    # === UPnP PROTOCOL IMPLEMENTATIONS ===
    
    async def _upnp_play(self, host: str, port: int, control_info: Dict, **kwargs) -> Dict[str, Any]:
        """UPnP Play implementation."""
        service_url = control_info.get('avtransport_url', '/MediaRenderer/AVTransport/Control')
        service_type = "urn:schemas-upnp-org:service:AVTransport:1"
        
        async with aiohttp.ClientSession() as session:
            response = await self.soap_client.send_soap_request_async(
                session, host, port, service_url, service_type, "Play",
                {"InstanceID": 0, "Speed": "1"}
            )
            
            if response.status == 200:
                return {"status": "success", "action": "play", "protocol": "upnp"}
            else:
                raise MediaControlError(f"UPnP Play failed with status {response.status}")
    
    async def _upnp_pause(self, host: str, port: int, control_info: Dict, **kwargs) -> Dict[str, Any]:
        """UPnP Pause implementation."""
        service_url = control_info.get('avtransport_url', '/MediaRenderer/AVTransport/Control')
        service_type = "urn:schemas-upnp-org:service:AVTransport:1"
        
        async with aiohttp.ClientSession() as session:
            response = await self.soap_client.send_soap_request_async(
                session, host, port, service_url, service_type, "Pause",
                {"InstanceID": 0}
            )
            
            if response.status == 200:
                return {"status": "success", "action": "pause", "protocol": "upnp"}
            else:
                raise MediaControlError(f"UPnP Pause failed with status {response.status}")
    
    async def _upnp_stop(self, host: str, port: int, control_info: Dict, **kwargs) -> Dict[str, Any]:
        """UPnP Stop implementation."""
        service_url = control_info.get('avtransport_url', '/MediaRenderer/AVTransport/Control')
        service_type = "urn:schemas-upnp-org:service:AVTransport:1"
        
        async with aiohttp.ClientSession() as session:
            response = await self.soap_client.send_soap_request_async(
                session, host, port, service_url, service_type, "Stop",
                {"InstanceID": 0}
            )
            
            if response.status == 200:
                return {"status": "success", "action": "stop", "protocol": "upnp"}
            else:
                raise MediaControlError(f"UPnP Stop failed with status {response.status}")
    
    async def _upnp_next(self, host: str, port: int, control_info: Dict, **kwargs) -> Dict[str, Any]:
        """UPnP Next implementation."""
        service_url = control_info.get('avtransport_url', '/MediaRenderer/AVTransport/Control')
        service_type = "urn:schemas-upnp-org:service:AVTransport:1"
        
        async with aiohttp.ClientSession() as session:
            response = await self.soap_client.send_soap_request_async(
                session, host, port, service_url, service_type, "Next",
                {"InstanceID": 0}
            )
            
            if response.status == 200:
                return {"status": "success", "action": "next", "protocol": "upnp"}
            else:
                raise MediaControlError(f"UPnP Next failed with status {response.status}")
    
    async def _upnp_previous(self, host: str, port: int, control_info: Dict, **kwargs) -> Dict[str, Any]:
        """UPnP Previous implementation."""
        service_url = control_info.get('avtransport_url', '/MediaRenderer/AVTransport/Control')
        service_type = "urn:schemas-upnp-org:service:AVTransport:1"
        
        async with aiohttp.ClientSession() as session:
            response = await self.soap_client.send_soap_request_async(
                session, host, port, service_url, service_type, "Previous",
                {"InstanceID": 0}
            )
            
            if response.status == 200:
                return {"status": "success", "action": "previous", "protocol": "upnp"}
            else:
                raise MediaControlError(f"UPnP Previous failed with status {response.status}")
    
    async def _upnp_seek(self, host: str, port: int, control_info: Dict, position: str, **kwargs) -> Dict[str, Any]:
        """UPnP Seek implementation."""
        service_url = control_info.get('avtransport_url', '/MediaRenderer/AVTransport/Control')
        service_type = "urn:schemas-upnp-org:service:AVTransport:1"
        
        # Convert position to proper format if needed
        if position.isdigit():
            # Convert seconds to HH:MM:SS
            seconds = int(position)
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            seconds = seconds % 60
            position = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        
        async with aiohttp.ClientSession() as session:
            response = await self.soap_client.send_soap_request_async(
                session, host, port, service_url, service_type, "Seek",
                {"InstanceID": 0, "Unit": "REL_TIME", "Target": position}
            )
            
            if response.status == 200:
                return {"status": "success", "action": "seek", "position": position, "protocol": "upnp"}
            else:
                raise MediaControlError(f"UPnP Seek failed with status {response.status}")
    
    async def _upnp_set_uri(self, host: str, port: int, control_info: Dict, uri: str, metadata: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """UPnP SetAVTransportURI implementation."""
        service_url = control_info.get('avtransport_url', '/MediaRenderer/AVTransport/Control')
        service_type = "urn:schemas-upnp-org:service:AVTransport:1"
        
        # Create default DIDL metadata if not provided
        if metadata is None:
            metadata = self._create_didl_metadata(uri)
        
        async with aiohttp.ClientSession() as session:
            response = await self.soap_client.send_soap_request_async(
                session, host, port, service_url, service_type, "SetAVTransportURI",
                {"InstanceID": 0, "CurrentURI": uri, "CurrentURIMetaData": metadata}
            )
            
            if response.status == 200:
                return {"status": "success", "action": "set_uri", "uri": uri, "protocol": "upnp"}
            else:
                raise MediaControlError(f"UPnP SetAVTransportURI failed with status {response.status}")
    
    async def _upnp_get_volume(self, host: str, port: int, control_info: Dict, **kwargs) -> Dict[str, Any]:
        """UPnP GetVolume implementation."""
        service_url = control_info.get('rendering_url', '/MediaRenderer/RenderingControl/Control')
        service_type = "urn:schemas-upnp-org:service:RenderingControl:1"
        
        async with aiohttp.ClientSession() as session:
            response = await self.soap_client.send_soap_request_async(
                session, host, port, service_url, service_type, "GetVolume",
                {"InstanceID": 0, "Channel": "Master"}
            )
            
            if response.status == 200:
                # Parse response for volume value
                response_text = await response.text()
                volume = self._parse_soap_response_value(response_text, "CurrentVolume")
                return {"status": "success", "volume": int(volume) if volume else 0, "protocol": "upnp"}
            else:
                raise MediaControlError(f"UPnP GetVolume failed with status {response.status}")
    
    async def _upnp_set_volume(self, host: str, port: int, control_info: Dict, level: int, **kwargs) -> Dict[str, Any]:
        """UPnP SetVolume implementation."""
        service_url = control_info.get('rendering_url', '/MediaRenderer/RenderingControl/Control')
        service_type = "urn:schemas-upnp-org:service:RenderingControl:1"
        
        async with aiohttp.ClientSession() as session:
            response = await self.soap_client.send_soap_request_async(
                session, host, port, service_url, service_type, "SetVolume",
                {"InstanceID": 0, "Channel": "Master", "DesiredVolume": level}
            )
            
            if response.status == 200:
                return {"status": "success", "action": "set_volume", "volume": level, "protocol": "upnp"}
            else:
                raise MediaControlError(f"UPnP SetVolume failed with status {response.status}")
    
    async def _upnp_get_mute(self, host: str, port: int, control_info: Dict, **kwargs) -> Dict[str, Any]:
        """UPnP GetMute implementation."""
        service_url = control_info.get('rendering_url', '/MediaRenderer/RenderingControl/Control')
        service_type = "urn:schemas-upnp-org:service:RenderingControl:1"
        
        async with aiohttp.ClientSession() as session:
            response = await self.soap_client.send_soap_request_async(
                session, host, port, service_url, service_type, "GetMute",
                {"InstanceID": 0, "Channel": "Master"}
            )
            
            if response.status == 200:
                # Parse response for mute value
                response_text = await response.text()
                mute = self._parse_soap_response_value(response_text, "CurrentMute")
                return {"status": "success", "muted": mute == "1", "protocol": "upnp"}
            else:
                raise MediaControlError(f"UPnP GetMute failed with status {response.status}")
    
    async def _upnp_set_mute(self, host: str, port: int, control_info: Dict, muted: bool, **kwargs) -> Dict[str, Any]:
        """UPnP SetMute implementation."""
        service_url = control_info.get('rendering_url', '/MediaRenderer/RenderingControl/Control')
        service_type = "urn:schemas-upnp-org:service:RenderingControl:1"
        
        async with aiohttp.ClientSession() as session:
            response = await self.soap_client.send_soap_request_async(
                session, host, port, service_url, service_type, "SetMute",
                {"InstanceID": 0, "Channel": "Master", "DesiredMute": "1" if muted else "0"}
            )
            
            if response.status == 200:
                return {"status": "success", "action": "set_mute", "muted": muted, "protocol": "upnp"}
            else:
                raise MediaControlError(f"UPnP SetMute failed with status {response.status}")
    
    # === ECP PROTOCOL IMPLEMENTATIONS ===
    
    async def _ecp_play(self, host: str, port: int, control_info: Dict, **kwargs) -> Dict[str, Any]:
        """ECP Play implementation (Roku)."""
        # For ECP, play is typically done by sending a key press
        async with aiohttp.ClientSession() as session:
            url = f"http://{host}:{port}/keypress/Play"
            async with session.post(url) as response:
                if response.status == 200:
                    return {"status": "success", "action": "play", "protocol": "ecp"}
                else:
                    raise MediaControlError(f"ECP Play failed with status {response.status}")
    
    async def _ecp_pause(self, host: str, port: int, control_info: Dict, **kwargs) -> Dict[str, Any]:
        """ECP Pause implementation (Roku)."""
        async with aiohttp.ClientSession() as session:
            url = f"http://{host}:{port}/keypress/PlayPause"
            async with session.post(url) as response:
                if response.status == 200:
                    return {"status": "success", "action": "pause", "protocol": "ecp"}
                else:
                    raise MediaControlError(f"ECP Pause failed with status {response.status}")
    
    async def _ecp_stop(self, host: str, port: int, control_info: Dict, **kwargs) -> Dict[str, Any]:
        """ECP Stop implementation (Roku)."""
        async with aiohttp.ClientSession() as session:
            url = f"http://{host}:{port}/keypress/Home"
            async with session.post(url) as response:
                if response.status == 200:
                    return {"status": "success", "action": "stop", "protocol": "ecp"}
                else:
                    raise MediaControlError(f"ECP Stop failed with status {response.status}")
    
    async def _ecp_set_uri(self, host: str, port: int, control_info: Dict, uri: str, **kwargs) -> Dict[str, Any]:
        """ECP Set URI implementation (Roku Media Player)."""
        # First launch Media Player
        async with aiohttp.ClientSession() as session:
            launch_url = f"http://{host}:{port}/launch/2213"
            async with session.post(launch_url) as response:
                if response.status != 200:
                    raise MediaControlError(f"ECP launch failed with status {response.status}")
            
            # Wait a moment for app to load
            await asyncio.sleep(2)
            
            # Send media URL
            input_url = f"http://{host}:{port}/input"
            data = f"mediaType=audio&url={uri}&loop=true"
            headers = {"Content-Type": "application/x-www-form-urlencoded"}
            
            async with session.post(input_url, data=data, headers=headers) as response:
                if response.status == 200:
                    return {"status": "success", "action": "set_uri", "uri": uri, "protocol": "ecp"}
                else:
                    raise MediaControlError(f"ECP set URI failed with status {response.status}")
    
    # === SAMSUNG WAM PROTOCOL IMPLEMENTATIONS ===
    
    async def _samsung_wam_play(self, host: str, port: int, control_info: Dict, **kwargs) -> Dict[str, Any]:
        """Samsung WAM Play implementation."""
        # Samsung WAM doesn't have a separate play command, playback starts with SetUrlPlayback
        return {"status": "success", "action": "play", "protocol": "samsung_wam", "note": "Use set_uri to start playback"}
    
    async def _samsung_wam_pause(self, host: str, port: int, control_info: Dict, **kwargs) -> Dict[str, Any]:
        """Samsung WAM Pause implementation."""
        # Samsung WAM typically uses SetPlaybackControl for pause
        cmd = "<n>SetPlaybackControl</n><p type=\"str\" name=\"playback\" val=\"pause\"/>"
        return await self._samsung_wam_send_command(host, port, cmd)
    
    async def _samsung_wam_stop(self, host: str, port: int, control_info: Dict, **kwargs) -> Dict[str, Any]:
        """Samsung WAM Stop implementation."""
        cmd = "<n>SetPlaybackControl</n><p type=\"str\" name=\"playback\" val=\"stop\"/>"
        return await self._samsung_wam_send_command(host, port, cmd)
    
    async def _samsung_wam_set_uri(self, host: str, port: int, control_info: Dict, uri: str, **kwargs) -> Dict[str, Any]:
        """Samsung WAM Set URI implementation."""
        cmd = f"<n>SetUrlPlayback</n><p type=\"cdata\" name=\"url\" val=\"empty\"><![CDATA[{uri}]]></p><p type=\"dec\" name=\"buffersize\" val=\"0\"/><p type=\"dec\" name=\"seektime\" val=\"0\"/><p type=\"dec\" name=\"resume\" val=\"1\"/>"
        return await self._samsung_wam_send_command(host, port, cmd)
    
    async def _samsung_wam_get_volume(self, host: str, port: int, control_info: Dict, **kwargs) -> Dict[str, Any]:
        """Samsung WAM Get Volume implementation."""
        cmd = "<n>GetVolume</n>"
        return await self._samsung_wam_send_command(host, port, cmd)
    
    async def _samsung_wam_set_volume(self, host: str, port: int, control_info: Dict, level: int, **kwargs) -> Dict[str, Any]:
        """Samsung WAM Set Volume implementation."""
        cmd = f"<n>SetVolume</n><p type=\"dec\" name=\"volume\" val=\"{level}\"/>"
        return await self._samsung_wam_send_command(host, port, cmd)
    
    async def _samsung_wam_send_command(self, host: str, port: int, cmd: str) -> Dict[str, Any]:
        """Send command to Samsung WAM device."""
        async with aiohttp.ClientSession() as session:
            url = f"http://{host}:{port}/UIC?cmd={cmd}"
            async with session.get(url) as response:
                if response.status == 200:
                    response_text = await response.text()
                    return {"status": "success", "protocol": "samsung_wam", "response": response_text}
                else:
                    raise MediaControlError(f"Samsung WAM command failed with status {response.status}")
    
    # === CAST PROTOCOL IMPLEMENTATIONS ===
    
    async def _cast_play(self, host: str, port: int, control_info: Dict, **kwargs) -> Dict[str, Any]:
        """Cast Play implementation (placeholder)."""
        # Cast protocol requires WebSocket implementation
        return {"status": "not_implemented", "protocol": "cast", "note": "Cast protocol requires WebSocket client"}
    
    async def _cast_pause(self, host: str, port: int, control_info: Dict, **kwargs) -> Dict[str, Any]:
        """Cast Pause implementation (placeholder)."""
        return {"status": "not_implemented", "protocol": "cast", "note": "Cast protocol requires WebSocket client"}
    
    async def _cast_stop(self, host: str, port: int, control_info: Dict, **kwargs) -> Dict[str, Any]:
        """Cast Stop implementation (placeholder)."""
        return {"status": "not_implemented", "protocol": "cast", "note": "Cast protocol requires WebSocket client"}
    
    async def _cast_set_uri(self, host: str, port: int, control_info: Dict, uri: str, **kwargs) -> Dict[str, Any]:
        """Cast Set URI implementation (placeholder)."""
        return {"status": "not_implemented", "protocol": "cast", "note": "Cast protocol requires WebSocket client"}
    
    # === UTILITY METHODS ===
    
    def _create_didl_metadata(self, uri: str) -> str:
        """Create basic DIDL-Lite metadata for UPnP."""
        return f'''&lt;DIDL-Lite xmlns="urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:upnp="urn:schemas-upnp-org:metadata-1-0/upnp/"&gt;&lt;item id="1" parentID="0" restricted="1"&gt;&lt;dc:title&gt;Audio Stream&lt;/dc:title&gt;&lt;dc:creator&gt;Unknown&lt;/dc:creator&gt;&lt;upnp:class&gt;object.item.audioItem.musicTrack&lt;/upnp:class&gt;&lt;res protocolInfo="http-get:*:audio/mpeg:*"&gt;{uri}&lt;/res&gt;&lt;/item&gt;&lt;/DIDL-Lite&gt;'''
    
    def _parse_soap_response_value(self, response_text: str, tag_name: str) -> Optional[str]:
        """Parse value from SOAP response."""
        try:
            root = ET.fromstring(response_text)
            # Find the tag with given name
            for elem in root.iter():
                if elem.tag.endswith(tag_name):
                    return elem.text
            return None
        except ET.ParseError:
            logger.error("Failed to parse SOAP response XML")
            return None


# === GLOBAL FUNCTIONS ===

# Global media controller instance
_media_controller = None

def get_media_controller(stealth_mode: bool = False) -> MediaController:
    """
    Get global media controller instance.
    
    Args:
        stealth_mode: Enable stealth mode
        
    Returns:
        MediaController instance
    """
    global _media_controller
    if _media_controller is None:
        _media_controller = MediaController(stealth_mode=stealth_mode)
    return _media_controller


# === CONVENIENCE FUNCTIONS ===

async def play_media(host: str, port: int = 1400, device_info: Optional[Dict] = None, **kwargs) -> Dict[str, Any]:
    """Convenience function to play media on device."""
    controller = get_media_controller(kwargs.get('stealth_mode', False))
    return await controller.play(host, port, device_info, **kwargs)

async def pause_media(host: str, port: int = 1400, device_info: Optional[Dict] = None, **kwargs) -> Dict[str, Any]:
    """Convenience function to pause media on device."""
    controller = get_media_controller(kwargs.get('stealth_mode', False))
    return await controller.pause(host, port, device_info, **kwargs)

async def stop_media(host: str, port: int = 1400, device_info: Optional[Dict] = None, **kwargs) -> Dict[str, Any]:
    """Convenience function to stop media on device."""
    controller = get_media_controller(kwargs.get('stealth_mode', False))
    return await controller.stop(host, port, device_info, **kwargs)

async def set_media_uri(host: str, uri: str, port: int = 1400, metadata: Optional[str] = None, device_info: Optional[Dict] = None, **kwargs) -> Dict[str, Any]:
    """Convenience function to set media URI on device."""
    controller = get_media_controller(kwargs.get('stealth_mode', False))
    return await controller.set_uri(host, port, uri, metadata, device_info, **kwargs)

async def set_volume(host: str, level: int, port: int = 1400, device_info: Optional[Dict] = None, **kwargs) -> Dict[str, Any]:
    """Convenience function to set volume on device."""
    controller = get_media_controller(kwargs.get('stealth_mode', False))
    return await controller.set_volume(host, port, level, device_info, **kwargs)

async def get_volume(host: str, port: int = 1400, device_info: Optional[Dict] = None, **kwargs) -> Dict[str, Any]:
    """Convenience function to get volume from device."""
    controller = get_media_controller(kwargs.get('stealth_mode', False))
    return await controller.get_volume(host, port, device_info, **kwargs)


# === CLI COMPATIBILITY FUNCTIONS ===

async def play(host: str, port: int, use_ssl: bool = False, **kwargs) -> Dict[str, Any]:
    """CLI-compatible play function."""
    return await play_media(host, port, **kwargs)

async def pause(host: str, port: int, use_ssl: bool = False, **kwargs) -> Dict[str, Any]:
    """CLI-compatible pause function."""
    return await pause_media(host, port, **kwargs)

async def stop(host: str, port: int, use_ssl: bool = False, **kwargs) -> Dict[str, Any]:
    """CLI-compatible stop function."""
    return await stop_media(host, port, **kwargs)

async def next_track(host: str, port: int, use_ssl: bool = False, **kwargs) -> Dict[str, Any]:
    """CLI-compatible next track function."""
    controller = get_media_controller(kwargs.get('stealth_mode', False))
    return await controller.next_track(host, port, **kwargs)

async def previous_track(host: str, port: int, use_ssl: bool = False, **kwargs) -> Dict[str, Any]:
    """CLI-compatible previous track function."""
    controller = get_media_controller(kwargs.get('stealth_mode', False))
    return await controller.previous_track(host, port, **kwargs)

async def get_mute(host: str, port: int, use_ssl: bool = False, **kwargs) -> Dict[str, Any]:
    """CLI-compatible get mute function."""
    controller = get_media_controller(kwargs.get('stealth_mode', False))
    return await controller.get_mute(host, port, **kwargs)

async def set_mute(host: str, port: int, muted: bool, use_ssl: bool = False, **kwargs) -> Dict[str, Any]:
    """CLI-compatible set mute function."""
    controller = get_media_controller(kwargs.get('stealth_mode', False))
    return await controller.set_mute(host, port, muted, **kwargs)