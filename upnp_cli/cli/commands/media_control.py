#!/usr/bin/env python3
"""
Media Control Commands Module

This module contains all media control related CLI commands including
play, pause, stop, volume control, and mute functionality.
"""

import json
import logging
from typing import Dict, Any

# Import core modules with absolute imports
import upnp_cli.media_control as media_control
from upnp_cli.cli.output import ColoredOutput

logger = logging.getLogger(__name__)


async def cmd_play(args) -> Dict[str, Any]:
    """Start playback on a device."""
    return await _execute_media_command(args, media_control.play, "Play")


async def cmd_pause(args) -> Dict[str, Any]:
    """Pause playback on a device."""
    return await _execute_media_command(args, media_control.pause, "Pause")


async def cmd_stop(args) -> Dict[str, Any]:
    """Stop playback on a device."""
    return await _execute_media_command(args, media_control.stop, "Stop")


async def cmd_next(args) -> Dict[str, Any]:
    """Skip to next track."""
    return await _execute_media_command(args, media_control.next_track, "Next Track")


async def cmd_previous(args) -> Dict[str, Any]:
    """Skip to previous track."""
    return await _execute_media_command(args, media_control.previous_track, "Previous Track")


async def cmd_get_volume(args) -> Dict[str, Any]:
    """Get current volume level."""
    return await _execute_media_command(args, media_control.get_volume, "Get Volume")


async def cmd_set_volume(args) -> Dict[str, Any]:
    """Set volume level."""
    return await _execute_media_command(
        args, 
        lambda host, port, use_ssl: media_control.set_volume(host, port, args.level, use_ssl),
        f"Set Volume to {args.level}"
    )


async def cmd_get_mute(args) -> Dict[str, Any]:
    """Get mute status."""
    return await _execute_media_command(args, media_control.get_mute, "Get Mute")


async def cmd_set_mute(args) -> Dict[str, Any]:
    """Set mute status."""
    return await _execute_media_command(
        args,
        lambda host, port, use_ssl: media_control.set_mute(host, port, bool(args.mute), use_ssl),
        f"Set Mute to {bool(args.mute)}"
    )


async def _execute_media_command(args, command_func, description: str) -> Dict[str, Any]:
    """Execute a media control command with consistent error handling."""
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
        
        # Dry run mode
        if args.dry_run:
            ColoredOutput.info(f"DRY RUN: Would execute {description} on {args.host}:{args.port}")
            return {"status": "dry_run", "command": description, "target": f"{args.host}:{args.port}"}
        
        # Execute command
        ColoredOutput.info(f"Executing {description} on {args.host}:{args.port}")
        
        result = await command_func(args.host, args.port, args.use_ssl)
        
        # Handle both dict responses (from new media_control) and legacy response objects
        if isinstance(result, dict):
            # New async media control functions return dictionaries
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                ColoredOutput.success(f"{description} executed successfully")
                if args.verbose and 'response' in result:
                    ColoredOutput.print(str(result['response']), 'white')
                elif 'volume' in result:
                    ColoredOutput.print(f"Volume: {result['volume']}", 'cyan')
                elif 'muted' in result:
                    ColoredOutput.print(f"Muted: {result['muted']}", 'cyan')
            
            return result
        else:
            # Legacy response objects (for backward compatibility)
            from upnp_cli.cli.utils import parse_soap_response
            parsed_result = parse_soap_response(result, args.verbose)
            
            if args.json:
                print(json.dumps({"status": "success", "response": parsed_result}, indent=2))
            else:
                ColoredOutput.success(f"{description} executed successfully")
                if args.verbose:
                    ColoredOutput.print(str(parsed_result), 'white')
            
            return {"status": "success", "response": parsed_result}
        
    except Exception as e:
        ColoredOutput.error(f"{description} failed: {e}")
        if args.verbose:
            logger.exception(f"{description} error details")
        return {"status": "error", "message": str(e)} 