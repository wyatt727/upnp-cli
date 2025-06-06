#!/usr/bin/env python3
"""
CLI Utilities Module

This module contains shared utility functions used across CLI command modules.
"""

import logging
from pathlib import Path
from typing import List, Dict, Any

import upnp_cli.cache as cache
import upnp_cli.discovery as discovery
import upnp_cli.soap_client as soap_client
from upnp_cli.cli.output import ColoredOutput

logger = logging.getLogger(__name__)


async def auto_discover_target(args) -> List[Dict[str, Any]]:
    """Auto-discover a target device if no host is specified."""
    ColoredOutput.info("No host specified, auto-discovering devices...")
    
    cache_manager = cache.DeviceCache(Path(args.cache)) if hasattr(args, 'cache') and args.cache else None
    
    # Try cache first
    if cache_manager:
        cached_entries = cache_manager.list()
        if cached_entries:
            cached_devices = [entry['info'] for entry in cached_entries]
            ColoredOutput.info(f"Using cached device: {cached_devices[0].get('friendlyName', 'Unknown')}")
            return cached_devices[:1]  # Return first cached device
    
    # Perform quick SSDP discovery
    ssdp_responses = await discovery.discover_ssdp_devices(timeout=5)
    if not ssdp_responses:
        return []
    
    # Get device descriptions from SSDP responses
    import aiohttp
    async with aiohttp.ClientSession() as session:
        for response in ssdp_responses:
            location = response.get('location')
            if location:
                device_info = await discovery.fetch_device_description(session, location)
                if device_info:
                    ColoredOutput.info(f"Auto-discovered device: {device_info.get('friendlyName', 'Unknown')}")
                    return [device_info]  # Return first working device
    
    # Fallback: try to construct device info from SSDP response
    if ssdp_responses:
        response = ssdp_responses[0]
        device_info = {
            'ip': response.get('addr', 'Unknown'),
            'port': 1400,  # Default UPnP port
            'friendlyName': 'Unknown Device',
            'location_url': response.get('location', '')
        }
        ColoredOutput.info(f"Auto-discovered device: {device_info['ip']}")
        return [device_info]
    
    return []


def parse_soap_response(response, verbose: bool = False) -> Dict[str, Any]:
    """
    Parse SOAP response using the global SOAP client.
    
    Args:
        response: HTTP response object
        verbose: Whether to include verbose information
        
    Returns:
        Parsed response dictionary
    """
    client = soap_client.get_soap_client()
    return client.parse_soap_response(response, verbose=verbose) 