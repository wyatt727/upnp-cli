#!/usr/bin/env python3
"""
Discovery Commands

Command implementations for UPnP device discovery and information gathering.
"""

import json
import logging
from typing import List, Dict, Any
from pathlib import Path

# Import core modules - fix import mess
import sys
from pathlib import Path

# Ensure we can import from the upnp_cli package
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import upnp_cli.discovery as discovery
import upnp_cli.cache as cache
import upnp_cli.utils as utils
from upnp_cli.cli.output import ColoredOutput

logger = logging.getLogger(__name__)


async def get_device_description(url: str, timeout: int = 10) -> Dict[str, Any]:
    """
    Fetch and parse device description from URL.
    
    Args:
        url: Device description URL
        timeout: Request timeout
        
    Returns:
        Parsed device information
    """
    import aiohttp
    try:
        async with aiohttp.ClientSession() as session:
            result = await discovery.fetch_device_description(session, url, timeout)
            return result or {}
    except Exception as e:
        logger.error(f"Failed to fetch device description from {url}: {e}")
        return {}


async def cmd_discover(args) -> Dict[str, Any]:
    """Discover UPnP devices on the network."""
    # Suppress console logging in JSON mode
    if args.json:
        import upnp_cli.logging_utils as logging_utils
        logging_utils.suppress_console_logging()
    
    # Only show colored output if not in JSON mode
    if not args.json:
        ColoredOutput.header("Discovering UPnP devices...")
    
    cache_manager = cache.DeviceCache(Path(args.cache)) if args.cache else None
    
    try:
        # Check cache first if enabled
        if cache_manager and not args.force_scan:
            cached_devices = cache_manager.list()
            if cached_devices:
                # Convert cache format to device format
                devices = [entry['info'] for entry in cached_devices]
                if not args.json:
                    ColoredOutput.info(f"Using cached results ({len(devices)} devices)")
                if args.json:
                    print(json.dumps(devices, indent=2))
                else:
                    _print_device_table(devices)
                return {"status": "success", "devices": devices, "source": "cache"}
        
        # Perform discovery
        if hasattr(args, 'ssdp_only') and args.ssdp_only:
            devices = await discovery.discover_ssdp_devices(timeout=args.timeout)
        else:
            network = args.network or utils.get_en0_network()[1]
            devices = await discovery.scan_network_async(
                network, 
                use_cache=bool(args.cache)
            )
        
        # Save to cache if enabled
        if cache_manager:
            for device in devices:
                ip = device.get('ip')
                port = device.get('port')
                if ip and port:
                    cache_manager.upsert(ip, port, device)
        
        # Output results
        if args.json:
            print(json.dumps(devices, indent=2))
        else:
            _print_device_table(devices)
            ColoredOutput.success(f"Discovered {len(devices)} UPnP devices")
        
        return {"status": "success", "devices": devices, "source": "scan"}
        
    except Exception as e:
        if not args.json:
            ColoredOutput.error(f"Discovery failed: {e}")
        if args.verbose:
            logger.exception("Discovery error details")
        return {"status": "error", "message": str(e)}
    finally:
        # Restore console logging if it was suppressed
        if args.json:
            import upnp_cli.logging_utils as logging_utils
            logging_utils.restore_console_logging()


def _print_device_table(devices: List[Dict[str, Any]]):
    """Print devices in a formatted table."""
    if not devices:
        ColoredOutput.warning("No devices found")
        return
    
    # Print header
    ColoredOutput.print(f"{'IP Address':<15} {'Port':<6} {'Device Name':<25} {'Manufacturer':<15} {'Model':<15}", 'bold')
    ColoredOutput.print("-" * 90, 'cyan')
    
    # Print devices
    for device in devices:
        ip = device.get('ip', 'Unknown')
        port = str(device.get('port', '?'))
        name = device.get('friendlyName', 'Unknown Device')[:24]
        manufacturer = device.get('manufacturer', 'Unknown')[:14]
        model = device.get('modelName', 'Unknown')[:14]
        
        print(f"{ip:<15} {port:<6} {name:<25} {manufacturer:<15} {model:<15}")


async def cmd_info(args) -> Dict[str, Any]:
    """Get detailed information about a specific device."""
    try:
        # Auto-discover if no host specified
        if not args.host:
            from upnp_cli.cli.utils import auto_discover_target
            devices = await auto_discover_target(args)
            if not devices:
                return {"status": "error", "message": "No devices found for auto-discovery"}
            device = devices[0]
            args.host = device['ip']
            args.port = device.get('port', args.port)
        
        # Get device description
        url = f"http://{args.host}:{args.port}/xml/device_description.xml"
        device_info = await get_device_description(url)
        
        if args.json:
            print(json.dumps(device_info, indent=2))
        else:
            _print_device_info(device_info)
        
        return {"status": "success", "device": device_info}
        
    except Exception as e:
        ColoredOutput.error(f"Failed to get device info: {e}")
        return {"status": "error", "message": str(e)}


def _print_device_info(device: Dict[str, Any]):
    """Print device information in a formatted way."""
    ColoredOutput.header(f"Device Information: {device.get('friendlyName', 'Unknown')}")
    
    basic_info = [
        ("IP Address", device.get('ip', 'Unknown')),
        ("Port", device.get('port', 'Unknown')),
        ("Manufacturer", device.get('manufacturer', 'Unknown')),
        ("Model", device.get('modelName', 'Unknown')),
        ("Model Number", device.get('modelNumber', 'Unknown')),
        ("Serial Number", device.get('serialNum', 'Unknown')),
        ("UDN", device.get('UDN', 'Unknown')),
        ("Software Version", device.get('softwareVersion', 'Unknown')),
    ]
    
    for label, value in basic_info:
        ColoredOutput.print(f"{label:<20}: {value}", 'white')
    
    # Print services
    services = device.get('services', [])
    if services:
        ColoredOutput.print(f"\nServices ({len(services)}):", 'cyan', bold=True)
        for service in services:
            service_type = service.get('serviceType', 'Unknown')
            control_url = service.get('controlURL', 'Unknown')
            ColoredOutput.print(f"  • {service_type}", 'yellow')
            ColoredOutput.print(f"    Control: {control_url}", 'white')


async def cmd_services(args) -> Dict[str, Any]:
    """List available services for a device."""
    try:
        # Auto-discover if no host specified
        if not args.host:
            from upnp_cli.cli.utils import auto_discover_target
            devices = await auto_discover_target(args)
            if not devices:
                return {"status": "error", "message": "No devices found"}
            device = devices[0]
            args.host = device['ip']
            args.port = device.get('port', args.port)
        
        # Get services
        url = f"http://{args.host}:{args.port}/xml/device_description.xml"
        device_info = await get_device_description(url)
        services = device_info.get('services', [])
        
        if args.json:
            print(json.dumps(services, indent=2))
        else:
            _print_services(services)
        
        return {"status": "success", "services": services}
        
    except Exception as e:
        ColoredOutput.error(f"Failed to get services: {e}")
        return {"status": "error", "message": str(e)}


def _print_services(services: List[Dict[str, Any]]):
    """Print services in a formatted way."""
    if not services:
        ColoredOutput.warning("No services found")
        return
    
    ColoredOutput.header(f"Available Services ({len(services)})")
    
    for i, service in enumerate(services, 1):
        service_type = service.get('serviceType', 'Unknown')
        service_id = service.get('serviceId', 'Unknown')
        control_url = service.get('controlURL', 'Unknown')
        event_url = service.get('eventSubURL', 'None')
        scpd_url = service.get('SCPDURL', 'None')
        
        ColoredOutput.print(f"\n{i}. {service_type}", 'yellow', bold=True)
        ColoredOutput.print(f"   Service ID: {service_id}", 'white')
        ColoredOutput.print(f"   Control URL: {control_url}", 'cyan')
        ColoredOutput.print(f"   Event URL: {event_url}", 'white')
        ColoredOutput.print(f"   SCPD URL: {scpd_url}", 'white')


# auto_discover_target moved to upnp_cli.cli.utils 