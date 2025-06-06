#!/usr/bin/env python3
"""
Security Scanning Commands Module

This module contains security scanning related CLI commands including
SSL/TLS scanning and RTSP stream discovery.
"""

import json
import logging
from typing import Dict, Any

# Import core modules with absolute imports
import upnp_cli.ssl_rtsp_scan as ssl_rtsp_scan
from upnp_cli.cli.output import ColoredOutput

logger = logging.getLogger(__name__)


async def cmd_ssl_scan(args) -> Dict[str, Any]:
    """Perform SSL/TLS security scan on a device."""
    try:
        # Auto-discover if no host specified
        if not args.host:
            from upnp_cli.cli.utils import auto_discover_target
            devices = await auto_discover_target(args)
            if not devices:
                return {"status": "error", "message": "No devices found"}
            device = devices[0]
            args.host = device['ip']
        
        ColoredOutput.header(f"SSL/TLS Security Scan: {args.host}:{args.ssl_port}")
        
        # Dry run mode
        if args.dry_run:
            ColoredOutput.info(f"DRY RUN: Would scan SSL/TLS on {args.host}:{args.ssl_port}")
            return {"status": "dry_run", "scan": "SSL/TLS", "target": f"{args.host}:{args.ssl_port}"}
        
        # Perform SSL scan
        ssl_results = await ssl_rtsp_scan.scan_ssl_cert(args.host, args.ssl_port)
        
        if args.json:
            print(json.dumps(ssl_results, indent=2))
        else:
            _print_ssl_results(ssl_results)
        
        return {"status": "success", "ssl_results": ssl_results}
        
    except Exception as e:
        ColoredOutput.error(f"SSL scan failed: {e}")
        return {"status": "error", "message": str(e)}


async def cmd_rtsp_scan(args) -> Dict[str, Any]:
    """Perform RTSP stream discovery scan on a device."""
    try:
        # Auto-discover if no host specified
        if not args.host:
            from upnp_cli.cli.utils import auto_discover_target
            devices = await auto_discover_target(args)
            if not devices:
                return {"status": "error", "message": "No devices found"}
            device = devices[0]
            args.host = device['ip']
        
        ColoredOutput.header(f"RTSP Stream Discovery: {args.host}:{args.rtsp_port}")
        
        # Dry run mode
        if args.dry_run:
            ColoredOutput.info(f"DRY RUN: Would scan RTSP on {args.host}:{args.rtsp_port}")
            return {"status": "dry_run", "scan": "RTSP", "target": f"{args.host}:{args.rtsp_port}"}
        
        # Perform RTSP scan
        rtsp_results = await ssl_rtsp_scan.scan_rtsp_streams(args.host, args.rtsp_port)
        
        if args.json:
            print(json.dumps(rtsp_results, indent=2))
        else:
            _print_rtsp_results(rtsp_results)
        
        return {"status": "success", "rtsp_results": rtsp_results}
        
    except Exception as e:
        ColoredOutput.error(f"RTSP scan failed: {e}")
        return {"status": "error", "message": str(e)}


def _print_ssl_results(results: Dict[str, Any]):
    """Print SSL scan results in a formatted way."""
    ColoredOutput.success("SSL/TLS Scan Results")
    
    # Basic SSL info
    ssl_version = results.get('ssl_version', 'Unknown')
    cipher = results.get('cipher', [])
    
    ColoredOutput.print(f"SSL Version: {ssl_version}", 'cyan')
    if cipher:
        cipher_name = cipher[0] if len(cipher) > 0 else 'Unknown'
        cipher_bits = cipher[1] if len(cipher) > 1 else 'Unknown'
        ColoredOutput.print(f"Cipher: {cipher_name} ({cipher_bits} bits)", 'cyan')
    
    # Certificate info
    cert_info = results.get('cert_info', {})
    if cert_info:
        ColoredOutput.print("\nCertificate Information:", 'yellow', bold=True)
        if 'subject' in cert_info:
            ColoredOutput.print(f"  Subject: {cert_info['subject']}", 'white')
        if 'issuer' in cert_info:
            ColoredOutput.print(f"  Issuer: {cert_info['issuer']}", 'white')
        if 'notBefore' in cert_info:
            ColoredOutput.print(f"  Valid From: {cert_info['notBefore']}", 'white')
        if 'notAfter' in cert_info:
            ColoredOutput.print(f"  Valid Until: {cert_info['notAfter']}", 'white')
    
    # Vulnerability checks
    ColoredOutput.print("\nVulnerability Assessment:", 'yellow', bold=True)
    for key, value in results.items():
        if key.startswith('weak_cipher_'):
            cipher_type = key.replace('weak_cipher_', '')
            if value == "VULNERABLE":
                ColoredOutput.error(f"  {cipher_type}: VULNERABLE")
            else:
                ColoredOutput.success(f"  {cipher_type}: NOT VULNERABLE")


def _print_rtsp_results(results: Dict[str, Any]):
    """Print RTSP scan results in a formatted way."""
    ColoredOutput.success("RTSP Stream Discovery Results")
    
    # OPTIONS response
    options = results.get('options_response', '')
    if options:
        ColoredOutput.print(f"Server Response: {options[:100]}...", 'cyan')
    
    # Stream paths
    ColoredOutput.print("\nAvailable Streams:", 'yellow', bold=True)
    available_count = 0
    for key, value in results.items():
        if key.startswith('path_'):
            path = key.replace('path_', '')
            if value == "AVAILABLE":
                ColoredOutput.success(f"  {path}: AVAILABLE")
                available_count += 1
            elif value == "NOT_FOUND":
                ColoredOutput.print(f"  {path}: NOT FOUND", 'white')
            else:
                ColoredOutput.error(f"  {path}: ERROR ({value})")
    
    if available_count == 0:
        ColoredOutput.warning("No RTSP streams found") 