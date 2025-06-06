"""
Base class for all UPnP routines.

All user-created routines must inherit from BaseRoutine and implement
the required methods and attributes.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import asyncio
from datetime import datetime

from upnp_cli.logging_utils import get_logger
from upnp_cli.http_server import MediaHTTPServer


class BaseRoutine(ABC):
    """
    Base class for all UPnP routines.
    
    Subclasses must define:
    - name: Human-readable name of the routine
    - description: What the routine does
    - execute: Main routine logic
    
    Optional attributes:
    - category: Category (e.g., 'prank', 'music', 'test')
    - media_files: List of required media files
    - supported_protocols: List of supported protocols
    - parameters: Dict of configurable parameters
    """
    
    # Required class attributes (must be set by subclasses)
    name: str = ""
    description: str = ""
    
    # Optional class attributes
    category: str = "misc"
    media_files: List[str] = []
    supported_protocols: List[str] = ["upnp"]
    parameters: Dict[str, Any] = {}
    examples: List[str] = []
    
    def __init__(self):
        """Initialize the routine."""
        self.logger = get_logger(f"routine.{self.__class__.__name__}")
        self.http_server: Optional[MediaHTTPServer] = None
        self.start_time: Optional[datetime] = None
        self.results: Dict[str, Any] = {}
    
    @abstractmethod
    def execute(self, devices: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        """
        Execute the routine on the specified devices.
        
        Args:
            devices: List of device dictionaries with 'ip', 'port', 'services', etc.
            **kwargs: Additional parameters specific to the routine
        
        Returns:
            Dict with execution results, including 'status', 'message', 'results', etc.
        """
        pass
    
    def start_http_server(self, port: int = 8080, directory: str = None) -> Dict[str, Any]:
        """Start HTTP server to serve media files."""
        if self.http_server and self.http_server.get_status().get('status') == 'running':
            return self.http_server.get_status()
        
        try:
            self.http_server = MediaHTTPServer(port=port, directory=directory)
            result = self.http_server.start()
            self.logger.info(f"Started HTTP server: {result}")
            return result
        except Exception as e:
            self.logger.error(f"Failed to start HTTP server: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def stop_http_server(self) -> Dict[str, Any]:
        """Stop the HTTP server."""
        if not self.http_server:
            return {'status': 'not_running'}
        
        try:
            result = self.http_server.stop()
            self.logger.info("Stopped HTTP server")
            return result
        except Exception as e:
            self.logger.error(f"Failed to stop HTTP server: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def get_media_url(self, filename: str) -> Optional[str]:
        """Get the HTTP URL for a media file."""
        if not self.http_server:
            return None
        
        status = self.http_server.get_status()
        if status.get('status') == 'running':
            local_ip = status.get('local_ip')
            port = status.get('port')
            return f"http://{local_ip}:{port}/{filename}"
        
        return None
    
    def validate_devices(self, devices: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate and filter devices that support this routine's protocols."""
        valid_devices = []
        
        for device in devices:
            if self._device_supports_routine(device):
                valid_devices.append(device)
            else:
                self.logger.warning(f"Device {device.get('ip')} doesn't support required protocols")
        
        return valid_devices
    
    def _device_supports_routine(self, device: Dict[str, Any]) -> bool:
        """Check if a device supports this routine's required protocols."""
        if 'upnp' in self.supported_protocols:
            # Check for basic UPnP MediaRenderer services
            services = device.get('services', [])
            has_avtransport = any('AVTransport' in s.get('serviceType', '') for s in services)
            if has_avtransport:
                return True
        
        if 'ecp' in self.supported_protocols:
            # Check for Roku ECP support
            if device.get('manufacturer', '').lower() == 'roku':
                return True
        
        if 'cast' in self.supported_protocols:
            # Check for Chromecast support  
            if 'chromecast' in device.get('modelName', '').lower():
                return True
        
        return len(self.supported_protocols) == 0  # Accept all if no protocols specified
    
    def log_execution_start(self, devices: List[Dict[str, Any]], **kwargs) -> None:
        """Log the start of routine execution."""
        self.start_time = datetime.now()
        device_names = [d.get('friendlyName', d.get('ip', 'unknown')) for d in devices]
        self.logger.info(f"Starting {self.name} on {len(devices)} devices: {', '.join(device_names)}")
        if kwargs:
            self.logger.debug(f"Parameters: {kwargs}")
    
    def log_execution_end(self, success_count: int, total_count: int) -> None:
        """Log the end of routine execution."""
        if self.start_time:
            duration = datetime.now() - self.start_time
            self.logger.info(f"Completed {self.name}: {success_count}/{total_count} devices successful "
                           f"(duration: {duration.total_seconds():.1f}s)")
    
    def create_result_summary(self, device_results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Create a standardized result summary."""
        total_devices = len(device_results)
        successful_devices = sum(1 for r in device_results.values() if r.get('status') == 'success')
        
        return {
            'routine': self.name,
            'status': 'success' if successful_devices > 0 else 'failed',
            'total_devices': total_devices,
            'successful_devices': successful_devices,
            'failed_devices': total_devices - successful_devices,
            'success_rate': f"{(successful_devices/total_devices*100):.1f}%" if total_devices > 0 else "0%",
            'device_results': device_results,
            'execution_time': datetime.now().isoformat(),
            'message': f"{self.name} executed on {successful_devices}/{total_devices} devices"
        }


class AsyncBaseRoutine(BaseRoutine):
    """Base class for asynchronous routines that can execute in parallel."""
    
    async def execute_async(self, devices: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        """
        Async version of execute for parallel device operations.
        
        Default implementation runs device operations in parallel.
        Override this method for custom async behavior.
        """
        self.log_execution_start(devices, **kwargs)
        
        # Run device operations in parallel
        tasks = []
        for device in devices:
            task = self.execute_on_device_async(device, **kwargs)
            tasks.append(task)
        
        device_results = {}
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for device, result in zip(devices, results):
            device_id = f"{device.get('ip')}:{device.get('port')}"
            if isinstance(result, Exception):
                device_results[device_id] = {
                    'status': 'error',
                    'error': str(result)
                }
            else:
                device_results[device_id] = result
        
        success_count = sum(1 for r in device_results.values() if r.get('status') == 'success')
        self.log_execution_end(success_count, len(devices))
        
        return self.create_result_summary(device_results)
    
    async def execute(self, devices: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        """Execute the routine asynchronously."""
        return await self.execute_async(devices, **kwargs)
    
    @abstractmethod
    async def execute_on_device_async(self, device: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        Execute the routine on a single device asynchronously.
        
        Args:
            device: Device dictionary with 'ip', 'port', 'services', etc.
            **kwargs: Additional parameters
        
        Returns:
            Dict with device-specific results
        """
        pass 