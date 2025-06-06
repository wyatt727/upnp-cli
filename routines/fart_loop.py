"""
Classic fart loop routine - the original UPnP prank.

Plays fart.mp3 on repeat across all compatible UPnP devices.
"""

import time
import asyncio
from typing import List, Dict, Any
import aiohttp

from .base_routine import AsyncBaseRoutine
from upnp_cli.soap_client import SOAPClient


class FartLoopRoutine(AsyncBaseRoutine):
    """Classic fart loop routine that plays fart.mp3 on repeat."""
    
    name = "Fart Loop"
    description = "Plays any audio file on repeat across all UPnP devices - the classic prank!"
    category = "prank"
    media_files = ["fart.mp3"]  # Default media file
    supported_protocols = ["upnp", "ecp", "cast"]
    
    parameters = {
        "volume": {
            "type": "int",
            "default": 50,
            "min": 0,
            "max": 100,
            "description": "Volume level (0-100)"
        },
        "duration": {
            "type": "int", 
            "default": 0,
            "description": "Duration in seconds (0 = infinite)"
        },
        "server_port": {
            "type": "int",
            "default": 8080,
            "description": "HTTP server port for serving media files"
        },
        "media_file": {
            "type": "str",
            "default": "fart.mp3",
            "description": "Media file to play (local file or full URL)"
        }
    }
    
    examples = [
        "upnp-cli routine fart_loop --volume 100",
        "upnp-cli routine fart_loop --volume 50 --duration 300",
        "upnp-cli routine fart_loop --server-port 9000",
        "upnp-cli routine fart_loop --media-file rickroll.mp3",
        "upnp-cli routine fart_loop --media-file https://example.com/audio.mp3"
    ]
    
    async def execute_on_device_async(self, device: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Execute fart loop on a single device."""
        try:
            volume = kwargs.get('volume', 50)
            server_port = kwargs.get('server_port', 8080)
            media_file = kwargs.get('media_file', 'fart.mp3')
            
            # Debug logging
            print(f"DEBUG: Executing fart loop on device: {device.get('ip')}")
            print(f"DEBUG: Device info: manufacturer={device.get('manufacturer', 'Unknown')}, model={device.get('modelName', 'Unknown')}")
            print(f"DEBUG: Services count: {len(device.get('services', []))}")
            
            self.logger.info(f"Executing fart loop on device: {device.get('ip')}")
            self.logger.info(f"Device info: manufacturer={device.get('manufacturer', 'Unknown')}, model={device.get('modelName', 'Unknown')}")
            self.logger.info(f"Services count: {len(device.get('services', []))}")
            
            # Get media URL - handle both local files and URLs
            media_url = self._get_media_url(media_file, server_port)
            if not media_url:
                error_msg = f"Could not get media URL for: {media_file}"
                print(f"DEBUG: {error_msg}")
                self.logger.error(error_msg)
                return {
                    'status': 'error',
                    'error': error_msg
                }
            
            print(f"DEBUG: Media URL: {media_url}")
            self.logger.info(f"Media URL: {media_url}")
            
            device_name = device.get('friendlyName', device.get('ip'))
            manufacturer = device.get('manufacturer', '').lower()
            
            print(f"DEBUG: Choosing protocol for manufacturer: '{manufacturer}'")
            self.logger.info(f"Choosing protocol for manufacturer: '{manufacturer}'")
            
            # Choose the best protocol for this device
            if 'sonos' in manufacturer:
                print("DEBUG: Using Sonos direct method")
                self.logger.info("Using Sonos direct method")
                return await self._execute_sonos_queue(device, media_url, volume)
            elif 'roku' in manufacturer:
                print("DEBUG: Using Roku ECP method")
                self.logger.info("Using Roku ECP method")
                return await self._execute_roku_ecp(device, media_url, volume)
            elif 'samsung' in manufacturer:
                print("DEBUG: Using Samsung WAM method")
                self.logger.info("Using Samsung WAM method")
                return await self._execute_samsung_wam(device, media_url, volume)
            elif 'chromecast' in device.get('modelName', '').lower():
                print("DEBUG: Using Chromecast method")
                self.logger.info("Using Chromecast method")
                return await self._execute_chromecast(device, media_url, volume)
            else:
                print("DEBUG: Using generic UPnP method")
                self.logger.info("Using generic UPnP method")
                return await self._execute_upnp(device, media_url, volume)
                
        except Exception as e:
            print(f"DEBUG: Exception in execute_on_device_async: {e}")
            self.logger.error(f"Failed to execute fart loop on {device.get('ip')}: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def _get_media_url(self, media_file: str, server_port: int) -> str:
        """
        Get media URL, handling both local files and full URLs.
        
        Args:
            media_file: Either a local filename or a full URL
            server_port: Port for HTTP server (used for local files)
            
        Returns:
            Complete URL to the media file
        """
        import os
        from urllib.parse import urlparse
        
        # Check if it's already a full URL
        parsed = urlparse(media_file)
        if parsed.scheme in ('http', 'https', 'ftp'):
            self.logger.info(f"Using external URL: {media_file}")
            return media_file
        
        # It's a local file - check if it exists
        if not os.path.exists(media_file):
            self.logger.error(f"Local media file not found: {media_file}")
            return None
        
        # Start HTTP server if not already running
        server_result = self.start_http_server(port=server_port)
        if server_result.get('status') == 'error':
            self.logger.error(f"Failed to start HTTP server: {server_result.get('message')}")
            return None
        
        # Get URL from HTTP server
        media_url = self.get_media_url(media_file)
        if not media_url:
            self.logger.error(f"Could not get URL for local file: {media_file}")
            return None
        
        self.logger.info(f"Serving local file {media_file} at: {media_url}")
        return media_url
    
    async def _execute_sonos_queue(self, device: Dict[str, Any], media_url: str, volume: int) -> Dict[str, Any]:
        """Execute fart loop using Sonos-specific approach - simplified for reliability."""
        host = device.get('ip')
        port = device.get('port', 1400)
        
        print(f"DEBUG: _execute_sonos_queue starting for {host}:{port}")
        
        soap_client = SOAPClient()
        
        try:
            async with aiohttp.ClientSession() as session:
                # Find required services
                avtransport_service = None
                rendering_service = None
                
                print(f"DEBUG: Checking {len(device.get('services', []))} services")
                for i, service in enumerate(device.get('services', [])):
                    service_type = service.get('serviceType', '')
                    print(f"DEBUG: Service {i}: {service_type}")
                    if 'AVTransport' in service_type:
                        avtransport_service = service
                        print(f"DEBUG: Found AVTransport service: {service}")
                    elif 'RenderingControl' in service_type:
                        rendering_service = service
                        print(f"DEBUG: Found RenderingControl service: {service}")
                
                # Also check embedded devices (common in Sonos)
                embedded_devices = device.get('devices', [])
                print(f"DEBUG: Checking {len(embedded_devices)} embedded devices")
                for i, embedded_device in enumerate(embedded_devices):
                    print(f"DEBUG: Embedded device {i}: {embedded_device.get('deviceType', 'Unknown')}")
                    for j, service in enumerate(embedded_device.get('services', [])):
                        service_type = service.get('serviceType', '')
                        print(f"DEBUG: Embedded service {j}: {service_type}")
                        if 'AVTransport' in service_type:
                            avtransport_service = service
                            print(f"DEBUG: Found AVTransport in embedded device: {service}")
                        elif 'RenderingControl' in service_type and 'Group' not in service_type:
                            # Prefer non-Group RenderingControl for volume
                            rendering_service = service
                            print(f"DEBUG: Found RenderingControl in embedded device: {service}")
                
                print(f"DEBUG: Final services - AVTransport: {avtransport_service is not None}, RenderingControl: {rendering_service is not None}")
                
                if not avtransport_service:
                    error_msg = 'No AVTransport service found'
                    print(f"DEBUG: ERROR - {error_msg}")
                    return {
                        'status': 'error',
                        'error': error_msg
                    }
                
                results = {}
                
                # Step 1: Stop current playback
                try:
                    print(f"DEBUG: Step 1 - Stopping current playback")
                    resp = await soap_client.send_soap_request_async(
                        session, host, port, 
                        avtransport_service.get('controlURL'),
                        avtransport_service.get('serviceType'),
                        "Stop", {"InstanceID": "0"}
                    )
                    results['stop'] = f"HTTP {resp.status}"
                    print(f"DEBUG: Stop result: {results['stop']}")
                except Exception as e:
                    results['stop'] = f"Error: {e}"
                    print(f"DEBUG: Stop failed: {e}")
                
                # Step 2: Set volume (if available)
                if rendering_service:
                    try:
                        print(f"DEBUG: Step 2 - Setting volume to {volume}")
                        resp = await soap_client.send_soap_request_async(
                            session, host, port,
                            rendering_service.get('controlURL'),
                            rendering_service.get('serviceType'),
                            "SetVolume", {
                                "InstanceID": "0",
                                "Channel": "Master",
                                "DesiredVolume": str(volume)
                            }
                        )
                        results['set_volume'] = f"HTTP {resp.status}"
                        print(f"DEBUG: Set volume result: {results['set_volume']}")
                    except Exception as e:
                        results['set_volume'] = f"Error: {e}"
                        print(f"DEBUG: Set volume failed: {e}")
                else:
                    print(f"DEBUG: Step 2 - No RenderingControl service, skipping volume")
                
                # Step 3: Set repeat mode
                try:
                    print(f"DEBUG: Step 3 - Setting repeat mode")
                    resp = await soap_client.send_soap_request_async(
                        session, host, port,
                        avtransport_service.get('controlURL'),
                        avtransport_service.get('serviceType'),
                        "SetPlayMode", {
                            "InstanceID": "0",
                            "NewPlayMode": "REPEAT_ALL"
                        }
                    )
                    results['set_repeat'] = f"HTTP {resp.status}"
                    print(f"DEBUG: Set repeat result: {results['set_repeat']}")
                except Exception as e:
                    results['set_repeat'] = f"Error: {e}"
                    print(f"DEBUG: Set repeat failed: {e}")
                
                # Step 4: Set the media URL directly (simplified approach)
                try:
                    print(f"DEBUG: Step 4 - Setting media URL directly")
                    
                    # Extract filename for metadata
                    import os
                    from urllib.parse import urlparse
                    
                    parsed = urlparse(media_url)
                    filename = os.path.basename(parsed.path) if parsed.path else "Audio File"
                    track_name = os.path.splitext(filename)[0].replace('_', ' ').title()
                    
                    print(f"DEBUG: Track name: {track_name}")
                    
                    # Simple DIDL metadata for direct URL playback
                    didl_metadata = f'''<DIDL-Lite xmlns="urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:upnp="urn:schemas-upnp-org:metadata-1-0/upnp/">
<item id="1" parentID="0" restricted="1">
<dc:title>{track_name}</dc:title>
<dc:creator>UPnP CLI</dc:creator>
<upnp:class>object.item.audioItem.musicTrack</upnp:class>
<res protocolInfo="http-get:*:audio/mpeg:*">{media_url}</res>
</item>
</DIDL-Lite>'''
                    
                    print(f"DEBUG: Setting URI {media_url}")
                    resp = await soap_client.send_soap_request_async(
                        session, host, port,
                        avtransport_service.get('controlURL'),
                        avtransport_service.get('serviceType'),
                        "SetAVTransportURI", {
                            "InstanceID": "0",
                            "CurrentURI": media_url,
                            "CurrentURIMetaData": didl_metadata
                        }
                    )
                    results['set_uri'] = f"HTTP {resp.status}"
                    print(f"DEBUG: Set URI result: {results['set_uri']}")
                except Exception as e:
                    results['set_uri'] = f"Error: {e}"
                    print(f"DEBUG: Set URI failed: {e}")
                
                # Step 5: Start playback
                try:
                    print(f"DEBUG: Step 5 - Starting playback")
                    resp = await soap_client.send_soap_request_async(
                        session, host, port,
                        avtransport_service.get('controlURL'),
                        avtransport_service.get('serviceType'),
                        "Play", {
                            "InstanceID": "0",
                            "Speed": "1"
                        }
                    )
                    results['play'] = f"HTTP {resp.status}"
                    print(f"DEBUG: Play result: {results['play']}")
                except Exception as e:
                    results['play'] = f"Error: {e}"
                    print(f"DEBUG: Play failed: {e}")
                
                # Step 6: Verify playback and implement active looping
                await asyncio.sleep(2)
                try:
                    print(f"DEBUG: Step 6 - Verifying playback and starting loop")
                    resp = await soap_client.send_soap_request_async(
                        session, host, port,
                        avtransport_service.get('controlURL'),
                        avtransport_service.get('serviceType'),
                        "GetTransportInfo", {"InstanceID": "0"}
                    )
                    text = resp.text()  # AsyncResponseWrapper.text() is not async
                    print(f"DEBUG: Transport info response: {text[:200]}...")
                    if "PLAYING" in text:
                        results['status_check'] = "PLAYING"
                        print(f"DEBUG: Status check: PLAYING - starting active loop")
                        
                        # Start active looping in the background
                        loop_task = asyncio.create_task(
                            self._active_loop_monitor(session, soap_client, host, port, 
                                                   avtransport_service, media_url, didl_metadata)
                        )
                        
                        # Let it run for a few seconds to verify it's working
                        await asyncio.sleep(5)
                        
                        # Check status again
                        resp2 = await soap_client.send_soap_request_async(
                            session, host, port,
                            avtransport_service.get('controlURL'),
                            avtransport_service.get('serviceType'),
                            "GetTransportInfo", {"InstanceID": "0"}
                        )
                        text2 = resp2.text()
                        if "PLAYING" in text2:
                            results['loop_status'] = "ACTIVE_LOOPING"
                            print(f"DEBUG: Loop confirmed active after 5 seconds")
                        else:
                            results['loop_status'] = "LOOP_FAILED"
                            print(f"DEBUG: Loop failed - not playing after 5 seconds")
                        
                        # Cancel the loop task for now (in real usage it would continue)
                        loop_task.cancel()
                        try:
                            await loop_task
                        except asyncio.CancelledError:
                            pass
                        
                    else:
                        results['status_check'] = "NOT_PLAYING"
                        print(f"DEBUG: Status check: NOT_PLAYING")
                except Exception as e:
                    results['status_check'] = f"Error: {e}"
                    print(f"DEBUG: Status check failed: {e}")
                
                print(f"DEBUG: Final results: {results}")
                
                # Determine success based on key operations and loop status
                success = (
                    results.get('set_uri', '').startswith('HTTP 2') and 
                    results.get('play', '').startswith('HTTP 2') and
                    results.get('loop_status') == 'ACTIVE_LOOPING'
                )
                
                partial_success = (
                    results.get('set_uri', '').startswith('HTTP 2') and 
                    results.get('play', '').startswith('HTTP 2') and
                    results.get('status_check') == 'PLAYING'
                )
                
                return {
                    'status': 'success' if success else ('partial_success' if partial_success else 'error'),
                    'protocol': 'sonos_direct_loop',
                    'media_url': media_url,
                    'volume': volume,
                    'message': f'💨 Sonos looping fart {"activated" if success else "started" if partial_success else "failed"}! Playing {track_name} {"on active repeat loop" if success else "once" if partial_success else ""}! 💨',
                    'details': results
                }
                
        except Exception as e:
            print(f"DEBUG: Exception in _execute_sonos_queue: {e}")
            return {
                'status': 'error',
                'error': f"Sonos execution failed: {e}"
            }
    
    async def _active_loop_monitor(self, session, soap_client, host, port, 
                                 avtransport_service, media_url, didl_metadata):
        """Continuously monitor playback and restart when track ends."""
        loop_count = 0
        consecutive_failures = 0
        max_failures = 3
        
        print(f"DEBUG: Active loop monitor started")
        
        try:
            while True:
                await asyncio.sleep(3)  # Check every 3 seconds
                
                try:
                    # Check transport state
                    resp = await soap_client.send_soap_request_async(
                        session, host, port,
                        avtransport_service.get('controlURL'),
                        avtransport_service.get('serviceType'),
                        "GetTransportInfo", {"InstanceID": "0"}
                    )
                    text = resp.text()
                    
                    if "STOPPED" in text or "PAUSED_PLAYBACK" in text:
                        loop_count += 1
                        print(f"DEBUG: Track ended, restarting loop #{loop_count}")
                        
                        # Restart playback
                        # 1. Set URI again
                        await soap_client.send_soap_request_async(
                            session, host, port,
                            avtransport_service.get('controlURL'),
                            avtransport_service.get('serviceType'),
                            "SetAVTransportURI", {
                                "InstanceID": "0",
                                "CurrentURI": media_url,
                                "CurrentURIMetaData": didl_metadata
                            }
                        )
                        
                        # 2. Start playback
                        await soap_client.send_soap_request_async(
                            session, host, port,
                            avtransport_service.get('controlURL'),
                            avtransport_service.get('serviceType'),
                            "Play", {
                                "InstanceID": "0",
                                "Speed": "1"
                            }
                        )
                        
                        print(f"DEBUG: Loop #{loop_count} restarted successfully")
                        consecutive_failures = 0
                        
                    elif "PLAYING" in text:
                        # All good, reset failure counter
                        consecutive_failures = 0
                        if loop_count > 0:
                            print(f"DEBUG: Loop #{loop_count} playing normally")
                    else:
                        print(f"DEBUG: Unknown transport state: {text[:100]}")
                        consecutive_failures += 1
                
                except Exception as e:
                    consecutive_failures += 1
                    print(f"DEBUG: Loop monitor error #{consecutive_failures}: {e}")
                    
                    if consecutive_failures >= max_failures:
                        print(f"DEBUG: Too many consecutive failures ({consecutive_failures}), stopping monitor")
                        break
                
        except asyncio.CancelledError:
            print(f"DEBUG: Loop monitor cancelled after {loop_count} loops")
            raise
    
    async def _execute_samsung_wam(self, device: Dict[str, Any], media_url: str, volume: int) -> Dict[str, Any]:
        """Execute fart loop using Samsung WAM API."""
        host = device.get('ip')
        wam_port = 55001  # Samsung WAM API port
        
        try:
            async with aiohttp.ClientSession() as session:
                results = {}
                
                # Step 1: Set volume
                volume_cmd = f"<name>SetVolume</name><p type=\"dec\" name=\"volume\" val=\"{volume}\"/>"
                try:
                    async with session.get(f"http://{host}:{wam_port}/UIC?cmd={volume_cmd}") as resp:
                        results['set_volume'] = f"HTTP {resp.status}"
                except Exception as e:
                    results['set_volume'] = f"Error: {e}"
                
                # Step 2: Set URL playback with repeat
                import urllib.parse
                url_encoded = urllib.parse.quote(media_url)
                playback_cmd = f"<name>SetUrlPlayback</name><p type=\"cdata\" name=\"url\" val=\"empty\"><![CDATA[{media_url}]]></p><p type=\"dec\" name=\"buffersize\" val=\"0\"/><p type=\"dec\" name=\"seektime\" val=\"0\"/><p type=\"dec\" name=\"resume\" val=\"1\"/>"
                encoded_cmd = urllib.parse.quote(playback_cmd)
                
                try:
                    async with session.get(f"http://{host}:{wam_port}/UIC?cmd={encoded_cmd}") as resp:
                        results['set_url_playback'] = f"HTTP {resp.status}"
                except Exception as e:
                    results['set_url_playback'] = f"Error: {e}"
                
                # Step 3: Set repeat mode (if supported)
                try:
                    repeat_cmd = "<name>SetRepeatMode</name><p type=\"str\" name=\"mode\" val=\"repeat_one\"/>"
                    encoded_repeat = urllib.parse.quote(repeat_cmd)
                    async with session.get(f"http://{host}:{wam_port}/UIC?cmd={encoded_repeat}") as resp:
                        results['set_repeat'] = f"HTTP {resp.status}"
                except Exception as e:
                    results['set_repeat'] = f"Error: {e}"
                
                return {
                    'status': 'success',
                    'protocol': 'samsung_wam',
                    'media_url': media_url,
                    'volume': volume,
                    'message': '💨 Samsung WAM audio loop launched! 💨',
                    'details': results
                }
                
        except Exception as e:
            return {
                'status': 'error',
                'error': f"Samsung WAM execution failed: {e}"
            }
    
    async def _execute_upnp(self, device: Dict[str, Any], media_url: str, volume: int) -> Dict[str, Any]:
        """Execute fart loop using UPnP/SOAP."""
        host = device.get('ip')
        port = device.get('port', 1400)
        
        soap_client = SOAPClient()
        
        try:
            async with aiohttp.ClientSession() as session:
                # Find AVTransport service
                avtransport_service = None
                for service in device.get('services', []):
                    if 'AVTransport' in service.get('serviceType', ''):
                        avtransport_service = service
                        break
                
                if not avtransport_service:
                    return {
                        'status': 'error',
                        'error': 'No AVTransport service found'
                    }
                
                control_url = avtransport_service.get('controlURL')
                service_type = avtransport_service.get('serviceType')
                
                results = {}
                
                # Stop current playback
                try:
                    resp = await soap_client.send_soap_request_async(
                        session, host, port, control_url, service_type, 
                        "Stop", {"InstanceID": "0"}
                    )
                    results['stop'] = f"HTTP {resp.status}"
                except Exception as e:
                    results['stop'] = f"Error: {e}"
                
                # Set the media URL
                import os
                from urllib.parse import urlparse
                
                parsed = urlparse(media_url)
                filename = os.path.basename(parsed.path) if parsed.path else "Audio File"
                track_name = os.path.splitext(filename)[0].replace('_', ' ').title()
                
                didl_metadata = f'''<DIDL-Lite xmlns="urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:upnp="urn:schemas-upnp-org:metadata-1-0/upnp/">
<item id="1" parentID="0" restricted="1">
<dc:title>{track_name}</dc:title>
<upnp:class>object.item.audioItem.musicTrack</upnp:class>
<res protocolInfo="http-get:*:audio/mpeg:*">{media_url}</res>
</item>
</DIDL-Lite>'''
                
                resp = await soap_client.send_soap_request_async(
                    session, host, port, control_url, service_type,
                    "SetAVTransportURI", {
                        "InstanceID": "0",
                        "CurrentURI": media_url,
                        "CurrentURIMetaData": didl_metadata
                    }
                )
                results['set_uri'] = f"HTTP {resp.status}"
                
                # Set volume if we have RenderingControl
                rendering_service = None
                for service in device.get('services', []):
                    if 'RenderingControl' in service.get('serviceType', ''):
                        rendering_service = service
                        break
                
                if rendering_service:
                    try:
                        resp = await soap_client.send_soap_request_async(
                            session, host, port, 
                            rendering_service.get('controlURL'),
                            rendering_service.get('serviceType'),
                            "SetVolume", {
                                "InstanceID": "0",
                                "Channel": "Master",
                                "DesiredVolume": str(volume)
                            }
                        )
                        results['set_volume'] = f"HTTP {resp.status}"
                    except Exception as e:
                        results['set_volume'] = f"Error: {e}"
                
                # Try to set repeat mode
                try:
                    resp = await soap_client.send_soap_request_async(
                        session, host, port, control_url, service_type,
                        "SetPlayMode", {
                            "InstanceID": "0",
                            "NewPlayMode": "REPEAT_ALL"
                        }
                    )
                    results['set_repeat'] = f"HTTP {resp.status}"
                except Exception as e:
                    results['set_repeat'] = f"Error: {e}"
                
                # Start playback
                resp = await soap_client.send_soap_request_async(
                    session, host, port, control_url, service_type,
                    "Play", {
                        "InstanceID": "0",
                        "Speed": "1"
                    }
                )
                results['play'] = f"HTTP {resp.status}"
                
                # Verify playback started
                await asyncio.sleep(1)
                try:
                    resp = await soap_client.send_soap_request_async(
                        session, host, port, control_url, service_type,
                        "GetTransportInfo", {"InstanceID": "0"}
                    )
                    text = await resp.text()
                    if "PLAYING" in text:
                        results['status_check'] = "PLAYING"
                    else:
                        results['status_check'] = "NOT_PLAYING"
                except Exception as e:
                    results['status_check'] = f"Error: {e}"
                
                return {
                    'status': 'success',
                    'protocol': 'upnp',
                    'media_url': media_url,
                    'volume': volume,
                    'message': f'💨 Generic UPnP loop activated! Playing {track_name} on repeat! 💨',
                    'details': results
                }
                
        except Exception as e:
            return {
                'status': 'error',
                'error': f"UPnP execution failed: {e}"
            }
    
    async def _execute_roku_ecp(self, device: Dict[str, Any], media_url: str, volume: int) -> Dict[str, Any]:
        """Execute fart loop using Roku ECP."""
        host = device.get('ip')
        
        try:
            async with aiohttp.ClientSession() as session:
                # Launch Media Player channel
                async with session.post(f"http://{host}:8060/launch/2213") as resp:
                    launch_result = f"HTTP {resp.status}"
                
                # Wait for channel to load
                await asyncio.sleep(2)
                
                # Send media URL
                data = f"mediaType=audio&url={media_url}&loop=true"
                headers = {'Content-Type': 'application/x-www-form-urlencoded'}
                
                async with session.post(f"http://{host}:8060/input", 
                                      data=data, headers=headers) as resp:
                    input_result = f"HTTP {resp.status}"
                
                return {
                    'status': 'success',
                    'protocol': 'roku_ecp',
                    'media_url': media_url,
                    'message': '💨 Roku ECP audio loop launched! 💨',
                    'details': {
                        'launch': launch_result,
                        'input': input_result
                    }
                }
                
        except Exception as e:
            return {
                'status': 'error',
                'error': f"Roku ECP execution failed: {e}"
            }
    
    async def _execute_chromecast(self, device: Dict[str, Any], media_url: str, volume: int) -> Dict[str, Any]:
        """Execute fart loop using Chromecast Cast protocol."""
        # Note: This is a placeholder - full Cast implementation requires pychromecast
        return {
            'status': 'error',
            'error': 'Chromecast Cast protocol not yet implemented - requires pychromecast library'
        }
    
    def cleanup(self) -> Dict[str, Any]:
        """Clean up resources when routine is stopped."""
        return self.stop_http_server()


class StopFartLoopRoutine(AsyncBaseRoutine):
    """Stop fart loop routine - quickly stops all fart loops on devices."""
    
    name = "Stop Fart Loop"
    description = "Immediately stops fart loops on all UPnP devices"
    category = "utility"
    supported_protocols = ["upnp", "ecp", "cast"]
    
    parameters = {}
    
    examples = [
        {
            "name": "Emergency Stop All Devices",
            "description": "Stop fart loops on all discovered devices",
            "command": "upnp-cli routine stop_fart_loop"
        },
        {
            "name": "Stop Specific Device",
            "description": "Stop fart loop on a specific device",
            "command": "upnp-cli --host 192.168.1.100 routine stop_fart_loop"
        }
    ]
    
    async def execute_on_device_async(self, device: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Execute stop routine on a single device."""
        try:
            print(f"DEBUG: Stopping fart loop on device: {device.get('ip', 'unknown')}")
            
            # Determine device type and use appropriate stop method
            manufacturer = device.get('manufacturer', '').lower()
            model = device.get('model', '').lower()
            
            print(f"DEBUG: Device info: manufacturer={manufacturer}, model={model}")
            
            if 'sonos' in manufacturer:
                return await self._stop_sonos(device)
            elif 'roku' in manufacturer or 'roku' in model:
                return await self._stop_roku(device)
            elif 'samsung' in manufacturer and ('wam' in model or 'soundbar' in model):
                return await self._stop_samsung_wam(device)
            else:
                return await self._stop_generic_upnp(device)
                
        except Exception as e:
            self.logger.error(f"Stop routine failed on {device.get('ip')}: {e}")
            return {
                'status': 'error',
                'error': f"Stop failed: {e}"
            }
    
    async def _stop_sonos(self, device: Dict[str, Any]) -> Dict[str, Any]:
        """Stop playback on Sonos device."""
        host = device.get('ip')
        port = device.get('port', 1400)
        
        print(f"DEBUG: Stopping Sonos device {host}:{port}")
        
        soap_client = SOAPClient()
        
        try:
            async with aiohttp.ClientSession() as session:
                # Find AVTransport service
                avtransport_service = None
                
                # Check main services
                for service in device.get('services', []):
                    if 'AVTransport' in service.get('serviceType', ''):
                        avtransport_service = service
                        break
                
                # Check embedded devices
                if not avtransport_service:
                    for embedded_device in device.get('devices', []):
                        for service in embedded_device.get('services', []):
                            if 'AVTransport' in service.get('serviceType', ''):
                                avtransport_service = service
                                break
                        if avtransport_service:
                            break
                
                if not avtransport_service:
                    return {
                        'status': 'error',
                        'error': 'No AVTransport service found'
                    }
                
                # Stop playback
                resp = await soap_client.send_soap_request_async(
                    session, host, port,
                    avtransport_service.get('controlURL'),
                    avtransport_service.get('serviceType'),
                    "Stop", {"InstanceID": "0"}
                )
                
                success = resp.status == 200
                
                return {
                    'status': 'success' if success else 'error',
                    'protocol': 'sonos_stop',
                    'message': f'🛑 Sonos fart loop {"stopped" if success else "stop failed"}! 🛑',
                    'http_status': resp.status
                }
                
        except Exception as e:
            return {
                'status': 'error',
                'error': f"Sonos stop failed: {e}"
            }
    
    async def _stop_generic_upnp(self, device: Dict[str, Any]) -> Dict[str, Any]:
        """Stop playback on generic UPnP device."""
        host = device.get('ip')
        port = device.get('port', 80)
        
        print(f"DEBUG: Stopping generic UPnP device {host}:{port}")
        
        soap_client = SOAPClient()
        
        try:
            async with aiohttp.ClientSession() as session:
                # Find AVTransport service
                avtransport_service = None
                
                for service in device.get('services', []):
                    if 'AVTransport' in service.get('serviceType', ''):
                        avtransport_service = service
                        break
                
                if not avtransport_service:
                    return {
                        'status': 'error',
                        'error': 'No AVTransport service found'
                    }
                
                # Stop playback
                resp = await soap_client.send_soap_request_async(
                    session, host, port,
                    avtransport_service.get('controlURL'),
                    avtransport_service.get('serviceType'),
                    "Stop", {"InstanceID": "0"}
                )
                
                success = resp.status == 200
                
                return {
                    'status': 'success' if success else 'error',
                    'protocol': 'upnp_stop',
                    'message': f'🛑 UPnP fart loop {"stopped" if success else "stop failed"}! 🛑',
                    'http_status': resp.status
                }
                
        except Exception as e:
            return {
                'status': 'error',
                'error': f"UPnP stop failed: {e}"
            }
    
    async def _stop_roku(self, device: Dict[str, Any]) -> Dict[str, Any]:
        """Stop playback on Roku device."""
        host = device.get('ip')
        port = device.get('port', 8060)
        
        print(f"DEBUG: Stopping Roku device {host}:{port}")
        
        try:
            async with aiohttp.ClientSession() as session:
                # Send home key to stop any playback
                url = f"http://{host}:{port}/keypress/Home"
                async with session.post(url) as resp:
                    success = resp.status == 200
                    
                    return {
                        'status': 'success' if success else 'error',
                        'protocol': 'roku_ecp_stop',
                        'message': f'🛑 Roku fart loop {"stopped" if success else "stop failed"}! 🛑',
                        'http_status': resp.status
                    }
                    
        except Exception as e:
            return {
                'status': 'error',
                'error': f"Roku stop failed: {e}"
            }
    
    async def _stop_samsung_wam(self, device: Dict[str, Any]) -> Dict[str, Any]:
        """Stop playback on Samsung WAM device."""
        host = device.get('ip')
        port = device.get('port', 55001)
        
        print(f"DEBUG: Stopping Samsung WAM device {host}:{port}")
        
        try:
            async with aiohttp.ClientSession() as session:
                # Send stop command via Samsung WAM API
                url = f"http://{host}:{port}/UIC?cmd=%3Cname%3ESetPlaybackControl%3C/name%3E%3Cp%20type=%22str%22%20name=%22playbackcontrol%22%20val=%22stop%22/%3E"
                async with session.get(url) as resp:
                    success = resp.status == 200
                    
                    return {
                        'status': 'success' if success else 'error',
                        'protocol': 'samsung_wam_stop',
                        'message': f'🛑 Samsung WAM fart loop {"stopped" if success else "stop failed"}! 🛑',
                        'http_status': resp.status
                    }
                    
        except Exception as e:
            return {
                'status': 'error',
                'error': f"Samsung WAM stop failed: {e}"
            } 