"""
Template for creating custom UPnP routines.

Copy this file and modify it to create your own custom routine.
Replace all the placeholders marked with TODO and implement your logic.
"""

from typing import List, Dict, Any
import aiohttp
import asyncio

from routines.base_routine import AsyncBaseRoutine
from upnp_cli.soap_client import SOAPClient


class MyCustomRoutine(AsyncBaseRoutine):
    """TODO: Replace with your routine description."""
    
    # TODO: Required - Set your routine name and description
    name = "My Custom Routine"
    description = "TODO: Describe what your routine does"
    
    # TODO: Optional - Set category and supported protocols
    category = "misc"  # Options: "prank", "music", "test", "misc"
    media_files = []   # List any required media files, e.g., ["myfile.mp3"]
    supported_protocols = ["upnp"]  # Options: "upnp", "ecp", "cast"
    
    # TODO: Optional - Define configurable parameters
    parameters = {
        "volume": {
            "type": "int",
            "default": 50,
            "min": 0,
            "max": 100,
            "description": "Volume level (0-100)"
        },
        "my_parameter": {
            "type": "str",
            "default": "default_value",
            "description": "TODO: Describe this parameter"
        }
    }
    
    # TODO: Optional - Add usage examples
    examples = [
        "upnp-cli routine my_custom_routine",
        "upnp-cli routine my_custom_routine --volume 75 --my-parameter custom_value"
    ]
    
    async def execute_on_device_async(self, device: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        TODO: Implement your routine logic here.
        
        This method is called once for each device that your routine will target.
        It runs asynchronously, so multiple devices can be processed in parallel.
        
        Args:
            device: Device dictionary containing 'ip', 'port', 'services', etc.
            **kwargs: Parameters passed from CLI or execute() call
        
        Returns:
            Dict with execution results - should contain 'status' and other details
        """
        try:
            # TODO: Extract parameters
            volume = kwargs.get('volume', 50)
            my_param = kwargs.get('my_parameter', 'default_value')
            
            # TODO: Start HTTP server if you need to serve media files
            # server_result = self.start_http_server(port=8080)
            # if server_result.get('status') == 'error':
            #     return {'status': 'error', 'error': 'Failed to start HTTP server'}
            
            # TODO: Get media URL if needed
            # media_url = self.get_media_url("myfile.mp3")
            # if not media_url:
            #     return {'status': 'error', 'error': 'Could not get media URL'}
            
            # TODO: Choose protocol based on device
            manufacturer = device.get('manufacturer', '').lower()
            
            if 'roku' in manufacturer:
                return await self._execute_roku(device, **kwargs)
            elif 'chromecast' in device.get('modelName', '').lower():
                return await self._execute_chromecast(device, **kwargs)
            else:
                return await self._execute_upnp(device, **kwargs)
                
        except Exception as e:
            self.logger.error(f"Failed to execute routine on {device.get('ip')}: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    async def _execute_upnp(self, device: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """TODO: Implement UPnP/SOAP execution logic."""
        host = device.get('ip')
        port = device.get('port', 1400)
        
        soap_client = SOAPClient()
        
        try:
            async with aiohttp.ClientSession() as session:
                # TODO: Find required services
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
                
                # TODO: Implement your SOAP calls here
                # Example: Get current transport info
                resp = await soap_client.send_soap_request_async(
                    session, host, port, control_url, service_type,
                    "GetTransportInfo", {"InstanceID": "0"}
                )
                
                # TODO: Process response and return results
                return {
                    'status': 'success',
                    'protocol': 'upnp',
                    'details': {
                        'transport_info': f"HTTP {resp.status}"
                    }
                }
                
        except Exception as e:
            return {
                'status': 'error',
                'error': f"UPnP execution failed: {e}"
            }
    
    async def _execute_roku(self, device: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """TODO: Implement Roku ECP execution logic."""
        host = device.get('ip')
        
        try:
            async with aiohttp.ClientSession() as session:
                # TODO: Implement Roku ECP calls
                # Example: Get device info
                async with session.get(f"http://{host}:8060/query/device-info") as resp:
                    device_info = f"HTTP {resp.status}"
                
                return {
                    'status': 'success',
                    'protocol': 'roku_ecp',
                    'details': {
                        'device_info': device_info
                    }
                }
                
        except Exception as e:
            return {
                'status': 'error',
                'error': f"Roku ECP execution failed: {e}"
            }
    
    async def _execute_chromecast(self, device: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """TODO: Implement Chromecast Cast protocol execution logic."""
        # Note: Cast protocol requires pychromecast library or WebSocket implementation
        return {
            'status': 'error',
            'error': 'Chromecast Cast protocol not implemented - requires pychromecast library'
        }
    
    def cleanup(self) -> Dict[str, Any]:
        """TODO: Optional - Clean up resources when routine is stopped."""
        # Example: Stop HTTP server
        # return self.stop_http_server()
        return {'status': 'no_cleanup_needed'}


# TODO: Instructions for testing your routine:
#
# 1. Save this file as routines/my_custom_routine.py
# 2. Update the class name and all TODO items
# 3. Test it: upnp-cli routine my_custom_routine --help
# 4. Run it: upnp-cli routine my_custom_routine
#
# Tips:
# - Use self.logger.info(), .debug(), .error() for logging
# - Return {'status': 'success'} for successful execution
# - Return {'status': 'error', 'error': 'message'} for failures
# - Use self.start_http_server() if you need to serve media files
# - Check device.get('manufacturer') to customize behavior per device type 