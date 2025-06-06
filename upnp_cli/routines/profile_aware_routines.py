#!/usr/bin/env python3
"""
Profile-Aware Routines

Intelligent routines that leverage enhanced profiles with complete SCPD data
to perform complex multi-action sequences with device-specific optimizations.
"""

import asyncio
import json
import time
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

from upnp_cli.profiles import get_profile_manager
from upnp_cli.cli.output import ColoredOutput
import upnp_cli.discovery as discovery
import upnp_cli.soap_client as soap_client
from upnp_cli.logging_utils import get_logger

logger = get_logger(__name__)


class ProfileAwareRoutine:
    """Base class for profile-aware routines."""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.profile = None
        self.device_info = None
        self.soap_client = soap_client.get_soap_client()
    
    async def initialize(self, host: str, port: int = 1400) -> bool:
        """Initialize with device and profile."""
        self.host = host
        self.port = port
        
        # Get device info
        self.device_info = await self._get_device_info()
        if not self.device_info:
            return False
        
        # Match profile
        profile_manager = get_profile_manager()
        self.profile = profile_manager.get_best_profile(self.device_info)
        
        return self.profile is not None
    
    async def _get_device_info(self) -> Optional[Dict[str, Any]]:
        """Get device information."""
        try:
            device_url = f"http://{self.host}:{self.port}/xml/device_description.xml"
            
            import aiohttp
            async with aiohttp.ClientSession() as session:
                return await discovery.fetch_device_description(session, device_url)
        except Exception as e:
            logger.error(f"Failed to get device info: {e}")
            return None
    
    def has_action(self, action_name: str) -> bool:
        """Check if device supports an action."""
        if not isinstance(self.profile.upnp, dict) or 'action_inventory' not in self.profile.upnp:
            return False
        
        action_inventory = self.profile.upnp['action_inventory']
        
        for service_name, actions in action_inventory.items():
            if action_name in actions:
                return True
        
        return False
    
    def get_action_info(self, action_name: str) -> Optional[Dict[str, Any]]:
        """Get action information."""
        if not isinstance(self.profile.upnp, dict) or 'action_inventory' not in self.profile.upnp:
            return None
        
        action_inventory = self.profile.upnp['action_inventory']
        
        for service_name, actions in action_inventory.items():
            if action_name in actions:
                return actions[action_name]
        
        return None
    
    def get_service_for_action(self, action_name: str) -> Optional[Tuple[str, str]]:
        """Get service name and control URL for an action."""
        if not isinstance(self.profile.upnp, dict):
            return None
        
        # Enhanced profile
        if 'action_inventory' in self.profile.upnp:
            action_inventory = self.profile.upnp['action_inventory']
            services = self.profile.upnp.get('services', {})
            
            for service_name, actions in action_inventory.items():
                if action_name in actions:
                    control_url = services.get(service_name, {}).get('controlURL', '')
                    service_type = services.get(service_name, {}).get('serviceType', '')
                    return service_name, control_url, service_type
        
        return None
    
    async def execute_action(self, action_name: str, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute action with profile guidance."""
        if arguments is None:
            arguments = {}
        
        service_info = self.get_service_for_action(action_name)
        if not service_info:
            raise ValueError(f"Action {action_name} not found in profile")
        
        service_name, control_url, service_type = service_info
        full_control_url = f"http://{self.host}:{self.port}{control_url}"
        
        result = await self.soap_client.call_action(
            full_control_url,
            service_type,
            action_name,
            arguments
        )
        
        return result
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the routine - to be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement execute method")


class MediaPlaybackRoutine(ProfileAwareRoutine):
    """Intelligent media playback routine."""
    
    def __init__(self):
        super().__init__(
            "Smart Media Playback",
            "Sets up media playback with device-specific optimizations"
        )
    
    async def execute(self, uri: str, volume: int = None, **kwargs) -> Dict[str, Any]:
        """Execute smart media playback."""
        results = {"status": "success", "actions": []}
        
        ColoredOutput.info(f"🎵 Starting smart media playback for {self.profile.name}")
        
        # Step 1: Stop any current playback
        if self.has_action('Stop'):
            try:
                await self.execute_action('Stop', {'InstanceID': '0'})
                results["actions"].append({"action": "Stop", "status": "success"})
                ColoredOutput.info("  ⏹️  Stopped current playback")
            except Exception as e:
                results["actions"].append({"action": "Stop", "status": "error", "error": str(e)})
        
        # Step 2: Set volume if specified and supported
        if volume is not None and self.has_action('SetVolume'):
            try:
                await self.execute_action('SetVolume', {
                    'InstanceID': '0',
                    'Channel': 'Master',
                    'DesiredVolume': str(volume)
                })
                results["actions"].append({"action": "SetVolume", "status": "success", "volume": volume})
                ColoredOutput.info(f"  🔊 Set volume to {volume}")
            except Exception as e:
                results["actions"].append({"action": "SetVolume", "status": "error", "error": str(e)})
        
        # Step 3: Set current URI
        if self.has_action('SetAVTransportURI'):
            try:
                await self.execute_action('SetAVTransportURI', {
                    'InstanceID': '0',
                    'CurrentURI': uri,
                    'CurrentURIMetaData': ''
                })
                results["actions"].append({"action": "SetAVTransportURI", "status": "success", "uri": uri})
                ColoredOutput.info(f"  📡 Set media URI: {uri}")
            except Exception as e:
                results["actions"].append({"action": "SetAVTransportURI", "status": "error", "error": str(e)})
                return results
        
        # Step 4: Start playback
        if self.has_action('Play'):
            try:
                await self.execute_action('Play', {
                    'InstanceID': '0',
                    'Speed': '1'
                })
                results["actions"].append({"action": "Play", "status": "success"})
                ColoredOutput.success("  ▶️  Started playback")
            except Exception as e:
                results["actions"].append({"action": "Play", "status": "error", "error": str(e)})
        
        return results


class VolumeControlRoutine(ProfileAwareRoutine):
    """Intelligent volume control routine."""
    
    def __init__(self):
        super().__init__(
            "Smart Volume Control",
            "Advanced volume control with fade and safety limits"
        )
    
    async def execute(self, target_volume: int, fade_duration: float = 0, **kwargs) -> Dict[str, Any]:
        """Execute smart volume control with optional fading."""
        results = {"status": "success", "actions": []}
        
        ColoredOutput.info(f"🔊 Smart volume control: target {target_volume}%")
        
        if not self.has_action('GetVolume') or not self.has_action('SetVolume'):
            return {"status": "error", "message": "Volume control actions not supported"}
        
        # Get current volume
        try:
            current_result = await self.execute_action('GetVolume', {
                'InstanceID': '0',
                'Channel': 'Master'
            })
            current_volume = int(current_result.get('CurrentVolume', 0))
            results["current_volume"] = current_volume
            ColoredOutput.info(f"  📊 Current volume: {current_volume}%")
        except Exception as e:
            results["actions"].append({"action": "GetVolume", "status": "error", "error": str(e)})
            return results
        
        # Safety check
        if target_volume > 85:
            ColoredOutput.warning(f"  ⚠️  Volume {target_volume}% exceeds safe limit (85%)")
        
        # Implement fading if requested
        if fade_duration > 0 and abs(current_volume - target_volume) > 5:
            ColoredOutput.info(f"  🌊 Fading volume over {fade_duration}s")
            
            steps = max(5, abs(current_volume - target_volume) // 5)
            step_duration = fade_duration / steps
            step_size = (target_volume - current_volume) / steps
            
            for i in range(steps):
                intermediate_volume = int(current_volume + (step_size * (i + 1)))
                
                try:
                    await self.execute_action('SetVolume', {
                        'InstanceID': '0',
                        'Channel': 'Master',
                        'DesiredVolume': str(intermediate_volume)
                    })
                    await asyncio.sleep(step_duration)
                except Exception as e:
                    results["actions"].append({
                        "action": "SetVolume", 
                        "status": "error", 
                        "error": str(e),
                        "step": i
                    })
        else:
            # Direct volume set
            try:
                await self.execute_action('SetVolume', {
                    'InstanceID': '0',
                    'Channel': 'Master',
                    'DesiredVolume': str(target_volume)
                })
                results["actions"].append({"action": "SetVolume", "status": "success", "volume": target_volume})
                ColoredOutput.success(f"  ✅ Volume set to {target_volume}%")
            except Exception as e:
                results["actions"].append({"action": "SetVolume", "status": "error", "error": str(e)})
        
        return results


class DeviceInfoRoutine(ProfileAwareRoutine):
    """Comprehensive device information gathering."""
    
    def __init__(self):
        super().__init__(
            "Device Information Gathering",
            "Gathers comprehensive device state and capabilities"
        )
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute comprehensive device information gathering."""
        results = {
            "status": "success",
            "device_info": {},
            "media_info": {},
            "volume_info": {},
            "capabilities": {}
        }
        
        ColoredOutput.info(f"ℹ️  Gathering comprehensive device information")
        
        # Gather media transport information
        if self.has_action('GetTransportInfo'):
            try:
                transport_info = await self.execute_action('GetTransportInfo', {'InstanceID': '0'})
                results["media_info"]["transport"] = transport_info
                ColoredOutput.info(f"  🎵 Transport State: {transport_info.get('CurrentTransportState', 'Unknown')}")
            except Exception as e:
                logger.error(f"Failed to get transport info: {e}")
        
        # Gather position information
        if self.has_action('GetPositionInfo'):
            try:
                position_info = await self.execute_action('GetPositionInfo', {'InstanceID': '0'})
                results["media_info"]["position"] = position_info
                
                track_duration = position_info.get('TrackDuration', '00:00:00')
                rel_time = position_info.get('RelTime', '00:00:00')
                ColoredOutput.info(f"  ⏱️  Position: {rel_time} / {track_duration}")
            except Exception as e:
                logger.error(f"Failed to get position info: {e}")
        
        # Gather volume information
        if self.has_action('GetVolume'):
            try:
                volume_info = await self.execute_action('GetVolume', {
                    'InstanceID': '0',
                    'Channel': 'Master'
                })
                results["volume_info"]["current"] = volume_info
                ColoredOutput.info(f"  🔊 Volume: {volume_info.get('CurrentVolume', 'Unknown')}%")
            except Exception as e:
                logger.error(f"Failed to get volume info: {e}")
        
        # Gather mute status
        if self.has_action('GetMute'):
            try:
                mute_info = await self.execute_action('GetMute', {
                    'InstanceID': '0',
                    'Channel': 'Master'
                })
                results["volume_info"]["mute"] = mute_info
                is_muted = mute_info.get('CurrentMute', '0') == '1'
                ColoredOutput.info(f"  🔇 Muted: {'Yes' if is_muted else 'No'}")
            except Exception as e:
                logger.error(f"Failed to get mute info: {e}")
        
        # Add profile capabilities
        if isinstance(self.profile.upnp, dict) and 'capabilities' in self.profile.upnp:
            results["capabilities"] = self.profile.upnp['capabilities']
            total_actions = sum(len(actions) for actions in self.profile.upnp['capabilities'].values())
            ColoredOutput.info(f"  🎯 Total Available Actions: {total_actions}")
        
        return results


class NetworkScanRoutine(ProfileAwareRoutine):
    """Profile-aware network scanning routine."""
    
    def __init__(self):
        super().__init__(
            "Profile-Aware Network Scan",
            "Scans network and matches devices to enhanced profiles"
        )
    
    async def execute(self, network: str = None, **kwargs) -> Dict[str, Any]:
        """Execute profile-aware network scan."""
        results = {
            "status": "success",
            "devices": [],
            "profile_matches": {},
            "enhanced_devices": []
        }
        
        ColoredOutput.header("🌐 Profile-Aware Network Scan")
        
        # Discover devices
        if not network:
            import upnp_cli.utils as utils
            network = utils.get_en0_network()[1]
        
        ColoredOutput.info(f"Scanning network: {network}")
        
        devices = await discovery.scan_network_async(network, use_cache=False)
        results["devices"] = devices
        
        if not devices:
            ColoredOutput.warning("No devices found")
            return results
        
        ColoredOutput.success(f"Found {len(devices)} devices")
        
        # Match devices to profiles
        profile_manager = get_profile_manager()
        
        for device in devices:
            device_name = device.get('friendlyName', f"{device.get('ip')}:{device.get('port')}")
            
            # Try to match profile
            profile = profile_manager.get_best_profile(device)
            
            if profile:
                results["profile_matches"][device_name] = {
                    "profile_name": profile.name,
                    "device_info": device,
                    "enhanced": isinstance(profile.upnp, dict) and 'action_inventory' in profile.upnp
                }
                
                if isinstance(profile.upnp, dict) and 'action_inventory' in profile.upnp:
                    results["enhanced_devices"].append({
                        "name": device_name,
                        "profile": profile.name,
                        "ip": device.get('ip'),
                        "port": device.get('port'),
                        "total_actions": sum(
                            len(actions) for actions in profile.upnp['action_inventory'].values()
                        )
                    })
                    ColoredOutput.success(f"  ✅ {device_name} -> Enhanced Profile: {profile.name}")
                else:
                    ColoredOutput.info(f"  📋 {device_name} -> Basic Profile: {profile.name}")
            else:
                ColoredOutput.warning(f"  ❌ {device_name} -> No matching profile")
        
        # Summary
        enhanced_count = len(results["enhanced_devices"])
        ColoredOutput.print(f"\n📊 Scan Summary:", 'cyan', bold=True)
        ColoredOutput.print(f"  Total Devices: {len(devices)}", 'white')
        ColoredOutput.print(f"  Profile Matches: {len(results['profile_matches'])}", 'white')
        ColoredOutput.print(f"  Enhanced Profiles: {enhanced_count}", 'green', bold=True)
        
        return results


# Routine registry
AVAILABLE_ROUTINES = {
    'media_playback': MediaPlaybackRoutine,
    'volume_control': VolumeControlRoutine,
    'device_info': DeviceInfoRoutine,
    'network_scan': NetworkScanRoutine
}


async def execute_profile_routine(routine_name: str, host: str = None, port: int = 1400, **kwargs) -> Dict[str, Any]:
    """Execute a profile-aware routine."""
    
    if routine_name not in AVAILABLE_ROUTINES:
        return {"status": "error", "message": f"Unknown routine: {routine_name}"}
    
    routine_class = AVAILABLE_ROUTINES[routine_name]
    routine = routine_class()
    
    ColoredOutput.header(f"🤖 Executing: {routine.name}")
    ColoredOutput.info(f"Description: {routine.description}")
    
    # Special handling for network scan (doesn't need device initialization)
    if routine_name == 'network_scan':
        return await routine.execute(**kwargs)
    
    # Initialize with device
    if not host:
        return {"status": "error", "message": "Host required for device-specific routines"}
    
    if not await routine.initialize(host, port):
        return {"status": "error", "message": "Failed to initialize routine with device"}
    
    # Execute routine
    try:
        result = await routine.execute(**kwargs)
        ColoredOutput.success(f"✅ Routine '{routine.name}' completed successfully")
        return result
    except Exception as e:
        ColoredOutput.error(f"❌ Routine '{routine.name}' failed: {e}")
        return {"status": "error", "message": str(e)}


def list_available_routines() -> List[Dict[str, str]]:
    """List all available profile-aware routines."""
    routines = []
    
    for name, routine_class in AVAILABLE_ROUTINES.items():
        routine = routine_class()
        routines.append({
            "name": name,
            "title": routine.name,
            "description": routine.description
        })
    
    return routines


async def cmd_profile_routine(args) -> Dict[str, Any]:
    """Command entry point for profile-aware routines."""
    
    # List available routines
    if args.list_routines:
        routines = list_available_routines()
        ColoredOutput.header("🤖 Available Profile-Aware Routines")
        
        for routine in routines:
            ColoredOutput.print(f"\n🔧 {routine['name']}", 'cyan', bold=True)
            ColoredOutput.print(f"   {routine['title']}", 'white')
            ColoredOutput.print(f"   {routine['description']}", 'gray')
        
        return {"status": "success", "routines": routines}
    
    # Execute specific routine
    routine_name = args.routine
    if not routine_name:
        return {"status": "error", "message": "No routine specified"}
    
    # Prepare kwargs from args
    kwargs = {}
    
    if hasattr(args, 'uri') and args.uri:
        kwargs['uri'] = args.uri
    if hasattr(args, 'volume') and args.volume is not None:
        kwargs['target_volume'] = args.volume
    if hasattr(args, 'fade_duration') and args.fade_duration:
        kwargs['fade_duration'] = args.fade_duration
    if hasattr(args, 'network') and args.network:
        kwargs['network'] = args.network
    
    # Execute routine
    return await execute_profile_routine(
        routine_name,
        host=args.host,
        port=args.port,
        **kwargs
    ) 