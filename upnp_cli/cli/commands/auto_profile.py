#!/usr/bin/env python3
"""
Auto-Profile Generation Commands Module

This module contains the comprehensive device fuzzing and automatic 
profile generation command. Due to its complexity, this acts as an
entry point that delegates to the main auto-profile implementation.
"""

import json
import logging
from typing import Dict, Any

from upnp_cli.cli.output import ColoredOutput

logger = logging.getLogger(__name__)


async def cmd_auto_profile(args) -> Dict[str, Any]:
    """
    Comprehensive device fuzzing and automatic profile generation.
    
    This command performs aggressive network scanning and fuzzing to
    automatically generate device profiles for penetration testing.
    """
    try:
        # Import the auto-profile functionality from the main CLI
        # This is a temporary arrangement until the full auto-profile 
        # implementation can be extracted to a separate module
        from upnp_cli.cli import _comprehensive_device_fuzzing, _generate_comprehensive_profiles, _print_comprehensive_profile_results, _save_comprehensive_profiles
        import upnp_cli.discovery as discovery
        import upnp_cli.utils as utils
        
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
        if args.aggressive:
            ColoredOutput.warning("⚠️  Aggressive mode enabled - this may be detected by security systems")
        
        fuzzed_devices = await _comprehensive_device_fuzzing(devices, args)
        
        # Generate profiles
        ColoredOutput.info("🧠 Generating intelligent device profiles...")
        generated_profiles = await _generate_comprehensive_profiles(fuzzed_devices, args)
        
        # Display results
        if args.json:
            print(json.dumps(generated_profiles, indent=2))
        else:
            _print_comprehensive_profile_results(generated_profiles, args)
        
        # Save profiles if requested
        if args.save_profiles and not args.preview:
            await _save_comprehensive_profiles(generated_profiles, args)
        elif args.preview:
            ColoredOutput.info("Preview mode - profiles not saved")
        
        return {"status": "success", "profiles": generated_profiles}
        
    except Exception as e:
        ColoredOutput.error(f"Auto-profile generation failed: {e}")
        if args.verbose:
            logger.exception("Auto-profile generation error details")
        return {"status": "error", "message": str(e)} 