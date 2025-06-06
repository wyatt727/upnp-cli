#!/usr/bin/env python3
"""
Cache and Server Management Commands Module

This module contains cache management and HTTP server related CLI commands.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any

import upnp_cli.cache as cache
import upnp_cli.http_server as http_server
from upnp_cli.cli.output import ColoredOutput

logger = logging.getLogger(__name__)


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