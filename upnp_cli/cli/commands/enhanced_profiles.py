#!/usr/bin/env python3
"""
Enhanced Profile Generation Commands

Command implementations for generating device profiles with comprehensive
SCPD action inventories, argument specifications, and state variable constraints.
"""

import json
import logging
from typing import List, Dict, Any
from pathlib import Path

import upnp_cli.discovery as discovery
import upnp_cli.utils as utils
from upnp_cli.cli.output import ColoredOutput
from upnp_cli.cli.utils import auto_discover_target
from upnp_cli.profile_generation.enhanced_profile_generator import (
    generate_enhanced_profile_with_scpd,
    generate_enhanced_profiles_for_devices,
    save_enhanced_profiles
)

logger = logging.getLogger(__name__)


async def cmd_enhanced_profile_single(args) -> Dict[str, Any]:
    """
    Generate enhanced profile for a single device with complete SCPD analysis.
    """
    try:
        # Auto-discover if no host specified
        if not args.host:
            devices = await auto_discover_target(args)
            if not devices:
                return {"status": "error", "message": "No devices found for enhanced profile generation"}
            device = devices[0]
            args.host = device['ip']
            args.port = device.get('port', args.port)
        
        ColoredOutput.header(f"🧠 Enhanced Profile Generation: {args.host}:{args.port}")
        
        # Get device description
        device_url = f"http://{args.host}:{args.port}/xml/device_description.xml"
        
        import aiohttp
        async with aiohttp.ClientSession() as session:
            device_info = await discovery.fetch_device_description(session, device_url)
        
        if not device_info:
            return {"status": "error", "message": "Could not fetch device description"}
        
        device_name = device_info.get('friendlyName', f"{args.host}:{args.port}")
        ColoredOutput.info(f"Device: {device_name}")
        
        # Generate enhanced profile
        base_url = f"http://{args.host}:{args.port}"
        profile = await generate_enhanced_profile_with_scpd(device_info, base_url)
        
        if not profile:
            return {"status": "error", "message": "Failed to generate enhanced profile"}
        
        # Output results
        if args.json:
            print(json.dumps(profile, indent=2))
        else:
            _print_enhanced_profile_summary(profile, args)
        
        # Save profile if requested
        if args.save_profile:
            output_dir = Path(args.save_profile) if args.save_profile != True else Path("enhanced_profiles")
            saved_file = await save_enhanced_profiles({"profiles": [profile]}, output_dir, individual_files=True)
            ColoredOutput.success(f"Enhanced profile saved to: {saved_file}")
        
        return {"status": "success", "profile": profile}
        
    except Exception as e:
        ColoredOutput.error(f"Enhanced profile generation failed: {e}")
        if args.verbose:
            logger.exception("Enhanced profile generation error details")
        return {"status": "error", "message": str(e)}


async def cmd_enhanced_profile_mass(args) -> Dict[str, Any]:
    """
    Generate enhanced profiles for all devices on the network.
    """
    try:
        ColoredOutput.header("🚀 Mass Enhanced Profile Generation")
        
        # Discover all devices
        network = args.network or utils.get_en0_network()[1]
        ColoredOutput.info(f"Scanning network: {network}")
        
        devices = await discovery.scan_network_async(
            network,
            use_cache=bool(args.cache)
        )
        
        if not devices:
            ColoredOutput.warning("No devices found for enhanced profile generation")
            return {"status": "warning", "message": "No devices found"}
        
        ColoredOutput.success(f"Discovered {len(devices)} devices for enhanced profile generation")
        
        # Generate enhanced profiles
        enhanced_profiles = await generate_enhanced_profiles_for_devices(devices)
        
        # Output results
        if args.json:
            print(json.dumps(enhanced_profiles, indent=2))
        else:
            _print_enhanced_profiles_summary(enhanced_profiles, args)
        
        # Save profiles if requested
        if args.save_profiles:
            output_dir = Path(args.save_profiles) if args.save_profiles != True else Path("enhanced_profiles")
            saved_file = await save_enhanced_profiles(enhanced_profiles, output_dir, individual_files=args.individual_files)
        
        return {"status": "success", "profiles": enhanced_profiles}
        
    except Exception as e:
        ColoredOutput.error(f"Mass enhanced profile generation failed: {e}")
        if args.verbose:
            logger.exception("Mass enhanced profile generation error details")
        return {"status": "error", "message": str(e)}


def _print_enhanced_profile_summary(profile: Dict[str, Any], args):
    """Print enhanced profile summary."""
    ColoredOutput.header(f"Enhanced Profile: {profile['name']}")
    
    # Basic info
    ColoredOutput.print(f"Generated: {profile['metadata']['generated_at']}", 'white')
    
    # SCPD Analysis summary
    scpd_analysis = profile['metadata']['scpd_analysis']
    ColoredOutput.print(f"\n📊 SCPD ANALYSIS", 'cyan', bold=True)
    ColoredOutput.print("=" * 50, 'cyan')
    ColoredOutput.print(f"Services Analyzed: {scpd_analysis['services_analyzed']}", 'white')
    ColoredOutput.print(f"Successful Parses: {scpd_analysis['successful_parses']}", 'green')
    ColoredOutput.print(f"Total Actions: {scpd_analysis['total_actions']}", 'green', bold=True)
    
    if scpd_analysis['parsing_errors']:
        ColoredOutput.print(f"Parsing Errors: {len(scpd_analysis['parsing_errors'])}", 'red')
    
    # Capabilities breakdown
    capabilities = profile.get('capabilities', {})
    ColoredOutput.print(f"\n🎯 CAPABILITIES", 'yellow', bold=True)
    ColoredOutput.print("=" * 50, 'yellow')
    ColoredOutput.print(f"🎵 Media Control: {capabilities.get('media_control_actions', 0)} actions", 'white')
    ColoredOutput.print(f"🔊 Volume Control: {capabilities.get('volume_control_actions', 0)} actions", 'white')
    ColoredOutput.print(f"ℹ️  Information: {capabilities.get('information_actions', 0)} actions", 'white')
    ColoredOutput.print(f"⚙️  Configuration: {capabilities.get('configuration_actions', 0)} actions", 'white')
    ColoredOutput.print(f"🔒 Security: {capabilities.get('security_actions', 0)} actions", 'white')
    
    # Services detail
    if not args.minimal:
        ColoredOutput.print(f"\n🔧 SERVICES", 'magenta', bold=True)
        ColoredOutput.print("=" * 50, 'magenta')
        
        services = profile['upnp']['services']
        for service_name, service_info in services.items():
            ColoredOutput.print(f"\n📋 {service_name.title()}", 'white', bold=True)
            ColoredOutput.print(f"   Type: {service_info['serviceType']}", 'gray')
            ColoredOutput.print(f"   Actions: {service_info['action_count']}", 'cyan')
            ColoredOutput.print(f"   Control URL: {service_info['controlURL']}", 'gray')
    
    # Action examples
    if args.verbose and not args.minimal:
        action_inventory = profile['upnp']['action_inventory']
        if action_inventory:
            ColoredOutput.print(f"\n🎬 ACTION EXAMPLES", 'green', bold=True)
            ColoredOutput.print("=" * 50, 'green')
            
            action_count = 0
            for service_name, actions in action_inventory.items():
                if action_count >= 10:  # Limit examples
                    break
                
                ColoredOutput.print(f"\n🔧 {service_name.title()} Service:", 'cyan', bold=True)
                
                for action_name, action_info in list(actions.items())[:3]:  # First 3 actions per service
                    if action_count >= 10:
                        break
                    
                    complexity = action_info.get('complexity', '🟢 Easy')
                    category = action_info.get('category', 'other')
                    args_in = len(action_info.get('arguments_in', []))
                    args_out = len(action_info.get('arguments_out', []))
                    
                    ColoredOutput.print(f"  • {action_name} {complexity}", 'white')
                    ColoredOutput.print(f"    Category: {category} | Args: {args_in} in, {args_out} out", 'gray')
                    
                    action_count += 1


def _print_enhanced_profiles_summary(enhanced_profiles: Dict[str, Any], args):
    """Print mass enhanced profiles summary."""
    metadata = enhanced_profiles['metadata']
    analysis = enhanced_profiles['analysis_summary']
    
    ColoredOutput.header(f"Mass Enhanced Profile Generation Results")
    
    # Generation summary
    ColoredOutput.print(f"\n📊 GENERATION SUMMARY", 'cyan', bold=True)
    ColoredOutput.print("=" * 60, 'cyan')
    ColoredOutput.print(f"Devices Analyzed: {metadata['total_devices']}", 'white')
    ColoredOutput.print(f"Profiles Generated: {metadata['profiles_generated']}", 'green', bold=True)
    ColoredOutput.print(f"Generated At: {metadata['generated_at']}", 'white')
    
    # Analysis summary
    ColoredOutput.print(f"\n🔍 ANALYSIS SUMMARY", 'yellow', bold=True)
    ColoredOutput.print("=" * 60, 'yellow')
    ColoredOutput.print(f"Total Services: {analysis['total_services']}", 'white')
    ColoredOutput.print(f"Total Actions: {analysis['total_actions']}", 'green', bold=True)
    ColoredOutput.print(f"State Variables: {analysis['total_state_variables']}", 'white')
    
    if analysis['parsing_errors']:
        ColoredOutput.print(f"Parsing Errors: {len(analysis['parsing_errors'])}", 'red')
    
    # Individual profiles
    if enhanced_profiles['profiles'] and not args.minimal:
        ColoredOutput.print(f"\n📋 GENERATED PROFILES", 'magenta', bold=True)
        ColoredOutput.print("=" * 60, 'magenta')
        
        for profile in enhanced_profiles['profiles']:
            capabilities = profile.get('capabilities', {})
            total_actions = capabilities.get('total_actions', 0)
            
            ColoredOutput.print(f"\n🎯 {profile['name']}", 'white', bold=True)
            ColoredOutput.print(f"   Total Actions: {total_actions}", 'green')
            ColoredOutput.print(f"   Media Control: {capabilities.get('media_control_actions', 0)}", 'cyan')
            ColoredOutput.print(f"   Volume Control: {capabilities.get('volume_control_actions', 0)}", 'cyan')
            ColoredOutput.print(f"   Information: {capabilities.get('information_actions', 0)}", 'cyan')
    
    # Recommendations
    recommendations = []
    
    if metadata['profiles_generated'] > 0:
        avg_actions = analysis['total_actions'] / metadata['profiles_generated']
        recommendations.append(f"✅ Generated comprehensive profiles with avg {avg_actions:.1f} actions per device")
    
    if analysis['total_actions'] > 100:
        recommendations.append(f"🎯 Rich network with {analysis['total_actions']} total control actions available")
    
    if len(analysis['parsing_errors']) > 0:
        error_rate = len(analysis['parsing_errors']) / analysis['total_services'] * 100
        if error_rate > 20:
            recommendations.append(f"⚠️ High SCPD parsing error rate ({error_rate:.1f}%) - some devices may have incomplete profiles")
    
    if recommendations:
        ColoredOutput.print(f"\n💡 RECOMMENDATIONS", 'green', bold=True)
        ColoredOutput.print("=" * 60, 'green')
        
        for i, rec in enumerate(recommendations, 1):
            ColoredOutput.print(f"{i}. {rec}", 'white') 