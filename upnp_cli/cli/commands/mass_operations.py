#!/usr/bin/env python3
"""
Mass Operations Commands Module

This module contains mass operation CLI commands including mass discovery,
service scanning, and comprehensive auto-profile generation.
"""

import json
import time
import asyncio
import logging
from pathlib import Path
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor

import upnp_cli.discovery as discovery
import upnp_cli.utils as utils
import upnp_cli.profiles as profiles
from upnp_cli.cli.output import ColoredOutput, ProgressReporter

logger = logging.getLogger(__name__)


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
    try:
        from routines import list_available_routines, get_routine_manager
    except ImportError:
        ColoredOutput.error("Routines module not available")
        return {"status": "error", "message": "Routines module not available"}
    
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


def _print_device_table(devices: List[Dict[str, Any]]):
    """Print devices in a formatted table."""
    ColoredOutput.header(f"Discovered Devices ({len(devices)})")
    
    for i, device in enumerate(devices, 1):
        name = device.get('friendlyName', 'Unknown Device')
        ip = device.get('ip', 'Unknown')
        port = device.get('port', 'Unknown')
        manufacturer = device.get('manufacturer', 'Unknown')
        model = device.get('modelName', 'Unknown')
        
        ColoredOutput.print(f"{i:2d}. {name}", 'cyan', bold=True)
        ColoredOutput.print(f"    {ip}:{port} | {manufacturer} {model}", 'white')


# Import the mass service scanning functionality
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
            
            if device.get("protocol_info"):
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
    
    # Medium Priority Devices (if verbose and not minimal)
    medium_priority = analysis["medium_priority_devices"]
    if medium_priority and args.verbose and not getattr(args, 'minimal', False):
        ColoredOutput.print(f"\n⚡ MEDIUM PRIORITY TARGETS ({len(medium_priority)} devices)", 'yellow', bold=True)
        ColoredOutput.print("=" * 60, 'yellow')
        
        for device in medium_priority:
            info = device["device_info"]
            ColoredOutput.print(f"\n📡 {info['friendly_name']} ({info['ip']}:{info['port']})", 'white')
            if device["profile_match"]:
                ColoredOutput.print(f"   Profile: {device['profile_match']['name']}", 'green')
            ColoredOutput.print(f"   Priority Score: {device['priority_score']}", 'yellow')
    
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


# Auto-profile generation command is in auto_profile.py module 