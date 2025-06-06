#!/usr/bin/env python3
"""
SCPD Analysis Commands

Command implementations for comprehensive SOAP action discovery from SCPD files.
Implements ADR-015: Comprehensive SOAP Action Discovery from SCPD Files.
"""

import json
import logging
import time
from typing import List, Dict, Any
from pathlib import Path

# Import enhanced SCPD parser - fix import mess
import sys
from pathlib import Path

# Ensure we can import from the upnp_cli package
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from upnp_cli.profile_generation.scpd_parser import (
    parse_device_scpds,
    generate_comprehensive_action_inventory
)
import upnp_cli.discovery as discovery
import upnp_cli.cache as cache
import upnp_cli.utils as utils
from upnp_cli.cli.output import ColoredOutput, ProgressReporter
from upnp_cli.cli.commands.discovery import get_device_description
from upnp_cli.cli.utils import auto_discover_target

logger = logging.getLogger(__name__)


async def cmd_scpd_analyze(args) -> Dict[str, Any]:
    """
    Comprehensive SCPD analysis and action discovery.
    
    This command demonstrates ADR-015 by parsing all SCPD files for a device
    and extracting the complete action inventory with full argument specifications.
    """
    try:
        # Auto-discover if no host specified
        if not args.host:
            devices = await auto_discover_target(args)
            if not devices:
                return {"status": "error", "message": "No devices found for SCPD analysis"}
            device = devices[0]
            args.host = device['ip']
            args.port = device.get('port', args.port)
        
        ColoredOutput.header(f"Comprehensive SCPD Analysis: {args.host}:{args.port}")
        
        # Get device description first
        url = f"http://{args.host}:{args.port}/xml/device_description.xml"
        device_info = await get_device_description(url)
        
        if not device_info:
            return {"status": "error", "message": "Could not fetch device description"}
        
        device_name = device_info.get('friendlyName', f"{args.host}:{args.port}")
        services = device_info.get('services', [])
        
        if not services:
            ColoredOutput.warning("No services found in device description")
            return {"status": "warning", "message": "No services found"}
        
        ColoredOutput.info(f"Device: {device_name}")
        ColoredOutput.info(f"Found {len(services)} services to analyze")
        
        # Parse all SCPD files
        base_url = f"http://{args.host}:{args.port}"
        
        if not args.json:
            ColoredOutput.info("🔍 Parsing SCPD files for comprehensive action discovery...")
        
        scpd_documents = await parse_device_scpds(device_info, base_url, timeout=args.timeout)
        
        # Generate analysis results
        analysis_results = _generate_scpd_analysis(device_info, scpd_documents, args)
        
        # Output results
        if args.json:
            print(json.dumps(analysis_results, indent=2))
        else:
            _print_scpd_analysis(analysis_results, args)
        
        # Save detailed report if requested
        if args.save_report:
            await _save_scpd_report(analysis_results, args)
        
        return {"status": "success", "analysis": analysis_results}
        
    except Exception as e:
        ColoredOutput.error(f"SCPD analysis failed: {e}")
        if args.verbose:
            logger.exception("SCPD analysis error details")
        return {"status": "error", "message": str(e)}


async def cmd_mass_scpd_analyze(args) -> Dict[str, Any]:
    """
    Mass SCPD analysis across multiple devices.
    
    Demonstrates comprehensive action discovery across an entire network.
    """
    try:
        ColoredOutput.header("🔍 Mass SCPD Analysis & Action Inventory Generation")
        
        # Discover all devices
        network = args.network or utils.get_en0_network()[1]
        ColoredOutput.info(f"Scanning network: {network}")
        
        devices = await discovery.scan_network_async(
            network,
            use_cache=bool(args.cache)
        )
        
        if not devices:
            ColoredOutput.warning("No devices found for mass SCPD analysis")
            return {"status": "warning", "message": "No devices found"}
        
        ColoredOutput.success(f"Discovered {len(devices)} devices for SCPD analysis")
        
        # Generate comprehensive action inventory
        ColoredOutput.info("📋 Generating comprehensive action inventory...")
        inventory = await generate_comprehensive_action_inventory(devices)
        
        # Output results
        if args.json:
            print(json.dumps(inventory, indent=2))
        else:
            _print_mass_scpd_analysis(inventory, args)
        
        # Save detailed report if requested
        if args.save_report:
            await _save_mass_scpd_report(inventory, args)
        
        return {"status": "success", "inventory": inventory}
        
    except Exception as e:
        ColoredOutput.error(f"Mass SCPD analysis failed: {e}")
        if args.verbose:
            logger.exception("Mass SCPD analysis error details")
        return {"status": "error", "message": str(e)}


def _generate_scpd_analysis(device_info: Dict[str, Any], scpd_documents: List, args) -> Dict[str, Any]:
    """Generate comprehensive SCPD analysis results."""
    analysis = {
        "device_info": {
            "friendly_name": device_info.get('friendlyName', 'Unknown'),
            "manufacturer": device_info.get('manufacturer', 'Unknown'),
            "model": device_info.get('modelName', 'Unknown'),
            "ip": device_info.get('ip', 'Unknown'),
            "port": device_info.get('port', 'Unknown')
        },
        "scpd_analysis": {
            "services_found": len(device_info.get('services', [])),
            "scpds_parsed": len(scpd_documents),
            "parsing_success_rate": 0.0,
            "total_actions_discovered": 0,
            "unique_actions": set(),
            "services": []
        },
        "action_inventory": {},
        "argument_analysis": {},
        "recommendations": []
    }
    
    successful_parses = 0
    
    for document in scpd_documents:
        service_analysis = {
            "service_type": document.service_type,
            "scpd_url": document.scpd_url,
            "parsing_success": document.parsing_success,
            "parsing_errors": document.parsing_errors,
            "action_count": document.get_action_count(),
            "actions": {},
            "state_variables": len(document.state_variables)
        }
        
        if document.parsing_success:
            successful_parses += 1
            
            # Extract action details
            for action_name, action in document.actions.items():
                action_dict = action.to_dict()
                service_analysis["actions"][action_name] = action_dict
                
                # Update global statistics
                analysis["scpd_analysis"]["total_actions_discovered"] += 1
                analysis["scpd_analysis"]["unique_actions"].add(action_name)
                
                # Analyze arguments
                total_args = len(action.arguments_in) + len(action.arguments_out)
                if action_name not in analysis["argument_analysis"]:
                    analysis["argument_analysis"][action_name] = {
                        "occurrences": 0,
                        "max_args_in": 0,
                        "max_args_out": 0,
                        "services": []
                    }
                
                arg_analysis = analysis["argument_analysis"][action_name]
                arg_analysis["occurrences"] += 1
                arg_analysis["max_args_in"] = max(arg_analysis["max_args_in"], len(action.arguments_in))
                arg_analysis["max_args_out"] = max(arg_analysis["max_args_out"], len(action.arguments_out))
                arg_analysis["services"].append(document.service_type)
        
        analysis["scpd_analysis"]["services"].append(service_analysis)
    
    # Calculate success rate
    if scpd_documents:
        analysis["scpd_analysis"]["parsing_success_rate"] = successful_parses / len(scpd_documents)
    
    # Convert set to list for JSON serialization
    analysis["scpd_analysis"]["unique_actions"] = list(analysis["scpd_analysis"]["unique_actions"])
    
    # Generate recommendations
    recommendations = []
    
    if analysis["scpd_analysis"]["parsing_success_rate"] >= 0.9:
        recommendations.append("✅ Excellent SCPD parsing success rate - comprehensive action discovery achieved")
    elif analysis["scpd_analysis"]["parsing_success_rate"] >= 0.7:
        recommendations.append("⚠️ Good SCPD parsing rate - some services may have incomplete action discovery")
    else:
        recommendations.append("❌ Low SCPD parsing success rate - action discovery may be incomplete")
    
    if analysis["scpd_analysis"]["total_actions_discovered"] > 20:
        recommendations.append(f"🎯 Rich device interface: {analysis['scpd_analysis']['total_actions_discovered']} actions available for control/testing")
    elif analysis["scpd_analysis"]["total_actions_discovered"] > 10:
        recommendations.append(f"📋 Moderate device interface: {analysis['scpd_analysis']['total_actions_discovered']} actions available")
    else:
        recommendations.append(f"📋 Basic device interface: {analysis['scpd_analysis']['total_actions_discovered']} actions available")
    
    # Security recommendations
    high_value_actions = ["Play", "Pause", "Stop", "SetVolume", "SetMute", "SetAVTransportURI"]
    found_control_actions = [action for action in analysis["scpd_analysis"]["unique_actions"] if action in high_value_actions]
    
    if found_control_actions:
        recommendations.append(f"🔥 High-value control actions available: {', '.join(found_control_actions)}")
    
    analysis["recommendations"] = recommendations
    
    return analysis


def _print_scpd_analysis(analysis: Dict[str, Any], args):
    """Print comprehensive SCPD analysis results."""
    device_info = analysis["device_info"]
    scpd_analysis = analysis["scpd_analysis"]
    
    ColoredOutput.header(f"SCPD Analysis Results: {device_info['friendly_name']}")
    
    # Device summary
    ColoredOutput.print(f"Device: {device_info['manufacturer']} {device_info['model']}", 'white')
    ColoredOutput.print(f"Location: {device_info['ip']}:{device_info['port']}", 'white')
    
    # Parsing summary
    ColoredOutput.print(f"\n📊 PARSING SUMMARY", 'cyan', bold=True)
    ColoredOutput.print("=" * 50, 'cyan')
    ColoredOutput.print(f"Services Found: {scpd_analysis['services_found']}", 'white')
    ColoredOutput.print(f"SCPDs Parsed: {scpd_analysis['scpds_parsed']}", 'white')
    ColoredOutput.print(f"Success Rate: {scpd_analysis['parsing_success_rate']:.1%}", 'green' if scpd_analysis['parsing_success_rate'] >= 0.8 else 'yellow')
    ColoredOutput.print(f"Total Actions: {scpd_analysis['total_actions_discovered']}", 'green', bold=True)
    ColoredOutput.print(f"Unique Actions: {len(scpd_analysis['unique_actions'])}", 'white')
    
    # Action inventory
    if scpd_analysis['unique_actions'] and not args.minimal:
        ColoredOutput.print(f"\n🎯 ACTION INVENTORY", 'yellow', bold=True)
        ColoredOutput.print("=" * 50, 'yellow')
        
        # Group actions by common types
        media_actions = []
        volume_actions = []
        info_actions = []
        other_actions = []
        
        for action in sorted(scpd_analysis['unique_actions']):
            if any(keyword in action for keyword in ['Play', 'Pause', 'Stop', 'Next', 'Previous', 'Seek']):
                media_actions.append(action)
            elif any(keyword in action for keyword in ['Volume', 'Mute', 'Bass', 'Treble']):
                volume_actions.append(action)
            elif any(keyword in action for keyword in ['Get', 'Info', 'Status', 'Current']):
                info_actions.append(action)
            else:
                other_actions.append(action)
        
        if media_actions:
            ColoredOutput.print("🎵 Media Control:", 'green', bold=True)
            for action in media_actions:
                ColoredOutput.print(f"  • {action}", 'white')
        
        if volume_actions:
            ColoredOutput.print("🔊 Audio Control:", 'cyan', bold=True)
            for action in volume_actions:
                ColoredOutput.print(f"  • {action}", 'white')
        
        if info_actions:
            ColoredOutput.print("ℹ️ Information:", 'blue', bold=True)
            for action in info_actions[:10]:  # Limit to first 10
                ColoredOutput.print(f"  • {action}", 'white')
            if len(info_actions) > 10:
                ColoredOutput.print(f"  ... and {len(info_actions) - 10} more", 'gray')
        
        if other_actions:
            ColoredOutput.print("🔧 Other Actions:", 'yellow', bold=True)
            for action in other_actions[:10]:  # Limit to first 10
                ColoredOutput.print(f"  • {action}", 'white')
            if len(other_actions) > 10:
                ColoredOutput.print(f"  ... and {len(other_actions) - 10} more", 'gray')
    
    # Service details (verbose mode)
    if args.verbose and not args.minimal:
        ColoredOutput.print(f"\n📋 SERVICE DETAILS", 'magenta', bold=True)
        ColoredOutput.print("=" * 50, 'magenta')
        
        for service in scpd_analysis['services']:
            status_icon = "✅" if service['parsing_success'] else "❌"
            ColoredOutput.print(f"\n{status_icon} {service['service_type']}", 'white', bold=True)
            ColoredOutput.print(f"   Actions: {service['action_count']}", 'cyan')
            ColoredOutput.print(f"   State Variables: {service['state_variables']}", 'white')
            ColoredOutput.print(f"   SCPD URL: {service['scpd_url']}", 'gray')
            
            if service['parsing_errors']:
                ColoredOutput.print(f"   Errors: {', '.join(service['parsing_errors'])}", 'red')
    
    # Recommendations
    recommendations = analysis.get("recommendations", [])
    if recommendations:
        ColoredOutput.print(f"\n💡 RECOMMENDATIONS", 'green', bold=True)
        ColoredOutput.print("=" * 50, 'green')
        
        for i, rec in enumerate(recommendations, 1):
            ColoredOutput.print(f"{i}. {rec}", 'white')


def _print_mass_scpd_analysis(inventory: Dict[str, Any], args):
    """Print mass SCPD analysis results."""
    ColoredOutput.header(f"Mass SCPD Analysis Results ({inventory['total_devices']} devices)")
    
    # Overall statistics
    ColoredOutput.print(f"\n📊 OVERALL STATISTICS", 'cyan', bold=True)
    ColoredOutput.print("=" * 60, 'cyan')
    ColoredOutput.print(f"Devices Analyzed: {inventory['devices_parsed']}/{inventory['total_devices']}", 'white')
    ColoredOutput.print(f"Services Parsed: {inventory['total_services']}", 'white')
    ColoredOutput.print(f"Total Actions: {inventory['total_actions']}", 'green', bold=True)
    ColoredOutput.print(f"Unique Actions: {len(inventory['unique_actions'])}", 'white')
    
    if inventory['parsing_errors']:
        ColoredOutput.print(f"Parsing Errors: {len(inventory['parsing_errors'])}", 'red')
    
    # Action statistics
    if inventory['action_statistics'] and not args.minimal:
        ColoredOutput.print(f"\n🎯 MOST COMMON ACTIONS", 'yellow', bold=True)
        ColoredOutput.print("=" * 60, 'yellow')
        
        # Show top 15 most common actions
        top_actions = list(inventory['action_statistics'].items())[:15]
        for action, count in top_actions:
            percentage = (count / inventory['devices_parsed']) * 100 if inventory['devices_parsed'] > 0 else 0
            ColoredOutput.print(f"  • {action:<30} {count:>3} devices ({percentage:>5.1f}%)", 'white')
    
    # Device summaries
    if args.verbose and not args.minimal:
        ColoredOutput.print(f"\n📋 DEVICE SUMMARIES", 'magenta', bold=True)
        ColoredOutput.print("=" * 60, 'magenta')
        
        for device_inv in inventory['device_inventories']:
            ColoredOutput.print(f"\n🔍 {device_inv['device_name']}", 'white', bold=True)
            ColoredOutput.print(f"   Services: {device_inv['services_parsed']}", 'cyan')
            ColoredOutput.print(f"   Actions: {device_inv['total_actions']}", 'white')
            
            if device_inv['total_actions'] > 0:
                # Show a few example actions
                all_actions = []
                for service in device_inv['services']:
                    all_actions.extend(service['actions'])
                
                if all_actions:
                    sample_actions = sorted(set(all_actions))[:5]
                    ColoredOutput.print(f"   Examples: {', '.join(sample_actions)}", 'gray')


async def _save_scpd_report(analysis: Dict[str, Any], args):
    """Save detailed SCPD analysis report."""
    try:
        save_path = Path(args.save_report)
        
        if save_path.is_dir() or not save_path.suffix:
            save_dir = save_path
            save_dir.mkdir(parents=True, exist_ok=True)
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            device_name = analysis["device_info"]["friendly_name"].replace(" ", "_")
            save_file = save_dir / f"scpd_analysis_{device_name}_{timestamp}.json"
        else:
            save_file = save_path
            save_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(save_file, 'w') as f:
            json.dump(analysis, f, indent=2)
        
        ColoredOutput.success(f"SCPD analysis report saved to: {save_file}")
        
    except Exception as e:
        ColoredOutput.error(f"Failed to save SCPD report: {e}")


async def _save_mass_scpd_report(inventory: Dict[str, Any], args):
    """Save detailed mass SCPD analysis report."""
    try:
        save_path = Path(args.save_report)
        
        if save_path.is_dir() or not save_path.suffix:
            save_dir = save_path
            save_dir.mkdir(parents=True, exist_ok=True)
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            save_file = save_dir / f"mass_scpd_analysis_{timestamp}.json"
        else:
            save_file = save_path
            save_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(save_file, 'w') as f:
            json.dump(inventory, f, indent=2)
        
        ColoredOutput.success(f"Mass SCPD analysis report saved to: {save_file}")
        
    except Exception as e:
        ColoredOutput.error(f"Failed to save mass SCPD report: {e}") 