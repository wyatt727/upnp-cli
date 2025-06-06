#!/usr/bin/env python3
"""
Routine Commands Module

This module contains routine-related CLI commands including
routine execution and listing available routines.
"""

import json
import logging
from typing import Dict, Any

from upnp_cli.cli.output import ColoredOutput

logger = logging.getLogger(__name__)


async def cmd_routine(args) -> Dict[str, Any]:
    """Execute a user-defined routine."""
    try:
        # Import routines with fallback
        try:
            from routines import list_available_routines, get_routine_manager
        except ImportError:
            ColoredOutput.error("Routines module not available")
            return {"status": "error", "message": "Routines module not available"}
        
        # Load the routine
        routine_manager = get_routine_manager()
        routine_class = routine_manager.get_routine(args.routine_name)
        if not routine_class:
            available = [r['name'] for r in list_available_routines()]
            ColoredOutput.error(f"Routine '{args.routine_name}' not found")
            ColoredOutput.info(f"Available routines: {', '.join(available)}")
            return {"status": "error", "message": f"Routine '{args.routine_name}' not found"}
        
        # Auto-discover if no host specified
        if not args.host:
            # For routines like fart_loop, discover ALL devices for mass operation
            print("DEBUG: Using NEW mass device discovery logic")
            ColoredOutput.info("No host specified, discovering all devices for mass routine execution...")
            import upnp_cli.discovery as discovery
            import upnp_cli.utils as utils
            
            # Discover all devices on the network
            network = getattr(args, 'network', None) or utils.get_en0_network()[1]
            devices = await discovery.scan_network_async(network, use_cache=False)
            
            if not devices:
                return {"status": "error", "message": "No devices found"}
            
            ColoredOutput.info(f"Found {len(devices)} devices for routine execution")
            
            # Execute routine on ALL devices (this is what fart_loop is supposed to do)
            all_device_info = []
            import aiohttp
            async with aiohttp.ClientSession() as session:
                for device in devices:
                    host = device.get('ip')
                    port = device.get('port', 1400)
                    if host:
                        # Get full device description for each device
                        device_url = f"http://{host}:{port}/xml/device_description.xml"
                        device_info = await discovery.fetch_device_description(session, device_url)
                        
                        if device_info:
                            # Ensure we have the basic info
                            device_info['ip'] = host
                            device_info['port'] = port
                            device_info['use_ssl'] = args.use_ssl
                            all_device_info.append(device_info)
                        else:
                            # Fallback to minimal device info
                            fallback_info = {
                                'ip': host,
                                'port': port,
                                'use_ssl': args.use_ssl,
                                'services': [],
                                'friendlyName': device.get('friendlyName', f"{host}:{port}")
                            }
                            all_device_info.append(fallback_info)
            
            # Execute routine on all discovered devices
            ColoredOutput.header(f"🎵 Mass executing routine '{args.routine_name}' on {len(all_device_info)} devices")
            
            routine = routine_class()
            result = await routine.execute(all_device_info, **routine_args)
            
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                if result.get('status') == 'success':
                    successful = result.get('successful_devices', 0)
                    total = result.get('total_devices', len(all_device_info))
                    ColoredOutput.success(f"🎉 Mass routine '{args.routine_name}' completed: {successful}/{total} devices successful")
                    if 'message' in result:
                        ColoredOutput.info(result['message'])
                else:
                    ColoredOutput.error(f"Mass routine '{args.routine_name}' failed: {result.get('message', 'Unknown error')}")
            
            return result
        
        # Single device execution (when host is specified)
        ColoredOutput.header(f"Executing routine '{args.routine_name}' on {args.host}:{args.port}")
        
        # Dry run mode
        if args.dry_run:
            ColoredOutput.info(f"DRY RUN: Would execute routine '{args.routine_name}' on {args.host}:{args.port}")
            return {"status": "dry_run", "routine": args.routine_name, "target": f"{args.host}:{args.port}"}
        
        # Execute routine
        routine_args = {
            'media_file': getattr(args, 'media_file', 'fart.mp3'),
            'server_port': getattr(args, 'server_port', 8080),
            'volume': getattr(args, 'volume', 50),
        }
        
        # Get full device info including services for the routine
        import upnp_cli.discovery as discovery
        import aiohttp
        
        device_url = f"http://{args.host}:{args.port}/xml/device_description.xml"
        async with aiohttp.ClientSession() as session:
            device_info = await discovery.fetch_device_description(session, device_url)
        
        if not device_info:
            # Fallback to minimal device info
            device_info = {
                'ip': args.host,
                'port': args.port,
                'use_ssl': args.use_ssl,
                'services': [],
                'friendlyName': f"{args.host}:{args.port}"
            }
        else:
            # Ensure we have the basic info
            device_info['ip'] = args.host
            device_info['port'] = args.port
            device_info['use_ssl'] = args.use_ssl
        
        routine = routine_class()
        result = await routine.execute([device_info], **routine_args)
        
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            if result.get('status') == 'success':
                ColoredOutput.success(f"Routine '{args.routine_name}' executed successfully")
                if 'message' in result:
                    ColoredOutput.info(result['message'])
            else:
                ColoredOutput.error(f"Routine '{args.routine_name}' failed: {result.get('message', 'Unknown error')}")
        
        return result
        
    except Exception as e:
        ColoredOutput.error(f"Routine execution failed: {e}")
        if args.verbose:
            logger.exception("Routine execution error details")
        return {"status": "error", "message": str(e)}


async def cmd_list_routines(args) -> Dict[str, Any]:
    """List available routines."""
    try:
        # Import routines with fallback
        try:
            from routines import list_available_routines
        except ImportError:
            ColoredOutput.warning("Routines module not available")
            return {"status": "warning", "message": "Routines module not available", "routines": []}
        
        available_routines = list_available_routines()
        
        if args.json:
            print(json.dumps({"routines": available_routines}, indent=2))
        else:
            ColoredOutput.header("Available Routines")
            if available_routines:
                for routine_info in available_routines:
                    name = routine_info['name']
                    description = routine_info.get('description', 'No description')
                    ColoredOutput.print(f"  • {name}: {description}", 'cyan')
            else:
                ColoredOutput.warning("No routines found in routines directory")
        
        return {"status": "success", "routines": available_routines}
        
    except Exception as e:
        ColoredOutput.error(f"Failed to list routines: {e}")
        return {"status": "error", "message": str(e)} 