#!/usr/bin/env python3
"""
Ultimate UPnP Pentest & Control CLI - Main Entry Point

This module provides the main command-line interface for the UPnP CLI toolkit.
It integrates all functionality including discovery, media control, security scanning,
and prank routines into a single, comprehensive CLI.
"""

import sys
import argparse
import asyncio
import json
import time
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

# Import core modules - fix the import mess
import sys
from pathlib import Path

# Ensure we can import from the upnp_cli package
current_dir = Path(__file__).parent
project_root = current_dir.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Now import everything using absolute imports
import upnp_cli.config as config
import upnp_cli.logging_utils as logging_utils
import upnp_cli.discovery as discovery
import upnp_cli.cache as cache
import upnp_cli.soap_client as soap_client
import upnp_cli.media_control as media_control
import upnp_cli.ssl_rtsp_scan as ssl_rtsp_scan
import upnp_cli.http_server as http_server
import upnp_cli.profiles as profiles
import upnp_cli.utils as utils

# Import new modular CLI components
from upnp_cli.cli.output import ColoredOutput, ProgressReporter
from upnp_cli.cli.commands.discovery import cmd_discover, cmd_info, cmd_services
from upnp_cli.cli.commands.scpd_analysis import cmd_scpd_analyze, cmd_mass_scpd_analyze
from upnp_cli.cli.commands.interactive_control import cmd_interactive_control
from upnp_cli.cli.commands.media_control import (
    cmd_play, cmd_pause, cmd_stop, cmd_next, cmd_previous,
    cmd_get_volume, cmd_set_volume, cmd_get_mute, cmd_set_mute
)
from upnp_cli.cli.commands.security_scanning import cmd_ssl_scan, cmd_rtsp_scan
from upnp_cli.cli.commands.routine_commands import cmd_routine, cmd_list_routines
from upnp_cli.cli.commands.mass_operations import cmd_mass_discover, cmd_mass_scan_services
from upnp_cli.cli.commands.cache_server import cmd_clear_cache, cmd_start_server, cmd_stop_server
from upnp_cli.cli.commands.auto_profile import cmd_auto_profile
from upnp_cli.cli.utils import auto_discover_target, parse_soap_response

# Import enhanced profile and API generation commands
from upnp_cli.cli.commands.enhanced_profiles import cmd_enhanced_profile_single, cmd_enhanced_profile_mass
from upnp_cli.cli.commands.profile_based_interactive import cmd_profile_interactive
from upnp_cli.routines.profile_aware_routines import cmd_profile_routine
# Temporarily disable API generator due to f-string syntax issues
# from upnp_cli.api_generator.profile_to_api import cmd_generate_api

# Import routines - fix the import mess
try:
    from routines import list_available_routines, get_routine_manager
except ImportError:
    # Provide fallback functionality if routines not available
    def list_available_routines():
        return []
    
    def get_routine_manager():
        class MockManager:
            def get_routine(self, name):
                return None
        return MockManager()

logger = logging.getLogger(__name__)


# === HELPER FUNCTIONS ===

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


# parse_soap_response moved to upnp_cli.cli.utils


class CLIError(Exception):
    """Custom exception for CLI-specific errors."""
    pass


# ColoredOutput and ProgressReporter classes moved to cli.output module


# Discovery commands moved to cli.commands.discovery module


# Media Control Commands moved to upnp_cli.cli.commands.media_control


# Security Scanning Commands moved to upnp_cli.cli.commands.security_scanning


# Routine Commands
async def cmd_routine(args) -> Dict[str, Any]:
    """Execute a user-defined routine."""
    try:
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
            # For fart_loop and other mass routines, discover ALL devices
            ColoredOutput.info("No host specified, discovering all devices for mass routine execution...")
            
            network = getattr(args, 'network', None) or utils.get_en0_network()[1]
            devices = await discovery.scan_network_async(network, use_cache=False)
            
            if not devices:
                return {"status": "error", "message": "No devices found"}
            
            ColoredOutput.info(f"Found {len(devices)} devices for routine execution")
            
            # Get full device info for all devices
            all_device_info = []
            import aiohttp
            async with aiohttp.ClientSession() as session:
                for device in devices:
                    host = device.get('ip')
                    port = device.get('port', 1400)
                    if host:
                        # Get full device description for each device
                        device_url = f"http://{host}:{port}/xml/device_description.xml"
                        device_info = await get_device_description(device_url)
                        
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
            
            # Execute routine
            routine_args = {
                'media_file': getattr(args, 'media_file', 'fart.mp3'),
                'server_port': getattr(args, 'server_port', 8080),
                'volume': getattr(args, 'volume', 50),
            }
            
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
        
        # Create device info for the routine
        device_info = {
            'ip': args.host,
            'port': args.port,
            'use_ssl': args.use_ssl
        }
        
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
        available_routines = list_available_routines()
        
        if args.json:
            print(json.dumps({"routines": available_routines}, indent=2))
        else:
            ColoredOutput.header("Available Routines")
            for routine_info in available_routines:
                name = routine_info['name']
                description = routine_info.get('description', 'No description')
                ColoredOutput.print(f"  • {name}: {description}", 'cyan')
        
        return {"status": "success", "routines": available_routines}
        
    except Exception as e:
        ColoredOutput.error(f"Failed to list routines: {e}")
        return {"status": "error", "message": str(e)}


# Mass Operation Commands
async def cmd_mass_discover(args) -> Dict[str, Any]:
    """Perform mass discovery and optional mass routine execution."""
    try:
        ColoredOutput.header("Mass UPnP Discovery & Operation")
        
        # Discover all devices
        network = args.network or utils.get_en0_network()[1]
        devices = await discovery.scan_network_async(
            network,
            use_cache=bool(args.cache)
        )
        
        if not devices:
            ColoredOutput.warning("No devices found for mass operation")
            return {"status": "warning", "message": "No devices found"}
        
        ColoredOutput.success(f"Discovered {len(devices)} devices for mass operation")
        
        # If no routine specified, just return discovery results
        if not args.routine:
            if args.json:
                print(json.dumps(devices, indent=2))
            else:
                _print_device_table(devices)
            return {"status": "success", "devices": devices}
        
        # Execute routine on all devices
        return await _execute_mass_routine(devices, args)
        
    except Exception as e:
        ColoredOutput.error(f"Mass operation failed: {e}")
        return {"status": "error", "message": str(e)}


async def _execute_mass_routine(devices: List[Dict[str, Any]], args) -> Dict[str, Any]:
    """Execute a routine on multiple devices in parallel."""
    routine_manager = get_routine_manager()
    routine_class = routine_manager.get_routine(args.routine)
    if not routine_class:
        available = [r['name'] for r in list_available_routines()]
        ColoredOutput.error(f"Routine '{args.routine}' not found")
        ColoredOutput.info(f"Available routines: {', '.join(available)}")
        return {"status": "error", "message": f"Routine '{args.routine}' not found"}
    
    ColoredOutput.header(f"Executing '{args.routine}' on {len(devices)} devices")
    
    if args.dry_run:
        ColoredOutput.info(f"DRY RUN: Would execute '{args.routine}' on {len(devices)} devices")
        return {"status": "dry_run", "routine": args.routine, "target_count": len(devices)}
    
    # Progress tracking
    progress = ProgressReporter(len(devices), f"Mass {args.routine}")
    results = {}
    
    # Execute routine on each device
    for device in devices:
        try:
            host = device['ip']
            port = device.get('port', 1400)
            device_name = device.get('friendlyName', f"{host}:{port}")
            
            progress.update(message=f"Attacking {device_name}")
            
            routine_args = {
                'media_file': getattr(args, 'media_file', 'fart.mp3'),
                'server_port': getattr(args, 'server_port', 8080),
                'volume': getattr(args, 'volume', 50),
            }
            
            # Create device info for the routine
            device_info = {
                'ip': host,
                'port': port,
                'use_ssl': args.use_ssl
            }
            
            routine = routine_class()
            result = await routine.execute([device_info], **routine_args)
            results[device_name] = result
            
            if result.get('status') == 'success':
                ColoredOutput.success(f"✅ {device_name}: SUCCESS")
            else:
                ColoredOutput.error(f"❌ {device_name}: FAILED - {result.get('message', 'Unknown error')}")
            
        except Exception as e:
            results[device_name] = {"status": "error", "message": str(e)}
            ColoredOutput.error(f"❌ {device_name}: ERROR - {e}")
    
    # Calculate summary
    successful = sum(1 for r in results.values() if r.get('status') == 'success')
    failed = len(devices) - successful
    
    progress.finish(f"{successful} successful, {failed} failed")
    
    summary = {
        "status": "complete",
        "routine": args.routine,
        "total_targets": len(devices),
        "successful_attacks": successful,
        "failed_attacks": failed,
        "attack_results": results
    }
    
    if args.json:
        print(json.dumps(summary, indent=2))
    
    return summary


async def cmd_mass_scan_services(args) -> Dict[str, Any]:
    """Perform comprehensive mass service scanning with prioritization."""
    try:
        ColoredOutput.header("Mass UPnP Service Analysis & Prioritization")
        
        # Discover all devices
        network = args.network or utils.get_en0_network()[1]
        ColoredOutput.info(f"Scanning network: {network}")
        
        devices = await discovery.scan_network_async(
            network,
            use_cache=bool(args.cache)
        )
        
        if not devices:
            ColoredOutput.warning("No devices found for service analysis")
            return {"status": "warning", "message": "No devices found"}
        
        ColoredOutput.success(f"Discovered {len(devices)} devices for service analysis")
        
        # Analyze services and prioritize
        service_analysis = await _analyze_device_services(devices, args)
        
        if args.json:
            print(json.dumps(service_analysis, indent=2))
        else:
            _print_service_analysis(service_analysis, args)
        
        # Save detailed report if requested
        if args.save_report:
            try:
                import datetime
                report_path = Path(args.save_report)
                
                # Add timestamp if filename doesn't include extension
                if not report_path.suffix:
                    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    report_path = report_path.with_name(f"{report_path.name}_{timestamp}.json")
                
                with open(report_path, 'w') as f:
                    json.dump(service_analysis, f, indent=2)
                
                ColoredOutput.success(f"Detailed report saved to: {report_path}")
                
            except Exception as e:
                ColoredOutput.error(f"Failed to save report: {e}")
        
        return {"status": "success", "analysis": service_analysis}
        
    except Exception as e:
        ColoredOutput.error(f"Mass service scan failed: {e}")
        return {"status": "error", "message": str(e)}


async def _analyze_device_services(devices: List[Dict[str, Any]], args) -> Dict[str, Any]:
    """
    Analyze services across all devices and prioritize them.
    
    Args:
        devices: List of discovered devices
        args: CLI arguments
        
    Returns:
        Comprehensive service analysis with prioritization
    """
    analysis = {
        "total_devices": len(devices),
        "scan_timestamp": time.time(),
        "high_priority_devices": [],
        "medium_priority_devices": [],
        "low_priority_devices": [],
        "unknown_devices": [],
        "service_summary": {},
        "security_findings": [],
        "protocol_distribution": {},
        "recommendations": []
    }
    
    profile_manager = profiles.get_profile_manager()
    
    # Service priority definitions
    high_priority_services = {
        'urn:schemas-upnp-org:service:AVTransport:1': 'Media Control (Audio/Video)',
        'urn:schemas-upnp-org:service:RenderingControl:1': 'Volume/Audio Control',
        'urn:schemas-sonos-com:service:Queue:1': 'Sonos Queue Management',
        'urn:dial-multiscreen-org:service:dial:1': 'Cast/DIAL Protocol',
        'urn:schemas-upnp-org:service:ConnectionManager:1': 'Media Connection Management'
    }
    
    medium_priority_services = {
        'urn:schemas-upnp-org:service:ContentDirectory:1': 'Media Library Access',
        'urn:schemas-upnp-org:service:MediaReceiverRegistrar:1': 'Device Registration',
        'urn:schemas-upnp-org:service:DeviceProtection:1': 'Security Services',
        'urn:microsoft-com:service:X_MS_MediaReceiverRegistrar:1': 'Microsoft Media Services'
    }
    
    # Protocol importance ranking
    protocol_priority = {
        'cast': {'priority': 1, 'name': 'Google Cast', 'description': 'High-value target, media streaming'},
        'samsung_wam': {'priority': 2, 'name': 'Samsung WAM API', 'description': 'Direct API access, good control'},
        'ecp': {'priority': 3, 'name': 'Roku ECP', 'description': 'External Control Protocol, media control'},
        'upnp': {'priority': 4, 'name': 'UPnP/DLNA', 'description': 'Standard media control protocol'},
        'heos_api': {'priority': 5, 'name': 'Denon HEOS API', 'description': 'Proprietary audio control'},
        'musiccast_api': {'priority': 6, 'name': 'Yamaha MusicCast', 'description': 'Proprietary audio control'},
        'jsonrpc_api': {'priority': 7, 'name': 'JSON-RPC', 'description': 'API-based control (Kodi, etc.)'},
        'generic': {'priority': 8, 'name': 'Generic/Unknown', 'description': 'Unknown or limited control'}
    }
    
    ColoredOutput.info("Analyzing device services and protocols...")
    
    for device in devices:
        device_analysis = {
            "device_info": {
                "ip": device.get('ip', 'Unknown'),
                "port": device.get('port', 'Unknown'),
                "friendly_name": device.get('friendlyName', 'Unknown Device'),
                "manufacturer": device.get('manufacturer', 'Unknown'),
                "model": device.get('modelName', 'Unknown'),
                "device_type": device.get('deviceType', 'Unknown')
            },
            "profile_match": None,
            "primary_protocol": 'generic',
            "services": device.get('services', []),
            "high_priority_services": [],
            "medium_priority_services": [],
            "security_concerns": [],
            "control_capabilities": [],
            "priority_score": 0
        }
        
        # Find matching profile
        best_profile = profile_manager.get_best_profile(device)
        if best_profile:
            device_analysis["profile_match"] = {
                "name": best_profile.name,
                "notes": best_profile.notes
            }
            device_analysis["primary_protocol"] = best_profile.get_primary_protocol()
            
            # Get control capabilities
            control_urls = best_profile.get_control_urls()
            if control_urls:
                device_analysis["control_capabilities"] = list(control_urls.keys())
        
        # Analyze services
        for service in device.get('services', []):
            service_type = service.get('serviceType', '')
            
            if service_type in high_priority_services:
                device_analysis["high_priority_services"].append({
                    "type": service_type,
                    "description": high_priority_services[service_type],
                    "control_url": service.get('controlURL', 'Unknown')
                })
                device_analysis["priority_score"] += 10
            
            elif service_type in medium_priority_services:
                device_analysis["medium_priority_services"].append({
                    "type": service_type,
                    "description": medium_priority_services[service_type],
                    "control_url": service.get('controlURL', 'Unknown')
                })
                device_analysis["priority_score"] += 5
        
        # Protocol-based priority scoring
        protocol = device_analysis["primary_protocol"]
        if protocol in protocol_priority:
            protocol_info = protocol_priority[protocol]
            device_analysis["priority_score"] += (10 - protocol_info['priority'])
            device_analysis["protocol_info"] = protocol_info
        
        # Security analysis
        ip = device.get('ip', '')
        port = device.get('port', '')
        
        # Check for common security issues
        if port in [80, 8080]:
            device_analysis["security_concerns"].append("HTTP service exposed (potentially insecure)")
        
        if any('admin' in url.lower() for service in device.get('services', []) 
               for url in [service.get('controlURL', ''), service.get('eventSubURL', '')] if url):
            device_analysis["security_concerns"].append("Administrative interfaces detected")
        
        # Check for known vulnerable services
        vulnerable_services = ['X_MS_MediaReceiverRegistrar', 'DeviceProtection']
        for service in device.get('services', []):
            if any(vuln in service.get('serviceType', '') for vuln in vulnerable_services):
                device_analysis["security_concerns"].append(f"Potentially vulnerable service: {service.get('serviceType', '')}")
        
        # Update protocol distribution
        protocol = device_analysis["primary_protocol"]
        if protocol not in analysis["protocol_distribution"]:
            analysis["protocol_distribution"][protocol] = 0
        analysis["protocol_distribution"][protocol] += 1
        
        # Categorize device by priority
        if device_analysis["priority_score"] >= 20:
            analysis["high_priority_devices"].append(device_analysis)
        elif device_analysis["priority_score"] >= 10:
            analysis["medium_priority_devices"].append(device_analysis)
        elif device_analysis["priority_score"] >= 1:
            analysis["low_priority_devices"].append(device_analysis)
        else:
            analysis["unknown_devices"].append(device_analysis)
        
        # Add security findings
        if device_analysis["security_concerns"]:
            analysis["security_findings"].append({
                "device": f"{device_analysis['device_info']['friendly_name']} ({ip}:{port})",
                "concerns": device_analysis["security_concerns"]
            })
    
    # Generate service summary
    all_services = {}
    for device in devices:
        for service in device.get('services', []):
            service_type = service.get('serviceType', 'Unknown')
            if service_type not in all_services:
                all_services[service_type] = {"count": 0, "devices": []}
            all_services[service_type]["count"] += 1
            all_services[service_type]["devices"].append(device.get('friendlyName', 'Unknown'))
    
    analysis["service_summary"] = dict(sorted(all_services.items(), 
                                            key=lambda x: x[1]["count"], reverse=True))
    
    # Generate recommendations
    high_count = len(analysis["high_priority_devices"])
    medium_count = len(analysis["medium_priority_devices"])
    
    if high_count > 0:
        analysis["recommendations"].append(f"🎯 {high_count} high-priority targets found - focus penetration testing here")
    
    if medium_count > 0:
        analysis["recommendations"].append(f"⚡ {medium_count} medium-priority targets available for secondary testing")
    
    if len(analysis["security_findings"]) > 0:
        analysis["recommendations"].append(f"🔍 {len(analysis['security_findings'])} devices have potential security concerns")
    
    # Protocol-specific recommendations
    if 'cast' in analysis["protocol_distribution"]:
        analysis["recommendations"].append("📱 Chromecast devices found - consider Cast protocol attacks")
    
    if 'samsung_wam' in analysis["protocol_distribution"]:
        analysis["recommendations"].append("🎵 Samsung WAM speakers found - direct API access available")
    
    if 'ecp' in analysis["protocol_distribution"]:
        analysis["recommendations"].append("📺 Roku devices found - ECP protocol exploitation possible")
    
    return analysis


def _print_service_analysis(analysis: Dict[str, Any], args):
    """Print formatted service analysis results."""
    
    ColoredOutput.header(f"Service Analysis Results ({analysis['total_devices']} devices)")
    
    # High Priority Devices
    high_priority = analysis["high_priority_devices"]
    if high_priority:
        ColoredOutput.print(f"\n🎯 HIGH PRIORITY TARGETS ({len(high_priority)} devices)", 'red', bold=True)
        ColoredOutput.print("=" * 60, 'red')
        
        for device in high_priority:
            info = device["device_info"]
            ColoredOutput.print(f"\n📡 {info['friendly_name']}", 'yellow', bold=True)
            ColoredOutput.print(f"   💻 {info['ip']}:{info['port']} | {info['manufacturer']} {info['model']}", 'white')
            
            if device["profile_match"]:
                ColoredOutput.print(f"   🎯 Profile: {device['profile_match']['name']}", 'green')
            
            if device["protocol_info"]:
                pinfo = device["protocol_info"]
                ColoredOutput.print(f"   🔌 Protocol: {pinfo['name']} (Priority: {pinfo['priority']}) - {pinfo['description']}", 'cyan')
            
            ColoredOutput.print(f"   ⭐ Priority Score: {device['priority_score']}", 'yellow')
            
            # High priority services
            if device["high_priority_services"]:
                ColoredOutput.print("   🔥 Critical Services:", 'red')
                for service in device["high_priority_services"]:
                    ColoredOutput.print(f"      • {service['description']}", 'white')
                    if args.verbose:
                        ColoredOutput.print(f"        Control URL: {service['control_url']}", 'gray')
            
            # Control capabilities
            if device["control_capabilities"]:
                ColoredOutput.print(f"   🎮 Control Options: {', '.join(device['control_capabilities'])}", 'green')
            
            # Security concerns
            if device["security_concerns"]:
                ColoredOutput.print("   ⚠️  Security Concerns:", 'yellow')
                for concern in device["security_concerns"]:
                    ColoredOutput.print(f"      • {concern}", 'yellow')
    
    # Medium Priority Devices
    medium_priority = analysis["medium_priority_devices"]
    if medium_priority and getattr(args, 'verbose', False) and not getattr(args, 'minimal', False):
        ColoredOutput.print(f"\n⚡ MEDIUM PRIORITY TARGETS ({len(medium_priority)} devices)", 'yellow', bold=True)
        ColoredOutput.print("=" * 60, 'yellow')
        
        for device in medium_priority:
            info = device["device_info"]
            ColoredOutput.print(f"\n📡 {info['friendly_name']} ({info['ip']}:{info['port']})", 'white')
            if device["profile_match"]:
                ColoredOutput.print(f"   Profile: {device['profile_match']['name']}", 'green')
            ColoredOutput.print(f"   Priority Score: {device['priority_score']}", 'yellow')
    
    # Service Summary
    if not hasattr(args, 'minimal') or not args.minimal:
        ColoredOutput.print(f"\n📊 SERVICE DISTRIBUTION", 'cyan', bold=True)
        ColoredOutput.print("=" * 60, 'cyan')
        
        service_summary = analysis["service_summary"]
        top_services = list(service_summary.items())[:10]  # Top 10 most common
        
        for service_type, info in top_services:
            count = info["count"]
            # Determine if this is a high-priority service
            priority_marker = "🔥" if "AVTransport" in service_type or "RenderingControl" in service_type else "📋"
            ColoredOutput.print(f"{priority_marker} {service_type}", 'white')
            ColoredOutput.print(f"   Found on {count} device(s)", 'gray')
    
    # Protocol Distribution
    ColoredOutput.print(f"\n🔌 PROTOCOL DISTRIBUTION", 'green', bold=True)
    ColoredOutput.print("=" * 60, 'green')
    
    for protocol, count in analysis["protocol_distribution"].items():
        if protocol in {'cast', 'samsung_wam', 'ecp'}:
            ColoredOutput.print(f"🎯 {protocol.upper()}: {count} device(s) (High Value)", 'red')
        elif protocol == 'upnp':
            ColoredOutput.print(f"📡 {protocol.upper()}: {count} device(s) (Standard)", 'yellow')
        else:
            ColoredOutput.print(f"📋 {protocol.upper()}: {count} device(s)", 'white')
    
    # Security Findings
    security_findings = analysis["security_findings"]
    if security_findings:
        ColoredOutput.print(f"\n🔍 SECURITY FINDINGS ({len(security_findings)} devices)", 'red', bold=True)
        ColoredOutput.print("=" * 60, 'red')
        
        for finding in security_findings:
            ColoredOutput.print(f"\n⚠️  {finding['device']}", 'yellow', bold=True)
            for concern in finding["concerns"]:
                ColoredOutput.print(f"   • {concern}", 'white')
    
    # Recommendations
    recommendations = analysis["recommendations"]
    if recommendations:
        ColoredOutput.print(f"\n💡 RECOMMENDATIONS", 'cyan', bold=True)
        ColoredOutput.print("=" * 60, 'cyan')
        
        for i, rec in enumerate(recommendations, 1):
            ColoredOutput.print(f"{i}. {rec}", 'white')
    
    # Summary
    ColoredOutput.print(f"\n📈 SUMMARY", 'magenta', bold=True)
    ColoredOutput.print("=" * 60, 'magenta')
    ColoredOutput.print(f"Total Devices Scanned: {analysis['total_devices']}", 'white')
    ColoredOutput.print(f"High Priority Targets: {len(analysis['high_priority_devices'])}", 'red')
    ColoredOutput.print(f"Medium Priority Targets: {len(analysis['medium_priority_devices'])}", 'yellow')
    ColoredOutput.print(f"Low Priority Targets: {len(analysis['low_priority_devices'])}", 'white')
    ColoredOutput.print(f"Unknown/Generic Devices: {len(analysis['unknown_devices'])}", 'gray')
    ColoredOutput.print(f"Security Concerns Found: {len(security_findings)}", 'red' if security_findings else 'green')


# Auto-Profile Generation with Comprehensive Fuzzing
async def cmd_auto_profile(args) -> Dict[str, Any]:
    """Comprehensive device fuzzing and automatic profile generation."""
    try:
        ColoredOutput.header("🔍 Comprehensive Device Fuzzing & Auto-Profile Generation")
        
        # Discover all devices
        network = args.network or utils.get_en0_network()[1]
        ColoredOutput.info(f"Scanning network: {network}")
        
        devices = await discovery.scan_network_async(
            network,
            use_cache=bool(args.cache)
        )
        
        if not devices:
            ColoredOutput.warning("No devices found for fuzzing and profile generation")
            return {"status": "warning", "message": "No devices found"}
        
        ColoredOutput.success(f"Discovered {len(devices)} devices for comprehensive analysis")
        
        # Perform aggressive fuzzing and service discovery
        ColoredOutput.info("🔥 Starting comprehensive device fuzzing...")
        if getattr(args, 'aggressive', False):
            ColoredOutput.warning("⚠️  Aggressive mode enabled - this may be detected by security systems")
        
        fuzzed_devices = await _comprehensive_device_fuzzing(devices, args)
        
        # Generate profiles
        ColoredOutput.info("🧠 Generating intelligent device profiles...")
        generated_profiles = await _generate_comprehensive_profiles(fuzzed_devices, args)
        
        # Display results
        if getattr(args, 'json', False):
            print(json.dumps(generated_profiles, indent=2))
        else:
            _print_comprehensive_profile_results(generated_profiles, args)
        
        # Save profiles if requested
        if getattr(args, 'save_profiles', False) and not getattr(args, 'preview', False):
            await _save_comprehensive_profiles(generated_profiles, args)
        elif getattr(args, 'preview', False):
            ColoredOutput.info("Preview mode - profiles not saved")
        
        return {"status": "success", "profiles": generated_profiles}
        
    except Exception as e:
        ColoredOutput.error(f"Auto-profile generation failed: {e}")
        if getattr(args, 'verbose', False):
            logger.exception("Auto-profile generation error details")
        return {"status": "error", "message": str(e)}


async def _comprehensive_device_fuzzing(devices: List[Dict[str, Any]], args) -> List[Dict[str, Any]]:
    """
    Perform comprehensive fuzzing on all devices to discover endpoints and capabilities.
    
    This function aggressively probes devices to find:
    - All open ports and services
    - UPnP endpoints and SOAP actions
    - Manufacturer-specific APIs
    - Hidden admin interfaces
    - Vulnerability indicators
    - Control capabilities
    """
    import aiohttp
    import asyncio
    from concurrent.futures import ThreadPoolExecutor
    
    fuzzed_devices = []
    progress = ProgressReporter(len(devices), "Comprehensive Device Fuzzing")
    
    # Create semaphore to limit concurrent connections
    semaphore = asyncio.Semaphore(getattr(args, 'threads', 50))
    
    for device in devices:
        try:
            ip = device.get('ip')
            if not ip:
                continue
                
            device_name = device.get('friendlyName', f"{ip}")
            progress.update(message=f"Fuzzing {device_name}")
            
            # Create comprehensive device analysis
            fuzzed_device = {
                "original_info": device.copy(),
                "ip": ip,
                "discovered_ports": {},
                "upnp_endpoints": {},
                "manufacturer_apis": {},
                "admin_interfaces": {},
                "soap_actions": {},
                "vulnerability_indicators": [],
                "control_surface": {},
                "confidence_data": {},
                "fuzzing_summary": {}
            }
            
            # Phase 1: Aggressive port scanning
            await _aggressive_port_scan(ip, fuzzed_device, args, semaphore)
            
            # Phase 2: UPnP endpoint fuzzing
            await _fuzz_upnp_endpoints(ip, fuzzed_device, args, semaphore)
            
            # Phase 3: Manufacturer API discovery
            await _fuzz_manufacturer_apis(ip, fuzzed_device, args, semaphore)
            
            # Phase 4: Admin interface hunting
            await _hunt_admin_interfaces(ip, fuzzed_device, args, semaphore)
            
            # Phase 5: SOAP action enumeration
            await _enumerate_soap_actions(ip, fuzzed_device, args, semaphore)
            
            # Phase 6: Vulnerability assessment
            await _assess_vulnerabilities(ip, fuzzed_device, args, semaphore)
            
            # Phase 7: Control surface mapping
            await _map_control_surface(ip, fuzzed_device, args, semaphore)
            
            fuzzed_devices.append(fuzzed_device)
            
        except Exception as e:
            ColoredOutput.warning(f"Failed to fuzz {device_name}: {e}")
            continue
    
    progress.finish(f"Comprehensively fuzzed {len(fuzzed_devices)} devices")
    return fuzzed_devices


async def _aggressive_port_scan(ip: str, fuzzed_device: Dict[str, Any], args, semaphore):
    """Aggressively scan ports to find all open services."""
    import socket
    import asyncio
    
    # Define port ranges - be smarter about aggressive mode
    if getattr(args, 'port_range', None):
        start, end = map(int, args.port_range.split('-'))
        ports = list(range(start, end + 1))
    else:
        # Core media/IoT ports that are always checked
        core_ports = [
            # UPnP/DLNA
            1400, 1401, 1900, 2869, 5000, 8080, 8081, 8200,
            # Manufacturer specific
            8060, 8008, 55001, 55002, 9090, 1255, 5005, 8090,
            # Web services
            80, 443, 8443, 8000, 8888, 9000, 9999,
            # RTSP/Media
            554, 8554, 7000, 7084, 1935,
            # Admin/Management
            22, 23, 21, 631, 8631, 8000, 8080, 9090
        ]
        
        if getattr(args, 'aggressive', False):
            # In aggressive mode, add more targeted ports but don't scan ALL ports
            additional_ports = [
                # More web services
                3000, 4000, 4443, 5000, 6000, 7000, 7001, 7070, 7777,
                8000, 8001, 8008, 8080, 8081, 8090, 8443, 8888, 9000, 9001, 9080, 9090, 9999,
                # IoT/Smart home
                8123, 5683, 1883, 8883, 502, 102, 161, 162,
                # Database/services  
                1433, 3306, 5432, 5900, 6379, 11211, 27017,
                # Admin/Debug/Config
                2323, 8728, 8291, 8080, 8000, 9000, 10000, 
                # Media streaming
                1935, 3689, 5353, 32400, 32469,
                # Samsung/LG specific
                8001, 8002, 3001, 9197, 9998,
                # Roku specific  
                8060, 8080, 9080
            ]
            ports = sorted(set(core_ports + additional_ports))
        else:
            ports = sorted(set(core_ports))
    
    ColoredOutput.info(f"   🔍 Port scanning {len(ports)} ports on {ip}")
    
    async def scan_port(port):
        async with semaphore:
            try:
                # TCP connect test with shorter timeout for speed
                _, writer = await asyncio.wait_for(
                    asyncio.open_connection(ip, port),
                    timeout=1.0
                )
                writer.close()
                await writer.wait_closed()
                
                # Service identification
                service_info = await _identify_port_service(ip, port, args)
                fuzzed_device["discovered_ports"][port] = service_info
                
                return port, service_info
            except:
                return None
    
    # Scan ports concurrently but limit for responsiveness
    batch_size = 100 if getattr(args, 'aggressive', False) else 50
    all_results = []
    
    for i in range(0, len(ports), batch_size):
        batch = ports[i:i + batch_size]
        tasks = [scan_port(port) for port in batch]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        all_results.extend(results)
    
    open_ports = [r for r in all_results if r and not isinstance(r, Exception)]
    fuzzed_device["fuzzing_summary"]["open_ports"] = len(open_ports)
    
    if open_ports:
        ColoredOutput.success(f"   ✅ Found {len(open_ports)} open ports on {ip}")
        # In aggressive mode, show which ports were found
        if getattr(args, 'aggressive', False) and len(open_ports) <= 10:
            port_list = [str(r[0]) for r in open_ports]
            ColoredOutput.info(f"       Open ports: {', '.join(port_list)}")


async def _identify_port_service(ip: str, port: int, args) -> Dict[str, Any]:
    """Identify what service is running on a specific port."""
    import aiohttp
    
    service_info = {
        "port": port,
        "protocols": [],
        "service_type": "unknown",
        "banners": {},
        "endpoints": []
    }
    
    # Test HTTP/HTTPS
    for protocol in ["http", "https"]:
        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=3),
                connector=aiohttp.TCPConnector(ssl=False)
            ) as session:
                url = f"{protocol}://{ip}:{port}"
                async with session.get(url) as response:
                    service_info["protocols"].append(protocol)
                    service_info["banners"][protocol] = {
                        "status": response.status,
                        "headers": dict(response.headers),
                        "content_type": response.headers.get('content-type', '')
                    }
                    
                    # Quick content analysis
                    try:
                        content = await response.text()
                        if len(content) < 10000:  # Avoid huge responses
                            service_info["banners"][protocol]["content_sample"] = content[:500]
                            
                            # Service type detection
                            if "upnp" in content.lower():
                                service_info["service_type"] = "upnp"
                            elif "sonos" in content.lower():
                                service_info["service_type"] = "sonos"
                            elif "roku" in content.lower():
                                service_info["service_type"] = "roku"
                            elif "samsung" in content.lower():
                                service_info["service_type"] = "samsung"
                            elif "chromecast" in content.lower() or "cast" in content.lower():
                                service_info["service_type"] = "chromecast"
                    except:
                        pass
                        
        except:
            continue
    
    return service_info


async def _fuzz_upnp_endpoints(ip: str, fuzzed_device: Dict[str, Any], args, semaphore):
    """Fuzz UPnP endpoints to find device descriptions and services."""
    import aiohttp
    
    ColoredOutput.info(f"   📡 Fuzzing UPnP endpoints on {ip}")
    
    # Comprehensive UPnP endpoint wordlist
    upnp_endpoints = [
        # Standard UPnP paths
        "/xml/device_description.xml",
        "/description.xml",
        "/upnp/desc.xml",
        "/device_description.xml",
        "/rootDesc.xml",
        "/description/device.xml",
        
        # Manufacturer specific
        "/MediaRenderer/desc.xml",
        "/MediaRenderer/device_description.xml",
        "/MediaServer/desc.xml",
        "/MediaServer/device_description.xml",
        "/upnp/MediaRenderer.xml",
        "/upnp/MediaServer.xml",
        
        # Sonos specific
        "/xml/zone_player.xml",
        "/status/zp",
        "/xml/device_description.xml",
        "/support/review",
        
        # Samsung specific
        "/xml/device_description.xml",
        "/dmr/dms_description.xml",
        "/dmr/control/AVTransport",
        "/dmr/control/RenderingControl",
        
        # Sony specific
        "/DLNA_MEDIA_RENDERER_1/desc.xml",
        "/DLNA_MEDIA_SERVER_1/desc.xml",
        "/av_renderer_desc.xml",
        
        # LG specific
        "/udap/api/data",
        "/roap/api/command",
        "/upnp/control/AVTransport1",
        "/upnp/control/RenderingControl1",
        
        # Generic patterns
        "/upnp",
        "/control",
        "/service",
        "/api",
        "/desc",
    ]
    
    if args.aggressive:
        # Add more endpoints for aggressive fuzzing
        aggressive_endpoints = [
            "/admin", "/config", "/setup", "/management", "/debug",
            "/system", "/status", "/info", "/version", "/api/v1",
            "/api/v2", "/rest", "/json", "/xml", "/soap", "/cgi-bin",
            "/.well-known", "/robots.txt", "/sitemap.xml"
        ]
        upnp_endpoints.extend(aggressive_endpoints)
    
    discovered_endpoints = {}
    
    async def test_endpoint(endpoint):
        async with semaphore:
            # Test on all discovered ports, not just HTTP-identified ones
            ports_to_test = list(fuzzed_device["discovered_ports"].keys())
            
            # Also test on common web ports even if not discovered
            common_web_ports = [80, 443, 8080, 8000, 8008, 8443, 9080]
            for port in common_web_ports:
                if port not in ports_to_test:
                    ports_to_test.append(port)
            
            for port in ports_to_test:
                for protocol in ["http", "https"]:
                    try:
                        async with aiohttp.ClientSession(
                            timeout=aiohttp.ClientTimeout(total=2),
                            connector=aiohttp.TCPConnector(ssl=False, verify_ssl=False)
                        ) as session:
                            url = f"{protocol}://{ip}:{port}{endpoint}"
                            async with session.get(url) as response:
                                if response.status in [200, 401, 403]:  # Include auth-required responses
                                    content = await response.text()
                                    if len(content) > 10:  # Any meaningful content
                                        endpoint_key = f"{protocol}://{ip}:{port}{endpoint}"
                                        discovered_endpoints[endpoint_key] = {
                                            "status": response.status,
                                            "content_length": len(content),
                                            "content_type": response.headers.get('content-type', ''),
                                            "content_sample": content[:1000],
                                            "headers": dict(response.headers)
                                        }
                                        
                                        # Parse UPnP device descriptions
                                        if "device" in content.lower() and ("upnp" in content.lower() or "xml" in response.headers.get('content-type', '')):
                                            try:
                                                device_info = await _parse_upnp_device_description(content)
                                                discovered_endpoints[endpoint_key]["parsed_device_info"] = device_info
                                            except:
                                                pass
                                        
                                        return endpoint_key
                    except:
                        continue
            return None
    
    # Test endpoints concurrently
    tasks = [test_endpoint(endpoint) for endpoint in upnp_endpoints[:getattr(args, 'max_endpoints', 500)]]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    valid_endpoints = [r for r in results if r and not isinstance(r, Exception)]
    fuzzed_device["upnp_endpoints"] = discovered_endpoints
    fuzzed_device["fuzzing_summary"]["upnp_endpoints"] = len(valid_endpoints)
    
    if valid_endpoints:
        ColoredOutput.success(f"   ✅ Found {len(valid_endpoints)} UPnP endpoints on {ip}")


async def _fuzz_manufacturer_apis(ip: str, fuzzed_device: Dict[str, Any], args, semaphore):
    """Fuzz manufacturer-specific APIs."""
    import aiohttp
    
    ColoredOutput.info(f"   🔌 Fuzzing manufacturer APIs on {ip}")
    
    # Manufacturer-specific API tests
    api_tests = {
        "roku_ecp": {
            "endpoints": [
                "/query/device-info",
                "/query/apps",
                "/launch/2213",
                "/keypress/Home",
                "/input",
                "/query/media-player"
            ],
            "ports": [8060]
        },
        "samsung_wam": {
            "endpoints": [
                "/UIC?cmd=<n>GetSpkName</n>",
                "/UIC?cmd=<n>GetVolume</n>",
                "/UIC?cmd=<n>GetMute</n>",
                "/UIC?cmd=<n>GetFunc</n>",
                "/UIC?cmd=<n>GetMainInfo</n>"
            ],
            "ports": [55001, 55002]
        },
        "chromecast": {
            "endpoints": [
                "/setup/eureka_info",
                "/setup/scan_wifi",
                "/setup/scan_results",
                "/setup/configured_networks",
                "/ssdp/device-desc.xml"
            ],
            "ports": [8008, 8443]
        },
        "yamaha_musiccast": {
            "endpoints": [
                "/YamahaExtendedControl/v1/system/getDeviceInfo",
                "/YamahaExtendedControl/v1/system/getFeatures",
                "/YamahaExtendedControl/v1/main/getStatus",
                "/YamahaExtendedControl/v1/netusb/getSettings"
            ],
            "ports": [5005]
        },
        "denon_heos": {
            "endpoints": [
                "/heos",
                "/heos/browse",
                "/heos/player/get_players",
                "/heos/system/heart_beat"
            ],
            "ports": [1255]
        },
        "bose_soundtouch": {
            "endpoints": [
                "/info",
                "/now_playing",
                "/volume",
                "/sources",
                "/bass",
                "/bassCapabilities"
            ],
            "ports": [8090]
        }
    }
    
    discovered_apis = {}
    
    async def test_api(api_name, api_config):
        async with semaphore:
            for port in api_config["ports"]:
                # Check if port is open
                if port in fuzzed_device["discovered_ports"]:
                    for endpoint in api_config["endpoints"]:
                        for protocol in ["http", "https"]:
                            try:
                                async with aiohttp.ClientSession(
                                    timeout=aiohttp.ClientTimeout(total=3),
                                    connector=aiohttp.TCPConnector(ssl=False)
                                ) as session:
                                    url = f"{protocol}://{ip}:{port}{endpoint}"
                                    async with session.get(url) as response:
                                        if response.status in [200, 201, 202]:
                                            content = await response.text()
                                            
                                            api_key = f"{api_name}_{protocol}_{port}"
                                            if api_key not in discovered_apis:
                                                discovered_apis[api_key] = []
                                            
                                            discovered_apis[api_key].append({
                                                "endpoint": endpoint,
                                                "url": url,
                                                "status": response.status,
                                                "content_length": len(content),
                                                "content_sample": content[:500],
                                                "headers": dict(response.headers)
                                            })
                            except:
                                continue
    
    # Test APIs concurrently
    tasks = [test_api(name, config) for name, config in api_tests.items()]
    await asyncio.gather(*tasks, return_exceptions=True)
    
    fuzzed_device["manufacturer_apis"] = discovered_apis
    fuzzed_device["fuzzing_summary"]["manufacturer_apis"] = len(discovered_apis)
    
    if discovered_apis:
        ColoredOutput.success(f"   ✅ Found {len(discovered_apis)} manufacturer APIs on {ip}")


async def _hunt_admin_interfaces(ip: str, fuzzed_device: Dict[str, Any], args, semaphore):
    """Hunt for admin and configuration interfaces."""
    import aiohttp
    
    ColoredOutput.info(f"   🔐 Hunting admin interfaces on {ip}")
    
    # Admin interface patterns
    admin_paths = [
        "/admin", "/admin/", "/admin/index.html", "/admin/login",
        "/administrator", "/management", "/manager", "/config",
        "/setup", "/setup/", "/setup.html", "/setup.php",
        "/web", "/webui", "/ui", "/console", "/panel",
        "/cgi-bin/admin", "/cgi-bin/config", "/system",
        "/status", "/settings", "/preferences", "/advanced",
        "/debug", "/test", "/api/admin", "/v1/admin"
    ]
    
    if args.aggressive:
        # Add more paths for aggressive mode
        aggressive_paths = [
            "/phpmyadmin", "/adminer", "/mysql", "/database",
            "/shell", "/cmd", "/exec", "/terminal", "/ssh",
            "/backup", "/restore", "/update", "/upgrade",
            "/reboot", "/restart", "/shutdown", "/reset",
            "/logs", "/log", "/error", "/access", "/audit"
        ]
        admin_paths.extend(aggressive_paths)
    
    discovered_admin = {}
    
    async def test_admin_path(path):
        async with semaphore:
            for port in fuzzed_device["discovered_ports"]:
                if "http" in fuzzed_device["discovered_ports"][port].get("protocols", []):
                    for protocol in ["http", "https"]:
                        try:
                            async with aiohttp.ClientSession(
                                timeout=aiohttp.ClientTimeout(total=3),
                                connector=aiohttp.TCPConnector(ssl=False)
                            ) as session:
                                url = f"{protocol}://{ip}:{port}{path}"
                                async with session.get(url, allow_redirects=True) as response:
                                    content = await response.text()
                                    
                                    # Look for admin interface indicators
                                    admin_indicators = [
                                        "login", "password", "username", "admin",
                                        "configuration", "management", "settings",
                                        "control panel", "dashboard", "console"
                                    ]
                                    
                                    content_lower = content.lower()
                                    if any(indicator in content_lower for indicator in admin_indicators):
                                        interface_key = f"{protocol}://{ip}:{port}{path}"
                                        discovered_admin[interface_key] = {
                                            "status": response.status,
                                            "final_url": str(response.url),
                                            "content_length": len(content),
                                            "indicators_found": [ind for ind in admin_indicators if ind in content_lower],
                                            "headers": dict(response.headers),
                                            "content_sample": content[:800]
                                        }
                                        
                                        # Check for authentication
                                        auth_indicators = ["401", "403", "basic auth", "digest auth"]
                                        if response.status in [401, 403] or any(auth in content_lower for auth in auth_indicators):
                                            discovered_admin[interface_key]["requires_auth"] = True
                                        
                                        return interface_key
                        except:
                            continue
            return None
    
    # Test admin paths concurrently
    tasks = [test_admin_path(path) for path in admin_paths]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    valid_admin = [r for r in results if r and not isinstance(r, Exception)]
    fuzzed_device["admin_interfaces"] = discovered_admin
    fuzzed_device["fuzzing_summary"]["admin_interfaces"] = len(valid_admin)
    
    if valid_admin:
        ColoredOutput.success(f"   ✅ Found {len(valid_admin)} admin interfaces on {ip}")
        # Admin interfaces are potential security concerns
        fuzzed_device["vulnerability_indicators"].append(f"Exposed admin interfaces: {len(valid_admin)}")


async def _enumerate_soap_actions(ip: str, fuzzed_device: Dict[str, Any], args, semaphore):
    """Enumerate SOAP actions for UPnP services."""
    import aiohttp
    import xml.etree.ElementTree as ET
    
    ColoredOutput.info(f"   🧼 Enumerating SOAP actions on {ip}")
    
    # Extract UPnP services from discovered endpoints
    services = []
    for endpoint_url, endpoint_data in fuzzed_device["upnp_endpoints"].items():
        if "parsed_device_info" in endpoint_data:
            device_services = endpoint_data["parsed_device_info"].get("services", [])
            for service in device_services:
                service["base_url"] = endpoint_url.split("/xml/")[0] if "/xml/" in endpoint_url else endpoint_url.rsplit("/", 1)[0]
                services.append(service)
    
    discovered_actions = {}
    
    for service in services:
        try:
            service_type = service.get("serviceType", "")
            control_url = service.get("controlURL", "")
            scpd_url = service.get("SCPDURL", "")
            base_url = service.get("base_url", "")
            
            if not control_url or not base_url:
                continue
            
            # Get SCPD (Service Control Point Definition) if available
            if scpd_url:
                try:
                    scpd_full_url = base_url + scpd_url if not scpd_url.startswith("http") else scpd_url
                    async with aiohttp.ClientSession(
                        timeout=aiohttp.ClientTimeout(total=5),
                        connector=aiohttp.TCPConnector(ssl=False)
                    ) as session:
                        async with session.get(scpd_full_url) as response:
                            if response.status == 200:
                                scpd_content = await response.text()
                                actions = _parse_scpd_actions(scpd_content)
                                
                                service_key = f"{service_type}_{control_url}"
                                discovered_actions[service_key] = {
                                    "service_type": service_type,
                                    "control_url": control_url,
                                    "scpd_url": scpd_url,
                                    "actions": actions,
                                    "base_url": base_url
                                }
                except:
                    pass
            
            # Test common SOAP actions even without SCPD
            common_actions = [
                "GetTransportInfo", "GetPositionInfo", "GetMediaInfo",
                "Play", "Pause", "Stop", "Next", "Previous",
                "GetVolume", "SetVolume", "GetMute", "SetMute",
                "Browse", "Search", "CreateObject", "DestroyObject",
                "GetSystemUpdateID", "GetSearchCapabilities",
                "GetConnectionIDs", "GetCurrentConnectionInfo"
            ]
            
            working_actions = []
            for action in common_actions:
                if await _test_soap_action(ip, base_url + control_url, service_type, action, semaphore):
                    working_actions.append(action)
            
            if working_actions:
                service_key = f"{service_type}_{control_url}_tested"
                discovered_actions[service_key] = {
                    "service_type": service_type,
                    "control_url": control_url,
                    "working_actions": working_actions,
                    "base_url": base_url
                }
                
        except Exception as e:
            continue
    
    fuzzed_device["soap_actions"] = discovered_actions
    fuzzed_device["fuzzing_summary"]["soap_services"] = len(discovered_actions)
    
    if discovered_actions:
        ColoredOutput.success(f"   ✅ Enumerated SOAP actions for {len(discovered_actions)} services on {ip}")


def _parse_scpd_actions(scpd_content: str) -> List[Dict[str, Any]]:
    """Parse SCPD XML to extract available actions with robust error handling."""
    try:
        # Use the robust XML parsing
        from . import discovery
        
        # Clean the XML content first
        scpd_content = discovery._sanitize_xml_content(scpd_content)
        scpd_content = discovery._remove_xml_namespaces(scpd_content)
        
        # Parse with fallbacks
        root = discovery._parse_xml_with_fallbacks(scpd_content)
        if root is None:
            logger.debug("Could not parse SCPD XML")
            return []
        
        actions = []
        
        # Find all action elements with multiple strategies
        action_elements = []
        for tag in ['action', 'Action', 'ACTION']:
            found = root.findall(f'.//{tag}')
            if found:
                action_elements.extend(found)
        
        for action_elem in action_elements:
            try:
                # Try multiple ways to find the name
                name_elem = None
                for name_tag in ['name', 'Name', 'NAME']:
                    name_elem = action_elem.find(name_tag)
                    if name_elem is not None and name_elem.text:
                        break
                
                if name_elem is None or not name_elem.text:
                    continue
                
                action_name = name_elem.text.strip()
                
                # Get arguments
                args_in = []
                args_out = []
                
                # Try multiple ways to find argument list
                arg_list = None
                for list_tag in ['argumentList', 'ArgumentList', 'ARGUMENTLIST']:
                    arg_list = action_elem.find(list_tag)
                    if arg_list is not None:
                        break
                
                if arg_list is not None:
                    # Find arguments
                    arguments = []
                    for arg_tag in ['argument', 'Argument', 'ARGUMENT']:
                        found_args = arg_list.findall(arg_tag)
                        if found_args:
                            arguments.extend(found_args)
                    
                    for arg in arguments:
                        try:
                            # Find argument name
                            arg_name_elem = None
                            for name_tag in ['name', 'Name', 'NAME']:
                                arg_name_elem = arg.find(name_tag)
                                if arg_name_elem is not None and arg_name_elem.text:
                                    break
                            
                            # Find argument direction
                            arg_direction_elem = None
                            for dir_tag in ['direction', 'Direction', 'DIRECTION']:
                                arg_direction_elem = arg.find(dir_tag)
                                if arg_direction_elem is not None and arg_direction_elem.text:
                                    break
                            
                            if arg_name_elem is not None and arg_direction_elem is not None:
                                arg_info = {"name": arg_name_elem.text.strip()}
                                direction = arg_direction_elem.text.strip().lower()
                                if direction == "in":
                                    args_in.append(arg_info)
                                else:
                                    args_out.append(arg_info)
                        except Exception:
                            continue
                
                actions.append({
                    "name": action_name,
                    "arguments_in": args_in,
                    "arguments_out": args_out
                })
            except Exception:
                continue
        
        return actions
        
    except Exception as e:
        logger.debug(f"SCPD parsing failed: {e}")
        return []


async def _test_soap_action(ip: str, control_url: str, service_type: str, action: str, semaphore) -> bool:
    """Test if a SOAP action is available."""
    import aiohttp
    
    async with semaphore:
        try:
            # Create minimal SOAP envelope
            soap_envelope = f'''<?xml version="1.0" encoding="utf-8"?>
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
<s:Body>
<u:{action} xmlns:u="{service_type}">
</u:{action}>
</s:Body>
</s:Envelope>'''
            
            headers = {
                'SOAPAction': f'"{service_type}#{action}"',
                'Content-Type': 'text/xml; charset="utf-8"'
            }
            
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=3),
                connector=aiohttp.TCPConnector(ssl=False)
            ) as session:
                async with session.post(control_url, data=soap_envelope, headers=headers) as response:
                    # Action exists if we get any response (even error)
                    return response.status in [200, 500]  # 500 can mean action exists but args are wrong
        except:
            return False


async def _assess_vulnerabilities(ip: str, fuzzed_device: Dict[str, Any], args, semaphore):
    """Assess potential vulnerabilities and security issues."""
    ColoredOutput.info(f"   🔍 Assessing vulnerabilities on {ip}")
    
    vulnerabilities = []
    
    # Check for exposed admin interfaces
    admin_interfaces = fuzzed_device.get("admin_interfaces", {})
    if admin_interfaces:
        vulnerabilities.append({
            "type": "exposed_admin",
            "severity": "HIGH",
            "description": f"Exposed administrative interfaces found: {len(admin_interfaces)}",
            "interfaces": list(admin_interfaces.keys())
        })
    
    # Check for unauthenticated UPnP services
    soap_actions = fuzzed_device.get("soap_actions", {})
    if soap_actions:
        # High severity if we have control actions
        control_actions = []
        for service_key, service_data in soap_actions.items():
            actions = service_data.get("actions", []) + service_data.get("working_actions", [])
            for action in actions:
                action_name = action if isinstance(action, str) else action.get("name", "")
                if action_name in ["Play", "Pause", "Stop", "SetVolume", "SetMute"]:
                    control_actions.append(action_name)
        
        severity = "HIGH" if control_actions else "MEDIUM"
        vulnerabilities.append({
            "type": "unauthenticated_upnp",
            "severity": severity,
            "description": f"Unauthenticated UPnP services allow remote control: {len(soap_actions)} services",
            "services": list(soap_actions.keys()),
            "control_actions": control_actions
        })
    
    # Check for manufacturer API exposure
    manufacturer_apis = fuzzed_device.get("manufacturer_apis", {})
    if manufacturer_apis:
        severity = "HIGH" if getattr(args, 'aggressive', False) else "MEDIUM"
        vulnerabilities.append({
            "type": "exposed_apis",
            "severity": severity, 
            "description": f"Manufacturer APIs exposed: {len(manufacturer_apis)}",
            "apis": list(manufacturer_apis.keys())
        })
    
    # Check discovered ports for security issues
    discovered_ports = fuzzed_device.get("discovered_ports", {})
    for port, service_info in discovered_ports.items():
        # Check for common insecure ports
        if port in [23, 22, 21, 1433, 3306, 5432]:  # Telnet, SSH, FTP, DB ports
            vulnerabilities.append({
                "type": "exposed_service",
                "severity": "HIGH" if port == 23 else "MEDIUM",
                "description": f"Potentially insecure service on port {port}",
                "port": port
            })
        
        # Check for HTTP on unusual ports
        protocols = service_info.get("protocols", [])
        if "http" in protocols and port not in [80, 443, 8080, 8000]:
            vulnerabilities.append({
                "type": "unencrypted_http",
                "severity": "LOW",
                "description": f"HTTP service on non-standard port {port}",
                "port": port
            })
        
        # Check banners for security indicators
        banners = service_info.get("banners", {})
        for protocol, banner in banners.items():
            content = banner.get("content_sample", "").lower()
            headers = banner.get("headers", {})
            
            # Check for authentication requirements
            if banner.get("status") in [401, 403]:
                vulnerabilities.append({
                    "type": "auth_required",
                    "severity": "LOW",
                    "description": f"Authentication required service on port {port} (good security)",
                    "port": port,
                    "status": banner.get("status")
                })
            
            # Check for default credentials hints
            if any(term in content for term in ["default", "admin", "password", "login"]):
                vulnerabilities.append({
                    "type": "potential_default_creds",
                    "severity": "MEDIUM", 
                    "description": f"Potential default credentials on port {port}",
                    "port": port,
                    "protocol": protocol
                })
            
            # Check for sensitive information disclosure
            if any(term in content for term in ["serial", "mac", "ssid", "password", "key"]):
                vulnerabilities.append({
                    "type": "information_disclosure",
                    "severity": "MEDIUM",
                    "description": f"Sensitive information potentially disclosed on port {port}",
                    "port": port
                })
    
    # Check UPnP endpoints for information disclosure
    upnp_endpoints = fuzzed_device.get("upnp_endpoints", {})
    for endpoint_url, endpoint_data in upnp_endpoints.items():
        content = endpoint_data.get("content_sample", "").lower()
        if any(term in content for term in ["serial", "mac address", "ssid", "network", "uuid"]):
            vulnerabilities.append({
                "type": "upnp_info_disclosure",
                "severity": "LOW",
                "description": f"Device information exposed via UPnP endpoint",
                "endpoint": endpoint_url
            })
    
    fuzzed_device["vulnerability_indicators"] = vulnerabilities
    fuzzed_device["fuzzing_summary"]["vulnerabilities"] = len(vulnerabilities)
    
    if vulnerabilities:
        high_severity = len([v for v in vulnerabilities if v["severity"] == "HIGH"])
        medium_severity = len([v for v in vulnerabilities if v["severity"] == "MEDIUM"])
        low_severity = len([v for v in vulnerabilities if v["severity"] == "LOW"])
        
        ColoredOutput.warning(f"   ⚠️  Found {len(vulnerabilities)} vulnerabilities on {ip} (H:{high_severity} M:{medium_severity} L:{low_severity})")
        
        # In aggressive mode, show details
        if args.aggressive:
            for vuln in vulnerabilities[:3]:  # Show first 3
                ColoredOutput.info(f"       • {vuln['severity']}: {vuln['description']}")
    else:
        ColoredOutput.info(f"   ✅ No major vulnerabilities detected on {ip}")


async def _map_control_surface(ip: str, fuzzed_device: Dict[str, Any], args, semaphore):
    """Map the complete control surface of the device."""
    ColoredOutput.info(f"   🎮 Mapping control surface on {ip}")
    
    control_surface = {
        "media_control": [],
        "volume_control": [],
        "power_control": [],
        "configuration": [],
        "information": [],
        "custom_apis": []
    }
    
    # Analyze SOAP actions for control capabilities
    for service_key, service_data in fuzzed_device["soap_actions"].items():
        service_type = service_data.get("service_type", "")
        actions = service_data.get("actions", []) + service_data.get("working_actions", [])
        
        for action in actions:
            action_name = action if isinstance(action, str) else action.get("name", "")
            
            if action_name in ["Play", "Pause", "Stop", "Next", "Previous", "Seek"]:
                control_surface["media_control"].append({
                    "action": action_name,
                    "service": service_type,
                    "control_url": service_data.get("control_url")
                })
            elif action_name in ["GetVolume", "SetVolume", "GetMute", "SetMute"]:
                control_surface["volume_control"].append({
                    "action": action_name,
                    "service": service_type,
                    "control_url": service_data.get("control_url")
                })
            elif action_name in ["GetTransportInfo", "GetPositionInfo", "GetMediaInfo"]:
                control_surface["information"].append({
                    "action": action_name,
                    "service": service_type,
                    "control_url": service_data.get("control_url")
                })
    
    # Analyze manufacturer APIs
    for api_key, api_data in fuzzed_device["manufacturer_apis"].items():
        for endpoint_data in api_data:
            endpoint = endpoint_data["endpoint"]
            
            if any(term in endpoint.lower() for term in ["volume", "mute"]):
                control_surface["volume_control"].append({
                    "endpoint": endpoint,
                    "api": api_key,
                    "url": endpoint_data["url"]
                })
            elif any(term in endpoint.lower() for term in ["play", "pause", "stop"]):
                control_surface["media_control"].append({
                    "endpoint": endpoint,
                    "api": api_key,
                    "url": endpoint_data["url"]
                })
            elif any(term in endpoint.lower() for term in ["info", "status", "device"]):
                control_surface["information"].append({
                    "endpoint": endpoint,
                    "api": api_key,
                    "url": endpoint_data["url"]
                })
            else:
                control_surface["custom_apis"].append({
                    "endpoint": endpoint,
                    "api": api_key,
                    "url": endpoint_data["url"]
                })
    
    fuzzed_device["control_surface"] = control_surface
    
    total_controls = sum(len(controls) for controls in control_surface.values())
    fuzzed_device["fuzzing_summary"]["control_capabilities"] = total_controls
    
    if total_controls > 0:
        ColoredOutput.success(f"   ✅ Mapped {total_controls} control capabilities on {ip}")


async def _parse_upnp_device_description(content: str) -> Dict[str, Any]:
    """Parse UPnP device description XML with robust error handling."""
    
    try:
        # Use the robust parsing function from discovery module
        from . import discovery
        return discovery.parse_device_description(content)
        
    except Exception as e:
        logger.debug(f"Fallback XML parsing failed: {e}")
        return {"parse_error": str(e), "content_sample": content[:300]}


async def _generate_comprehensive_profiles(fuzzed_devices: List[Dict[str, Any]], args) -> Dict[str, Any]:
    """Generate individual device profiles from fuzzing results."""
    import time
    
    generated_profiles = {
        "generation_timestamp": time.time(),
        "total_devices_analyzed": len(fuzzed_devices),
        "profiles": [],
        "fuzzing_summary": {},
        "vulnerability_summary": {},
        "control_surface_summary": {},
        "recommendations": []
    }
    
    # Generate profile for each individual device
    for fuzzed_device in fuzzed_devices:
        original_info = fuzzed_device["original_info"]
        manufacturer = original_info.get('manufacturer', 'Unknown').strip()
        model = original_info.get('modelName', 'Unknown').strip()
        friendly_name = original_info.get('friendlyName', 'Unknown Device').strip()
        ip = fuzzed_device.get("ip", "unknown")
        
        # Use friendly name if manufacturer/model are generic
        if manufacturer == 'Unknown' or model == 'Unknown':
            if friendly_name != 'Unknown Device':
                # Try to extract manufacturer from friendly name
                name_parts = friendly_name.split()
                if len(name_parts) >= 2:
                    manufacturer = name_parts[0] if manufacturer == 'Unknown' else manufacturer
                    model = ' '.join(name_parts[1:]) if model == 'Unknown' else model
        
        # Skip if still no identification
        if manufacturer == 'Unknown' and model == 'Unknown' and friendly_name == 'Unknown Device':
            # Use IP as fallback identifier
            manufacturer = "Generic"
            model = f"Device_{ip.replace('.', '_')}"
        
        profile = await _create_comprehensive_profile(manufacturer, model, [fuzzed_device], args)
        if profile:
            # Add device-specific information
            profile["discovered_on"] = ip
            profile["friendly_name"] = friendly_name
            generated_profiles["profiles"].append(profile)
    
    # Generate comprehensive summaries
    _generate_fuzzing_summaries(fuzzed_devices, generated_profiles)
    _generate_comprehensive_recommendations(fuzzed_devices, generated_profiles)
    
    return generated_profiles


async def _create_comprehensive_profile(manufacturer: str, model: str, devices: List[Dict[str, Any]], args) -> Dict[str, Any]:
    """Create a comprehensive device profile from fuzzing results in profiles.json format."""
    
    if not devices:
        return None
    
    # Use consensus from all devices  
    profile = {
        "name": f"{manufacturer} {model}",
        "match": {
            "manufacturer": [manufacturer],
            "modelName": [model]
        },
        "notes": f"Auto-generated from comprehensive fuzzing of {len(devices)} device(s) on {time.strftime('%Y-%m-%d %H:%M:%S')}"
    }
    
    # Analyze all devices to determine best protocol and create control configuration
    protocol_votes = {}
    all_soap_services = {}
    all_manufacturer_apis = {}
    all_discovered_ports = set()
    total_vulnerabilities = 0
    has_control_capabilities = False
    
    for device in devices:
        ip = device.get("ip")
        
        # Collect discovered ports  
        ports = device.get("discovered_ports", {})
        all_discovered_ports.update(ports.keys())
        
        # Count vulnerabilities
        vulnerabilities = device.get("vulnerability_indicators", [])
        total_vulnerabilities += len(vulnerabilities)
        
        # Analyze SOAP services for UPnP
        soap_actions = device.get("soap_actions", {})
        for service_key, service_data in soap_actions.items():
            service_type = service_data.get("service_type", "")
            if service_type:
                if service_type not in all_soap_services:
                    all_soap_services[service_type] = {
                        "control_urls": set(),
                        "actions": set()
                    }
                
                control_url = service_data.get("control_url", "")
                if control_url:
                    all_soap_services[service_type]["control_urls"].add(control_url)
                
                # Add actions
                actions = service_data.get("actions", []) + service_data.get("working_actions", [])
                for action in actions:
                    action_name = action if isinstance(action, str) else action.get("name", "")
                    if action_name:
                        all_soap_services[service_type]["actions"].add(action_name)
                        has_control_capabilities = True
        
        # Analyze manufacturer APIs
        manufacturer_apis = device.get("manufacturer_apis", {})
        for api_key, api_data in manufacturer_apis.items():
            if "roku" in api_key:
                protocol_votes["ecp"] = protocol_votes.get("ecp", 0) + 1
                all_manufacturer_apis["roku"] = api_data
                has_control_capabilities = True
            elif "samsung" in api_key:
                protocol_votes["samsung_wam"] = protocol_votes.get("samsung_wam", 0) + 1
                all_manufacturer_apis["samsung"] = api_data
                has_control_capabilities = True
            elif "chromecast" in api_key:
                protocol_votes["cast"] = protocol_votes.get("cast", 0) + 1
                all_manufacturer_apis["chromecast"] = api_data
                has_control_capabilities = True
            elif "yamaha" in api_key:
                protocol_votes["musiccast_api"] = protocol_votes.get("musiccast_api", 0) + 1
                all_manufacturer_apis["yamaha"] = api_data
                has_control_capabilities = True
            elif "denon" in api_key or "heos" in api_key:
                protocol_votes["heos_api"] = protocol_votes.get("heos_api", 0) + 1
                all_manufacturer_apis["denon"] = api_data
                has_control_capabilities = True
            elif "bose" in api_key:
                protocol_votes["soundtouch_api"] = protocol_votes.get("soundtouch_api", 0) + 1
                all_manufacturer_apis["bose"] = api_data
                has_control_capabilities = True
        
        # Vote for UPnP if we have SOAP services
        if soap_actions:
            protocol_votes["upnp"] = protocol_votes.get("upnp", 0) + 1
            has_control_capabilities = True
    
    # Don't create profile if no control capabilities found
    if not has_control_capabilities:
        return None
    
    # Select primary protocol
    primary_protocol = "upnp"  # Default
    if protocol_votes:
        primary_protocol = max(protocol_votes.items(), key=lambda x: x[1])[0]
    
    # Add appropriate protocol configuration based on what was discovered
    if primary_protocol == "upnp" and all_soap_services:
        await _add_upnp_config_from_discovery(profile, all_soap_services)
    elif primary_protocol == "ecp" and "roku" in all_manufacturer_apis:
        await _add_roku_config_from_discovery(profile, all_manufacturer_apis["roku"], all_discovered_ports)
    elif primary_protocol == "samsung_wam" and "samsung" in all_manufacturer_apis:
        await _add_samsung_config_from_discovery(profile, all_manufacturer_apis["samsung"], all_discovered_ports)
    elif primary_protocol == "cast" and "chromecast" in all_manufacturer_apis:
        await _add_cast_config_from_discovery(profile, all_manufacturer_apis["chromecast"], all_discovered_ports)
    elif primary_protocol == "musiccast_api" and "yamaha" in all_manufacturer_apis:
        await _add_yamaha_config_from_discovery(profile, all_manufacturer_apis["yamaha"], all_discovered_ports)
    elif primary_protocol == "heos_api" and "denon" in all_manufacturer_apis:
        await _add_denon_config_from_discovery(profile, all_manufacturer_apis["denon"], all_discovered_ports)
    elif primary_protocol == "soundtouch_api" and "bose" in all_manufacturer_apis:
        await _add_bose_config_from_discovery(profile, all_manufacturer_apis["bose"], all_discovered_ports)
    elif all_soap_services:
        # Fallback to UPnP if we have SOAP services
        await _add_upnp_config_from_discovery(profile, all_soap_services)
    else:
        # No usable control interface found
        return None
    
    # Add security and other metadata
    await _add_security_assessment_simple(profile, devices, total_vulnerabilities)
    await _add_comprehensive_match_criteria(profile, devices)
    
    return profile


async def _add_upnp_config_from_discovery(profile: Dict[str, Any], all_soap_services: Dict[str, Any]):
    """Add UPnP configuration in profiles.json format from discovered services."""
    profile["upnp"] = {}
    
    # Convert discovered services to profiles.json format
    service_mapping = {
        "urn:schemas-upnp-org:service:AVTransport:1": "avtransport",
        "urn:schemas-upnp-org:service:RenderingControl:1": "rendering", 
        "urn:schemas-upnp-org:service:ContentDirectory:1": "contentdirectory",
        "urn:schemas-upnp-org:service:ConnectionManager:1": "connectionmanager",
        "urn:schemas-sonos-com:service:Queue:1": "queue",
        "urn:schemas-upnp-org:service:GroupRenderingControl:1": "groupRendering"
    }
    
    for service_type, service_info in all_soap_services.items():
        mapped_name = service_mapping.get(service_type, service_type.split(":")[-1].lower())
        
        # Use the first control URL found
        control_urls = list(service_info["control_urls"])
        if control_urls:
            profile["upnp"][mapped_name] = {
                "serviceType": service_type,
                "controlURL": control_urls[0]
            }
            
            # Add available actions as comment
            actions = list(service_info["actions"])
            if actions:
                profile["upnp"][mapped_name]["availableActions"] = actions[:10]  # Limit for readability


async def _add_samsung_config_from_discovery(profile: Dict[str, Any], samsung_apis: List[Dict[str, Any]], discovered_ports: set):
    """Add Samsung WAM configuration from discovery results."""
    # Determine port from discovery
    samsung_ports = [55001, 55002]
    primary_port = 55001
    for port in samsung_ports:
        if port in discovered_ports:
            primary_port = port
            break
    
    profile["samsung_wam"] = {
        "port": primary_port,
        "commands": {
            "getInfo": "/UIC?cmd=<n>GetSpkName</n>",
            "getVolume": "/UIC?cmd=<n>GetVolume</n>", 
            "setVolume": "/UIC?cmd=<n>SetVolume</n><p type=\"dec\" name=\"volume\" val=\"{VOLUME}\"/>",
            "getMute": "/UIC?cmd=<n>GetMute</n>",
            "setMute": "/UIC?cmd=<n>SetMute</n><p type=\"dec\" name=\"mute\" val=\"{MUTE}\"/>",
            "setUrlPlayback": "/UIC?cmd=<n>SetUrlPlayback</n><p type=\"cdata\" name=\"url\" val=\"empty\"><![CDATA[{MEDIA_URL}]]></p>"
        }
    }
    
    # Add discovered endpoints
    discovered_endpoints = []
    for endpoint_data in samsung_apis:
        endpoint = endpoint_data.get("endpoint", "")
        if endpoint and endpoint not in discovered_endpoints:
            discovered_endpoints.append(endpoint)
    
    if discovered_endpoints:
        profile["samsung_wam"]["discoveredEndpoints"] = discovered_endpoints


async def _add_security_assessment_simple(profile: Dict[str, Any], devices: List[Dict[str, Any]], total_vulnerabilities: int):
    """Add simplified security assessment to profile."""
    if total_vulnerabilities > 0:
        # Add vulnerability count to notes
        profile["notes"] += f" | Discovered {total_vulnerabilities} potential security concerns during fuzzing"


def _generate_security_recommendations(vulnerability_types: Dict, exposed_services: List[str]) -> List[str]:
    """Generate security recommendations based on findings."""
    recommendations = []
    
    if "exposed_admin" in vulnerability_types:
        recommendations.append("🔒 Restrict access to administrative interfaces")
    
    if "unauthenticated_upnp" in vulnerability_types:
        recommendations.append("🛡️ Consider disabling UPnP or restricting network access")
    
    if "default_credentials" in vulnerability_types:
        recommendations.append("🔑 Change default credentials immediately")
    
    if "exposed_apis" in vulnerability_types:
        recommendations.append("🔐 Review manufacturer API exposure")
    
    if "admin_interfaces" in exposed_services:
        recommendations.append("🚫 Block external access to admin ports")
    
    if len(exposed_services) > 2:
        recommendations.append("🔥 Device has large attack surface - consider network segmentation")
    
    return recommendations


async def _add_comprehensive_match_criteria(profile: Dict[str, Any], devices: List[Dict[str, Any]]):
    """Add comprehensive match criteria based on all discovered data."""
    
    # Collect additional identifiers from fuzzing
    device_types = set()
    server_headers = set()
    friendly_names = set()
    service_signatures = set()
    
    for device in devices:
        original_info = device["original_info"]
        
        # Basic identifiers
        device_type = original_info.get("deviceType", "")
        if device_type:
            device_types.add(device_type)
        
        server = original_info.get("ssdp_server", "")
        if server:
            server_headers.add(server)
            
        friendly_name = original_info.get("friendlyName", "")
        if friendly_name:
            # Extract meaningful parts
            name_parts = friendly_name.split()
            for part in name_parts:
                if len(part) > 3 and part.lower() not in ['the', 'and', 'for', 'room', 'player']:
                    friendly_names.add(part)
        
        # Service-based signatures
        for service_key in device.get("soap_actions", {}):
            service_signatures.add(service_key.split("_")[0])  # Extract service type
    
    # Add to match criteria
    if device_types:
        profile["match"]["deviceType"] = list(device_types)
    
    if server_headers:
        profile["match"]["server_header"] = list(server_headers)
    
    if friendly_names and len(friendly_names) <= 5:
        profile["match"]["friendlyName"] = list(friendly_names)
    
    if service_signatures:
        profile["match"]["services"] = list(service_signatures)


async def _add_roku_config_from_discovery(profile: Dict[str, Any], roku_apis: List[Dict[str, Any]], discovered_ports: set):
    """Add Roku ECP configuration from discovery results."""
    # Determine port from discovery  
    roku_port = 8060
    if roku_port in discovered_ports:
        profile["ecp"] = {
            "port": roku_port,
            "launchURL": "/launch/2213",
            "inputURL": "/input"
        }
        
        # Add discovered endpoints
        discovered_endpoints = []
        for endpoint_data in roku_apis:
            endpoint = endpoint_data.get("endpoint", "")
            if endpoint and endpoint not in discovered_endpoints:
                discovered_endpoints.append(endpoint)
        
        if discovered_endpoints:
            profile["ecp"]["discoveredEndpoints"] = discovered_endpoints


async def _add_cast_config_from_discovery(profile: Dict[str, Any], cast_apis: List[Dict[str, Any]], discovered_ports: set):
    """Add Chromecast configuration from discovery results."""
    cast_port = 8008
    if cast_port in discovered_ports:
        profile["cast"] = {
            "port": cast_port,
            "setup_url": "/setup/eureka_info",
            "notes": "Requires pychromecast library for full control"
        }


async def _add_yamaha_config_from_discovery(profile: Dict[str, Any], yamaha_apis: List[Dict[str, Any]], discovered_ports: set):
    """Add Yamaha MusicCast configuration from discovery results."""
    yamaha_port = 5005
    if yamaha_port in discovered_ports:
        profile["musiccast_api"] = {
            "port": yamaha_port,
            "base_path": "/YamahaExtendedControl/v1",
            "endpoints": {
                "device_info": "/system/getDeviceInfo",
                "features": "/system/getFeatures",
                "status": "/main/getStatus", 
                "volume": "/main/setVolume?volume={VOLUME}"
            }
        }


async def _add_denon_config_from_discovery(profile: Dict[str, Any], denon_apis: List[Dict[str, Any]], discovered_ports: set):
    """Add Denon HEOS configuration from discovery results."""
    denon_port = 1255
    if denon_port in discovered_ports:
        profile["heos_api"] = {
            "port": denon_port,
            "endpoints": {
                "players": "/heos/player/get_players",
                "heartbeat": "/heos/system/heart_beat"
            }
        }


async def _add_bose_config_from_discovery(profile: Dict[str, Any], bose_apis: List[Dict[str, Any]], discovered_ports: set):
    """Add Bose SoundTouch configuration from discovery results.""" 
    bose_port = 8090
    if bose_port in discovered_ports:
        profile["soundtouch_api"] = {
            "port": bose_port,
            "endpoints": {
                "info": "/info",
                "volume": "/volume",
                "sources": "/sources"
            }
        }


def _generate_fuzzing_summaries(fuzzed_devices: List[Dict[str, Any]], generated_profiles: Dict[str, Any]):
    """Generate comprehensive fuzzing summaries."""
    
    # Aggregate fuzzing statistics
    total_ports = sum(len(d.get("discovered_ports", {})) for d in fuzzed_devices)
    total_endpoints = sum(len(d.get("upnp_endpoints", {})) for d in fuzzed_devices)
    total_apis = sum(len(d.get("manufacturer_apis", {})) for d in fuzzed_devices)
    total_admin = sum(len(d.get("admin_interfaces", {})) for d in fuzzed_devices)
    total_soap = sum(len(d.get("soap_actions", {})) for d in fuzzed_devices)
    total_vulns = sum(len(d.get("vulnerability_indicators", [])) for d in fuzzed_devices)
    
    generated_profiles["fuzzing_summary"] = {
        "total_ports_discovered": total_ports,
        "total_upnp_endpoints": total_endpoints,
        "total_manufacturer_apis": total_apis,
        "total_admin_interfaces": total_admin,
        "total_soap_services": total_soap,
        "total_vulnerabilities": total_vulns,
        "devices_with_vulns": len([d for d in fuzzed_devices if d.get("vulnerability_indicators")]),
        "high_risk_devices": len([d for d in fuzzed_devices 
                                if len([v for v in d.get("vulnerability_indicators", []) 
                                       if v.get("severity") == "HIGH"]) > 0])
    }
    
    # Vulnerability breakdown
    vuln_types = {}
    for device in fuzzed_devices:
        for vuln in device.get("vulnerability_indicators", []):
            vuln_type = vuln.get("type", "unknown")
            if vuln_type not in vuln_types:
                vuln_types[vuln_type] = {"count": 0, "severity": vuln.get("severity", "LOW")}
            vuln_types[vuln_type]["count"] += 1
    
    generated_profiles["vulnerability_summary"] = vuln_types
    
    # Control surface summary
    control_stats = {
        "media_control": 0,
        "volume_control": 0,
        "configuration": 0,
        "information": 0
    }
    
    for device in fuzzed_devices:
        control_surface = device.get("control_surface", {})
        for category, controls in control_surface.items():
            if category in control_stats:
                control_stats[category] += len(controls)
    
    generated_profiles["control_surface_summary"] = control_stats


def _generate_comprehensive_recommendations(fuzzed_devices: List[Dict[str, Any]], generated_profiles: Dict[str, Any]):
    """Generate comprehensive recommendations."""
    recommendations = []
    
    profiles_count = len(generated_profiles["profiles"])
    devices_count = len(fuzzed_devices)
    fuzzing_summary = generated_profiles["fuzzing_summary"]
    
    # Profile generation recommendations
    if profiles_count > 0:
        recommendations.append(f"✅ Successfully generated {profiles_count} comprehensive device profiles")
        
        high_confidence = len([p for p in generated_profiles["profiles"] if p.get("confidence_score", 0) >= 0.8])
        if high_confidence > 0:
            recommendations.append(f"🎯 {high_confidence} profiles have high confidence (≥80%)")
    
    # Security recommendations
    high_risk = fuzzing_summary.get("high_risk_devices", 0)
    if high_risk > 0:
        recommendations.append(f"🚨 {high_risk} devices have HIGH severity vulnerabilities - immediate action required")
    
    admin_interfaces = fuzzing_summary.get("total_admin_interfaces", 0)
    if admin_interfaces > 0:
        recommendations.append(f"🔐 {admin_interfaces} administrative interfaces exposed - restrict access")
    
    # Control surface recommendations  
    control_summary = generated_profiles.get("control_surface_summary", {})
    total_controls = sum(control_summary.values())
    if total_controls > 0:
        recommendations.append(f"🎮 Mapped {total_controls} control endpoints across all devices")
        
        media_controls = control_summary.get("media_control", 0)
        if media_controls > 0:
            recommendations.append(f"📺 {media_controls} media control endpoints available for automation")
    
    # Fuzzing effectiveness recommendations
    if fuzzing_summary.get("total_ports_discovered", 0) > devices_count * 5:
        recommendations.append(f"🔍 Comprehensive port scanning effective - avg {fuzzing_summary['total_ports_discovered'] // devices_count} ports per device")
    
    if fuzzing_summary.get("total_manufacturer_apis", 0) > 0:
        recommendations.append(f"🔌 Found {fuzzing_summary['total_manufacturer_apis']} proprietary API endpoints")
    
    generated_profiles["recommendations"] = recommendations


def _print_comprehensive_profile_results(generated_profiles: Dict[str, Any], args):
    """Print comprehensive profile generation results."""
    
    profiles = generated_profiles["profiles"]
    fuzzing_summary = generated_profiles["fuzzing_summary"]
    
    ColoredOutput.header(f"🔍 Comprehensive Auto-Profile Generation Results")
    ColoredOutput.print(f"Devices Analyzed: {generated_profiles['total_devices_analyzed']}", 'white')
    ColoredOutput.print(f"Profiles Generated: {len(profiles)}", 'green', bold=True)
    
    # Fuzzing effectiveness summary
    ColoredOutput.print(f"\n📊 FUZZING EFFECTIVENESS", 'cyan', bold=True)
    ColoredOutput.print("=" * 50, 'cyan')
    ColoredOutput.print(f"Total Ports Discovered: {fuzzing_summary.get('total_ports_discovered', 0)}", 'white')
    ColoredOutput.print(f"UPnP Endpoints Found: {fuzzing_summary.get('total_upnp_endpoints', 0)}", 'white')
    ColoredOutput.print(f"Manufacturer APIs: {fuzzing_summary.get('total_manufacturer_apis', 0)}", 'white')
    ColoredOutput.print(f"Admin Interfaces: {fuzzing_summary.get('total_admin_interfaces', 0)}", 'yellow')
    ColoredOutput.print(f"SOAP Services: {fuzzing_summary.get('total_soap_services', 0)}", 'white')
    
    # Security summary
    ColoredOutput.print(f"\n🔒 SECURITY ANALYSIS", 'red', bold=True)
    ColoredOutput.print("=" * 50, 'red')
    ColoredOutput.print(f"Total Vulnerabilities: {fuzzing_summary.get('total_vulnerabilities', 0)}", 'white')
    ColoredOutput.print(f"Devices with Vulnerabilities: {fuzzing_summary.get('devices_with_vulns', 0)}", 'yellow')
    ColoredOutput.print(f"High Risk Devices: {fuzzing_summary.get('high_risk_devices', 0)}", 'red')
    
    if not profiles:
        ColoredOutput.warning("No profiles could be generated with sufficient confidence")
        return
    
    # Group profiles by protocol and confidence
    high_confidence = [p for p in profiles if p.get("confidence_score", 0) >= 0.8]
    medium_confidence = [p for p in profiles if 0.5 <= p.get("confidence_score", 0) < 0.8]
    
    if high_confidence:
        ColoredOutput.print(f"\n🎯 HIGH CONFIDENCE PROFILES ({len(high_confidence)})", 'green', bold=True)
        ColoredOutput.print("=" * 50, 'green')
        
        for profile in high_confidence:
            name = profile["name"]
            confidence = profile.get("confidence_score", 0.0)
            protocol = profile.get("primary_protocol", "unknown")
            device_count = profile.get("generated_from", 1)
            risk_level = profile.get("security_assessment", {}).get("risk_level", "UNKNOWN")
            
            risk_color = {"HIGH": "red", "MEDIUM": "yellow", "LOW": "green"}.get(risk_level, "white")
            
            ColoredOutput.print(f"\n🟢 {name}", 'white', bold=True)
            ColoredOutput.print(f"   Confidence: {confidence:.1%} | Protocol: {protocol.upper()} | Devices: {device_count}", 'gray')
            ColoredOutput.print(f"   Security Risk: {risk_level}", risk_color)
            
            # Show key capabilities
            if protocol == "upnp" and "upnp" in profile:
                services = list(profile["upnp"].keys())
                ColoredOutput.print(f"   UPnP Services: {', '.join(services[:3])}{'...' if len(services) > 3 else ''}", 'cyan')
            
            # Show security findings
            security = profile.get("security_assessment", {})
            vuln_types = security.get("vulnerability_types", {})
            if vuln_types:
                critical_vulns = [v for v, data in vuln_types.items() if data.get("severity") == "HIGH"]
                if critical_vulns:
                    ColoredOutput.print(f"   ⚠️  Critical: {', '.join(critical_vulns)}", 'red')
    
    if medium_confidence:
        ColoredOutput.print(f"\n🟡 MEDIUM CONFIDENCE PROFILES ({len(medium_confidence)})", 'yellow', bold=True)
        ColoredOutput.print("=" * 50, 'yellow')
        
        for profile in medium_confidence:
            name = profile["name"]
            confidence = profile.get("confidence_score", 0.0)
            protocol = profile.get("primary_protocol", "unknown")
            ColoredOutput.print(f"🟡 {name} ({confidence:.1%}, {protocol.upper()})", 'white')
    
    # Show recommendations
    recommendations = generated_profiles.get("recommendations", [])
    if recommendations:
        ColoredOutput.print(f"\n💡 COMPREHENSIVE RECOMMENDATIONS", 'magenta', bold=True)
        ColoredOutput.print("=" * 50, 'magenta')
        
        for i, rec in enumerate(recommendations, 1):
            ColoredOutput.print(f"{i}. {rec}", 'white')


async def _save_comprehensive_profiles(generated_profiles: Dict[str, Any], args):
    """Save comprehensive profiles with full fuzzing data."""
    try:
        save_path = Path(args.save_profiles)
        
        # Create directory if needed
        if save_path.is_dir() or not save_path.suffix:
            save_dir = save_path
            save_dir.mkdir(parents=True, exist_ok=True)
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            save_file = save_dir / f"comprehensive_profiles_{timestamp}.json"
        else:
            save_file = save_path
            save_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Prepare comprehensive data package
        complete_data = {
            "metadata": {
                "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "tool_version": config.VERSION,
                "generation_method": "comprehensive_fuzzing",
                "total_devices": generated_profiles["total_devices_analyzed"],
                "profiles_generated": len(generated_profiles["profiles"])
            },
            "fuzzing_summary": generated_profiles["fuzzing_summary"],
            "vulnerability_summary": generated_profiles["vulnerability_summary"],
            "control_surface_summary": generated_profiles["control_surface_summary"],
            "device_profiles": generated_profiles["profiles"],
            "recommendations": generated_profiles["recommendations"]
        }
        
        with open(save_file, 'w') as f:
            json.dump(complete_data, f, indent=2)
        
        ColoredOutput.success(f"Comprehensive profiles saved to: {save_file}")
        
        # Save individual profile files if requested
        if getattr(args, 'individual_files', False):
            individual_dir = save_file.parent / f"{save_file.stem}_individual"
            individual_dir.mkdir(exist_ok=True)
            
            for profile in generated_profiles["profiles"]:
                profile_name = profile["name"].replace(" ", "_").replace("/", "_")
                confidence = profile.get("confidence_score", 0)
                individual_file = individual_dir / f"{profile_name}_conf{confidence:.0%}.json"
                
                with open(individual_file, 'w') as f:
                    json.dump(profile, f, indent=2)
            
            ColoredOutput.info(f"Individual profile files saved to: {individual_dir}")
        
    except Exception as e:
        ColoredOutput.error(f"Failed to save comprehensive profiles: {e}")


# API Generation Command
async def cmd_generate_api(args) -> Dict[str, Any]:
    """Generate REST API from enhanced profile."""
    try:
        from pathlib import Path
        import sys
        
        ColoredOutput.info("🚀 Generating REST API from enhanced profile...")
        
        # Validate profile file exists
        profile_file = Path(args.profile_file)
        if not profile_file.exists():
            ColoredOutput.error(f"❌ Profile file not found: {profile_file}")
            return {"status": "error", "message": "Profile file not found"}
        
        # Set output directory
        if args.output_dir:
            output_dir = Path(args.output_dir)
        else:
            output_dir = Path("generated_apis") / profile_file.stem
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        ColoredOutput.info(f"📁 Output directory: {output_dir}")
        
        # Import the API generator
        try:
            from upnp_cli.api_generator.profile_to_api import generate_profile_api
        except ImportError as e:
            ColoredOutput.error(f"❌ Could not import API generator: {e}")
            return {"status": "error", "message": "API generator not available"}
        
        # Generate the API
        try:
            result = await generate_profile_api(profile_file, output_dir)
            
            if result.get("status") == "success":
                ColoredOutput.success("✅ REST API generated successfully!")
                ColoredOutput.info(f"📂 API files saved to: {output_dir}")
                
                api_file = output_dir / result.get("api_file", "api.py")
                if api_file.exists():
                    ColoredOutput.info(f"🚀 Start API with: cd {output_dir} && python {api_file.name}")
                    ColoredOutput.info(f"📚 Documentation at: http://localhost:8000/docs")
                
                return {
                    "status": "success",
                    "api_file": str(api_file),
                    "output_dir": str(output_dir),
                    "profile_file": str(profile_file)
                }
            else:
                ColoredOutput.error(f"❌ API generation failed: {result.get('message', 'Unknown error')}")
                return {"status": "error", "message": result.get("message", "API generation failed")}
                
        except Exception as e:
            ColoredOutput.error(f"❌ Error during API generation: {e}")
            if args.verbose:
                logger.exception("API generation error details")
            return {"status": "error", "message": str(e)}
            
    except Exception as e:
        ColoredOutput.error(f"❌ Unexpected error in API generation: {e}")
        if args.verbose:
            logger.exception("Unexpected error details")
        return {"status": "error", "message": str(e)}


# Cache Management Commands
async def cmd_clear_cache(args) -> Dict[str, Any]:
    """Clear the device cache."""
    try:
        if args.cache:
            cache_manager = cache.DeviceCache(Path(args.cache))
            cache_manager.clear()
            ColoredOutput.success(f"Cache cleared: {args.cache}")
        else:
            # Clear default cache
            default_cache = Path.home() / '.upnp_cli' / 'devices_cache.db'
            if default_cache.exists():
                default_cache.unlink()
                ColoredOutput.success(f"Default cache cleared: {default_cache}")
            else:
                ColoredOutput.info("No cache file found to clear")
        
        return {"status": "success", "message": "Cache cleared"}
        
    except Exception as e:
        ColoredOutput.error(f"Failed to clear cache: {e}")
        return {"status": "error", "message": str(e)}


# HTTP Server Commands
async def cmd_start_server(args) -> Dict[str, Any]:
    """Start the local HTTP server."""
    try:
        result = http_server.start_media_server(args.server_port)
        
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            status = result.get('status', 'unknown')
            if status == 'running':
                ColoredOutput.success(f"HTTP server started on port {result['port']}")
                ColoredOutput.info(f"Server URL: http://{result['local_ip']}:{result['port']}")
                if 'fart_url' in result:
                    ColoredOutput.info(f"Fart URL: {result['fart_url']}")
            elif status == 'already_running':
                ColoredOutput.warning(f"HTTP server already running on port {result['port']}")
                if result.get('local_ip'):
                    ColoredOutput.info(f"Server URL: http://{result['local_ip']}:{result['port']}")
            else:
                ColoredOutput.error(f"Failed to start server: {result.get('error', 'Unknown error')}")
        
        return result
        
    except Exception as e:
        ColoredOutput.error(f"Failed to start server: {e}")
        return {"status": "error", "message": str(e)}


async def cmd_stop_server(args) -> Dict[str, Any]:
    """Stop the local HTTP server."""
    try:
        port = getattr(args, 'server_port', 8080)
        result = http_server.stop_media_server(port)
        
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            status = result.get('status', 'unknown')
            if status == 'stopped':
                ColoredOutput.success("HTTP server stopped")
            elif status == 'not_running':
                ColoredOutput.warning("HTTP server was not running")
            else:
                ColoredOutput.error(f"Error stopping server: {result.get('error', 'Unknown error')}")
        
        return result
        
    except Exception as e:
        ColoredOutput.error(f"Failed to stop server: {e}")
        return {"status": "error", "message": str(e)}


# Utility Functions moved to upnp_cli.cli.utils


async def cmd_tutorial(args) -> Dict[str, Any]:
    """Run interactive tutorials for new users."""
    try:
        ColoredOutput.header(f"📚 UPnP CLI Tutorial: {args.type.title()}")
        
        tutorials = {
            'basic': [
                ("Welcome", "This tutorial will teach you UPnP CLI basics"),
                ("Discovery", "First, let's discover devices on your network", "upnp-cli discover"),
                ("Device Info", "Get detailed info about a device", "upnp-cli info --host <IP>"),
                ("Interactive Mode", "Use interactive mode for full control", "upnp-cli interactive --host <IP>"),
                ("Completion", "You're ready to use UPnP CLI!")
            ],
            'security': [
                ("Security Testing", "Learn to perform UPnP security assessments"),
                ("Mass Scanning", "Scan entire networks for UPnP devices", "upnp-cli mass-scan"),
                ("Device Profiling", "Generate comprehensive profiles", "upnp-cli auto-profile --aggressive"),
                ("SSL Testing", "Check for SSL vulnerabilities", "upnp-cli ssl-scan --host <IP>"),
                ("RTSP Discovery", "Find video streams", "upnp-cli rtsp-scan --host <IP>"),
                ("Completion", "You're ready for UPnP penetration testing!")
            ],
            'media': [
                ("Media Control", "Learn to control media devices"),
                ("Auto-Discovery", "Find media devices automatically", "upnp-cli discover"),
                ("Playback Control", "Control media playback", "upnp-cli play"),
                ("Volume Control", "Adjust volume levels", "upnp-cli set-volume 50"),
                ("Interactive Control", "Advanced media control", "upnp-cli interactive"),
                ("Completion", "You can now control UPnP media devices!")
            ]
        }
        
        tutorial_steps = tutorials.get(args.type, tutorials['basic'])
        
        for i, step in enumerate(tutorial_steps, 1):
            ColoredOutput.print(f"\n📖 Step {i}: {step[0]}", 'cyan', bold=True)
            ColoredOutput.print(f"   {step[1]}", 'white')
            
            if len(step) > 2:  # Has command example
                ColoredOutput.print(f"\n💡 Try this command:", 'yellow')
                ColoredOutput.print(f"   $ {step[2]}", 'green')
            
            if i < len(tutorial_steps):
                try:
                    input(ColoredOutput.format_text("⏭️  Press Enter to continue (Ctrl+C to exit)...", 'gray'))
                except KeyboardInterrupt:
                    ColoredOutput.warning("\n📚 Tutorial interrupted")
                    return {"status": "cancelled"}
        
        ColoredOutput.success("🎉 Tutorial completed! You're ready to use UPnP CLI.")
        return {"status": "success", "tutorial": args.type}
        
    except Exception as e:
        ColoredOutput.error(f"Tutorial failed: {e}")
        return {"status": "error", "message": str(e)}


async def cmd_menu(args) -> Dict[str, Any]:
    """Interactive main menu for guided navigation."""
    try:
        while True:
            ColoredOutput.header("🎮 UPnP CLI - Main Menu")
            
            ColoredOutput.print("🔍 Quick Actions:", 'cyan', bold=True)
            ColoredOutput.print("  1. Discover devices on network", 'white')
            ColoredOutput.print("  2. Interactive device control", 'white')
            ColoredOutput.print("  3. Security testing workflow", 'white')
            ColoredOutput.print("  4. Media control workflow", 'white')
            
            ColoredOutput.print("\n📚 Learning:", 'cyan', bold=True)
            ColoredOutput.print("  5. Basic tutorial", 'white')
            ColoredOutput.print("  6. Security testing tutorial", 'white')
            ColoredOutput.print("  7. Media control tutorial", 'white')
            
            ColoredOutput.print("\n⚙️  Advanced:", 'cyan', bold=True)
            ColoredOutput.print("  8. Mass network scanning", 'white')
            ColoredOutput.print("  9. Comprehensive device profiling", 'white')
            ColoredOutput.print("  0. Exit", 'red')
            
            try:
                choice = input(ColoredOutput.format_text("\n🎯 Select option: ", 'yellow')).strip()
            except KeyboardInterrupt:
                ColoredOutput.warning("\n👋 Goodbye!")
                break
            
            if choice == '0':
                ColoredOutput.info("👋 Goodbye!")
                break
            elif choice == '1':
                result = await cmd_discover(args)
            elif choice == '2':
                result = await cmd_interactive_control(args)
            elif choice == '3':
                result = await cmd_mass_scan_services(args)
            elif choice == '4':
                ColoredOutput.info("Starting media control workflow...")
                result = await cmd_play(args)
            elif choice == '5':
                args.type = 'basic'
                result = await cmd_tutorial(args)
            elif choice == '6':
                args.type = 'security'
                result = await cmd_tutorial(args)
            elif choice == '7':
                args.type = 'media'
                result = await cmd_tutorial(args)
            elif choice == '8':
                result = await cmd_mass_scan_services(args)
            elif choice == '9':
                # Set default values for auto-profile command when called from menu
                if not hasattr(args, 'aggressive'):
                    args.aggressive = False
                if not hasattr(args, 'preview'): 
                    args.preview = False
                if not hasattr(args, 'save_profiles'):
                    args.save_profiles = False
                if not hasattr(args, 'port_range'):
                    args.port_range = None
                if not hasattr(args, 'minimal'):
                    args.minimal = False
                if not hasattr(args, 'threads'):
                    args.threads = 50
                if not hasattr(args, 'max_endpoints'):
                    args.max_endpoints = 500
                if not hasattr(args, 'min_confidence'):
                    args.min_confidence = 0.5
                if not hasattr(args, 'individual_files'):
                    args.individual_files = False
                result = await cmd_auto_profile(args)
            else:
                ColoredOutput.warning("⚠️  Invalid choice. Please select a number from the menu.")
                continue
            
            if choice != '0':
                input(ColoredOutput.format_text("\n⏸️  Press Enter to return to menu...", 'gray'))
        
        return {"status": "success", "message": "Menu session completed"}
        
    except Exception as e:
        ColoredOutput.error(f"Menu failed: {e}")
        return {"status": "error", "message": str(e)}


def create_parser() -> argparse.ArgumentParser:
    """Create the main argument parser with all subcommands."""
    parser = argparse.ArgumentParser(
        prog='upnp-cli',
        description='Ultimate UPnP Pentest & Control CLI - Discover, analyze, and control UPnP devices',
        epilog='''
Examples:
  upnp-cli discover                    # Find devices on network
  upnp-cli play --host 192.168.1.100  # Start playback on device
  upnp-cli interactive                 # Interactive SOAP controller
  upnp-cli mass-scan --save-report     # Comprehensive security scan
  
Workflows:
  Getting Started: discover → info → services → interactive
  Media Control:   discover → play → set-volume → stop  
  Security Test:   mass-scan → auto-profile → ssl-scan
        ''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # Global arguments
    parser.add_argument('--version', action='version', version=f'upnp-cli {config.VERSION}')
    parser.add_argument('--host', help='Target device IP address')
    parser.add_argument('--port', type=int, default=1400, help='Target device port (default: 1400)')
    parser.add_argument('--use-ssl', action='store_true', help='Use HTTPS instead of HTTP')
    parser.add_argument('--ssl-port', type=int, default=1443, help='SSL port (default: 1443)')
    parser.add_argument('--rtsp-port', type=int, default=7000, help='RTSP port (default: 7000)')
    parser.add_argument('--timeout', type=int, default=10, help='Request timeout in seconds (default: 10)')
    parser.add_argument('--stealth', action='store_true', help='Enable stealth mode (slower, harder to detect)')
    parser.add_argument('--cache', help='Cache file path for storing discovered devices')
    parser.add_argument('--force-scan', action='store_true', help='Force new scan even if cache exists')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without executing')
    parser.add_argument('--json', action='store_true', help='Output results in JSON format')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose output')
    parser.add_argument('--network', help='Network range to scan (e.g., 192.168.1.0/24)')
    
    # Create subparsers
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Discovery commands
    discover_parser = subparsers.add_parser('discover', help='Discover UPnP devices')
    discover_parser.add_argument('--ssdp-only', action='store_true', help='Use SSDP discovery only (faster)')
    discover_parser.set_defaults(func=cmd_discover)
    
    info_parser = subparsers.add_parser('info', help='Get device information')
    
    services_parser = subparsers.add_parser('services', help='List device services')
    
    # Media control commands
    play_parser = subparsers.add_parser('play', help='Start playback')
    
    pause_parser = subparsers.add_parser('pause', help='Pause playback')
    
    stop_parser = subparsers.add_parser('stop', help='Stop playback')
    
    next_parser = subparsers.add_parser('next', help='Skip to next track')
    
    prev_parser = subparsers.add_parser('previous', help='Skip to previous track')
    
    get_vol_parser = subparsers.add_parser('get-volume', help='Get current volume')
    
    set_vol_parser = subparsers.add_parser('set-volume', help='Set volume level')
    set_vol_parser.add_argument('level', type=int, help='Volume level (0-100)')
    
    get_mute_parser = subparsers.add_parser('get-mute', help='Get mute status')
    
    set_mute_parser = subparsers.add_parser('set-mute', help='Set mute status')
    set_mute_parser.add_argument('mute', type=int, choices=[0, 1], help='Mute state (0=unmute, 1=mute)')
    
    # Security scanning commands
    ssl_parser = subparsers.add_parser('ssl-scan', help='Perform SSL/TLS security scan')
    
    rtsp_parser = subparsers.add_parser('rtsp-scan', help='Discover RTSP streams')
    
    # Routine commands
    routine_parser = subparsers.add_parser('routine', help='Execute a routine')
    routine_parser.add_argument('routine_name', help='Name of the routine to execute')
    routine_parser.add_argument('--media-file', default='fart.mp3', help='Media file to use (default: fart.mp3)')
    routine_parser.add_argument('--server-port', type=int, default=8080, help='HTTP server port (default: 8080)')
    routine_parser.add_argument('--volume', type=int, default=50, help='Playback volume (default: 50)')
    
    list_routines_parser = subparsers.add_parser('list-routines', help='List available routines')
    
    # Mass operation commands
    mass_parser = subparsers.add_parser('mass', help='Mass discovery and operations')
    mass_parser.add_argument('--routine', help='Routine to execute on all discovered devices')
    mass_parser.add_argument('--media-file', default='fart.mp3', help='Media file to use (default: fart.mp3)')
    mass_parser.add_argument('--server-port', type=int, default=8080, help='HTTP server port (default: 8080)')
    mass_parser.add_argument('--volume', type=int, default=50, help='Playback volume (default: 50)')
    
    # Mass service scanning command
    mass_scan_parser = subparsers.add_parser('mass-scan', help='Mass service scanning with prioritization')
    mass_scan_parser.add_argument('--minimal', action='store_true', help='Show minimal output (only high priority devices)')
    mass_scan_parser.add_argument('--save-report', help='Save detailed report to file')
    
    # Auto-profile fuzzing command
    auto_profile_parser = subparsers.add_parser('auto-profile', help='Comprehensive device fuzzing and automatic profile generation')
    auto_profile_parser.add_argument('--save-profiles', help='Directory or file to save generated profiles')
    auto_profile_parser.add_argument('--individual-files', action='store_true', help='Save individual profile files')
    auto_profile_parser.add_argument('--min-confidence', type=float, default=0.5, help='Minimum confidence score for profiles (default: 0.5)')
    auto_profile_parser.add_argument('--aggressive', action='store_true', help='Enable aggressive fuzzing (more intrusive)')
    auto_profile_parser.add_argument('--preview', action='store_true', help='Preview profiles without saving')
    auto_profile_parser.add_argument('--port-range', help='Custom port range to scan (e.g., 1-65535)')
    auto_profile_parser.add_argument('--max-endpoints', type=int, default=500, help='Maximum endpoints to fuzz per device (default: 500)')
    auto_profile_parser.add_argument('--threads', type=int, default=50, help='Number of concurrent fuzzing threads (default: 50)')
    
    # SCPD analysis commands (ADR-015)
    scpd_parser = subparsers.add_parser('scpd-analyze', help='Comprehensive SCPD analysis and action discovery')
    scpd_parser.add_argument('--save-report', help='Save detailed analysis report to file')
    scpd_parser.add_argument('--minimal', action='store_true', help='Show minimal output')
    
    mass_scpd_parser = subparsers.add_parser('mass-scpd-analyze', help='Mass SCPD analysis across all devices')
    mass_scpd_parser.add_argument('--save-report', help='Save detailed mass analysis report to file')
    mass_scpd_parser.add_argument('--minimal', action='store_true', help='Show minimal output')
    
    # Interactive SOAP action control command
    interactive_parser = subparsers.add_parser('interactive', help='Interactive SOAP action controller')
    interactive_parser.add_argument('--device', help='Specific device to control (if multiple found)')
    
    # Tutorial command for new users
    tutorial_parser = subparsers.add_parser('tutorial', help='Interactive tutorials for new users')
    tutorial_parser.add_argument('--type', choices=['basic', 'security', 'media'], default='basic',
                                help='Tutorial type (default: basic)')
    
    # Main menu command for guided navigation
    menu_parser = subparsers.add_parser('menu', help='Interactive main menu')
    
    # Enhanced Profile Generation Commands
    enhanced_profile_parser = subparsers.add_parser('enhanced-profile', help='Enhanced profile generation with complete SCPD analysis')
    enhanced_profile_subparsers = enhanced_profile_parser.add_subparsers(dest='profile_command', help='Enhanced profile operations')
    
    # Single device enhanced profile
    single_profile_parser = enhanced_profile_subparsers.add_parser('single', help='Generate enhanced profile for single device')
    single_profile_parser.add_argument('--save-profile', nargs='?', const=True, help='Save profile to file')
    single_profile_parser.add_argument('--minimal', action='store_true', help='Show minimal output')
    
    # Mass enhanced profile generation
    mass_profile_parser = enhanced_profile_subparsers.add_parser('mass', help='Generate enhanced profiles for all devices')
    mass_profile_parser.add_argument('--save-profiles', nargs='?', const=True, help='Save profiles to directory')
    mass_profile_parser.add_argument('--individual-files', action='store_true', help='Save individual profile files')
    mass_profile_parser.add_argument('--minimal', action='store_true', help='Show minimal output')
    
    # Profile-based Interactive Controller
    profile_interactive_parser = subparsers.add_parser('profile-interactive', help='Enhanced interactive control using profiles')
    
    # Profile-aware Routines
    profile_routine_parser = subparsers.add_parser('profile-routine', help='Execute profile-aware routines')
    profile_routine_parser.add_argument('routine', nargs='?', help='Routine name to execute')
    profile_routine_parser.add_argument('--list-routines', action='store_true', help='List available routines')
    profile_routine_parser.add_argument('--uri', help='Media URI (for media_playback routine)')
    profile_routine_parser.add_argument('--volume', type=int, help='Volume level (for volume_control routine)')
    profile_routine_parser.add_argument('--fade-duration', type=float, help='Fade duration in seconds')
    
    # API Generation
    generate_api_parser = subparsers.add_parser('generate-api', help='Generate REST API from enhanced profiles')
    generate_api_parser.add_argument('profile_file', help='Enhanced profile JSON file')
    generate_api_parser.add_argument('--output-dir', help='Output directory for generated API')
    
    # Cache management commands
    clear_cache_parser = subparsers.add_parser('clear-cache', help='Clear device cache')
    
    # HTTP server commands
    start_server_parser = subparsers.add_parser('start-server', help='Start HTTP server')
    start_server_parser.add_argument('--server-port', type=int, default=8080, help='Server port (default: 8080)')
    
    stop_server_parser = subparsers.add_parser('stop-server', help='Stop HTTP server')
    stop_server_parser.add_argument('--server-port', type=int, default=8080, help='Server port (default: 8080)')
    
    return parser


async def main():
    """Main entry point for the CLI."""
    parser = create_parser()
    args = parser.parse_args()
    
    # Configure logging
    logging_utils.setup_logging(verbose=args.verbose)
    
    # Handle no command
    if not args.command:
        parser.print_help()
        sys.exit(0)
    
    # Configure stealth mode
    if args.stealth:
        config.STEALTH_MODE = True
        ColoredOutput.info("Stealth mode enabled")
    
    # Command dispatch
    commands = {
        'discover': cmd_discover,
        'info': cmd_info,
        'services': cmd_services,
        'play': cmd_play,
        'pause': cmd_pause,
        'stop': cmd_stop,
        'next': cmd_next,
        'previous': cmd_previous,
        'get-volume': cmd_get_volume,
        'set-volume': cmd_set_volume,
        'get-mute': cmd_get_mute,
        'set-mute': cmd_set_mute,
        'ssl-scan': cmd_ssl_scan,
        'rtsp-scan': cmd_rtsp_scan,
        'routine': cmd_routine,
        'list-routines': cmd_list_routines,
        'mass': cmd_mass_discover,
        'mass-scan': cmd_mass_scan_services,
        'auto-profile': cmd_auto_profile,
        'scpd-analyze': cmd_scpd_analyze,
        'mass-scpd-analyze': cmd_mass_scpd_analyze,
        'interactive': cmd_interactive_control,
        'tutorial': cmd_tutorial,
        'menu': cmd_menu,
        'clear-cache': cmd_clear_cache,
        'start-server': cmd_start_server,
        'stop-server': cmd_stop_server,
        'profile-interactive': cmd_profile_interactive,
        'profile-routine': cmd_profile_routine,
        'generate-api': cmd_generate_api,
    }
    
    try:
        # Handle enhanced-profile subcommands
        if args.command == 'enhanced-profile':
            if args.profile_command == 'single':
                result = await cmd_enhanced_profile_single(args)
            elif args.profile_command == 'mass':
                result = await cmd_enhanced_profile_mass(args)
            else:
                ColoredOutput.error("Enhanced profile command requires subcommand (single|mass)")
                sys.exit(1)
        else:
            command_func = commands.get(args.command)
            if command_func:
                result = await command_func(args)
            else:
                ColoredOutput.error(f"Unknown command: {args.command}")
                parser.print_help()
                sys.exit(1)
        
        # Exit with appropriate code
        if result.get('status') == 'error':
            sys.exit(1)
        elif result.get('status') == 'warning':
            sys.exit(2)
            
    except KeyboardInterrupt:
        ColoredOutput.warning("\nOperation cancelled by user")
        sys.exit(130)
    except Exception as e:
        ColoredOutput.error(f"Unexpected error: {e}")
        if args.verbose:
            logger.exception("Unexpected error details")
        sys.exit(1)


def main_entry():
    """Entry point for the CLI that handles async execution."""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(130)


if __name__ == '__main__':
    main_entry() 