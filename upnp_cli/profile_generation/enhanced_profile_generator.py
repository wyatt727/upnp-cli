#!/usr/bin/env python3
"""
Enhanced Profile Generator with Complete SCPD Integration

Generates device profiles with comprehensive SCPD action inventories,
argument specifications, and state variable constraints.
"""

import json
import time
from typing import Dict, List, Any, Optional
from pathlib import Path

from .scpd_parser import parse_device_scpds, SCPDDocument
from upnp_cli.cli.output import ColoredOutput
from upnp_cli.logging_utils import get_logger

logger = get_logger(__name__)


async def generate_enhanced_profile_with_scpd(device_info: Dict[str, Any], base_url: str) -> Dict[str, Any]:
    """Generate enhanced profile with complete SCPD data."""
    
    ColoredOutput.info(f"🔍 Generating enhanced profile with full SCPD analysis...")
    
    # Parse all SCPD documents for the device
    scpd_documents = await parse_device_scpds(device_info, base_url)
    
    # Create enhanced profile structure
    profile = {
        "name": f"{device_info.get('manufacturer', 'Unknown')} {device_info.get('modelName', 'Unknown')}",
        "match": {
            "manufacturer": [device_info.get('manufacturer', '')],
            "modelName": [device_info.get('modelName', '')],
            "deviceType": [device_info.get('deviceType', '')]
        },
        "metadata": {
            "generated_at": time.strftime('%Y-%m-%d %H:%M:%S'),
            "scpd_analysis": {
                "services_analyzed": len(scpd_documents),
                "successful_parses": len([doc for doc in scpd_documents if doc.parsing_success]),
                "total_actions": sum(doc.get_action_count() for doc in scpd_documents),
                "parsing_errors": []
            }
        },
        "upnp": {
            "services": {},
            "action_inventory": {},
            "state_variables": {},
            "capabilities": {
                "media_control": [],
                "volume_control": [],
                "information_retrieval": [],
                "configuration": [],
                "security": []
            }
        }
    }
    
    # Process each SCPD document
    for document in scpd_documents:
        if document.parsing_success:
            service_name = _extract_service_name(document.service_type)
            
            ColoredOutput.info(f"   📋 Processing {service_name} service ({document.get_action_count()} actions)")
            
            # Add service configuration
            profile["upnp"]["services"][service_name] = {
                "serviceType": document.service_type,
                "scpdURL": document.scpd_url,
                "controlURL": _find_control_url(device_info, document.service_type),
                "action_count": document.get_action_count(),
                "parsing_success": True
            }
            
            # Add complete action inventory with full specifications
            profile["upnp"]["action_inventory"][service_name] = {}
            for action_name, action in document.actions.items():
                profile["upnp"]["action_inventory"][service_name][action_name] = {
                    "name": action.name,
                    "description": action.description,
                    "arguments_in": [
                        {
                            "name": arg.name,
                            "direction": arg.direction,
                            "data_type": arg.data_type,
                            "related_state_variable": arg.related_state_variable,
                            "required": True,  # Assume all input args are required
                            "validation": _get_argument_validation(arg, document.state_variables)
                        }
                        for arg in action.arguments_in
                    ],
                    "arguments_out": [
                        {
                            "name": arg.name,
                            "direction": arg.direction,
                            "data_type": arg.data_type,
                            "related_state_variable": arg.related_state_variable
                        }
                        for arg in action.arguments_out
                    ],
                    "complexity": _calculate_action_complexity(action),
                    "category": _categorize_action(action.name),
                    "soap_template": _generate_soap_template(action, document.service_type)
                }
            
            # Add state variables with constraints
            profile["upnp"]["state_variables"][service_name] = {}
            for var_name, variable in document.state_variables.items():
                profile["upnp"]["state_variables"][service_name][var_name] = {
                    "name": variable.name,
                    "data_type": variable.data_type,
                    "send_events": variable.send_events,
                    "default_value": variable.default_value,
                    "allowed_values": variable.allowed_values,
                    "minimum": variable.minimum,
                    "maximum": variable.maximum,
                    "step": variable.step
                }
            
            # Categorize capabilities
            _categorize_service_capabilities(document, profile["upnp"]["capabilities"])
            
        else:
            # Record parsing failures
            profile["metadata"]["scpd_analysis"]["parsing_errors"].extend(document.parsing_errors)
    
    # Add capability summary
    capabilities = profile["upnp"]["capabilities"]
    profile["capabilities"] = {
        "media_control_actions": len(capabilities.get("media_control", [])),
        "volume_control_actions": len(capabilities.get("volume_control", [])),
        "information_actions": len(capabilities.get("information_retrieval", [])),
        "configuration_actions": len(capabilities.get("configuration", [])),
        "security_actions": len(capabilities.get("security", [])),
        "total_actions": sum(len(actions) for actions in capabilities.values())
    }
    
    ColoredOutput.success(f"✅ Enhanced profile generated with {profile['capabilities']['total_actions']} total actions")
    
    return profile


def _extract_service_name(service_type: str) -> str:
    """Extract friendly service name from service type URN."""
    if ':' in service_type:
        return service_type.split(':')[-2].lower()
    return service_type.lower()


def _find_control_url(device_info: Dict[str, Any], service_type: str) -> str:
    """Find control URL for a service type."""
    services = device_info.get('services', [])
    
    # Check embedded devices too
    embedded_devices = device_info.get('devices', [])
    for embedded_device in embedded_devices:
        services.extend(embedded_device.get('services', []))
    
    for service in services:
        if service.get('serviceType') == service_type:
            return service.get('controlURL', '')
    
    return ''


def _get_argument_validation(argument, state_variables: Dict) -> Dict[str, Any]:
    """Get validation rules for an argument from state variables."""
    validation = {}
    
    if argument.related_state_variable and argument.related_state_variable in state_variables:
        state_var = state_variables[argument.related_state_variable]
        
        if state_var.allowed_values:
            validation["allowed_values"] = state_var.allowed_values
        
        if state_var.minimum is not None:
            validation["minimum"] = state_var.minimum
        
        if state_var.maximum is not None:
            validation["maximum"] = state_var.maximum
        
        if state_var.data_type:
            validation["data_type"] = state_var.data_type
    
    return validation


def _calculate_action_complexity(action) -> str:
    """Calculate action complexity based on argument count."""
    total_args = len(action.arguments_in) + len(action.arguments_out)
    
    if total_args == 0:
        return "🟢 Easy"
    elif total_args <= 2:
        return "🟡 Medium"
    else:
        return "🔴 Complex"


def _categorize_action(action_name: str) -> str:
    """Categorize action by function."""
    action_lower = action_name.lower()
    
    if any(keyword in action_lower for keyword in ['play', 'pause', 'stop', 'next', 'previous', 'seek']):
        return "media_control"
    elif any(keyword in action_lower for keyword in ['volume', 'mute', 'bass', 'treble']):
        return "volume_control"
    elif any(keyword in action_lower for keyword in ['get', 'info', 'status', 'current', 'list']):
        return "information_retrieval"
    elif any(keyword in action_lower for keyword in ['set', 'config', 'update', 'add', 'remove']):
        return "configuration"
    elif any(keyword in action_lower for keyword in ['auth', 'security', 'login', 'password']):
        return "security"
    else:
        return "other"


def _categorize_service_capabilities(document: SCPDDocument, capabilities: Dict[str, List]):
    """Categorize service capabilities by action types."""
    for action_name, action in document.actions.items():
        category = _categorize_action(action_name)
        if category != "other" and action_name not in capabilities.get(category, []):
            capabilities[category].append(action_name)


def _generate_soap_template(action, service_type: str) -> str:
    """Generate SOAP envelope template for the action."""
    args_xml = ""
    for arg in action.arguments_in:
        args_xml += f"      <{arg.name}>{{{arg.name.upper()}}}</{arg.name}>\n"
    
    template = f'''<?xml version="1.0" encoding="utf-8"?>
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
  <s:Body>
    <u:{action.name} xmlns:u="{service_type}">
{args_xml.rstrip()}
    </u:{action.name}>
  </s:Body>
</s:Envelope>'''
    
    return template


async def generate_enhanced_profiles_for_devices(devices: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate enhanced profiles for multiple devices."""
    
    ColoredOutput.header("🧠 Enhanced Profile Generation with Complete SCPD Analysis")
    
    enhanced_profiles = {
        "metadata": {
            "generated_at": time.strftime('%Y-%m-%d %H:%M:%S'),
            "generation_method": "enhanced_scpd_analysis",
            "total_devices": len(devices),
            "profiles_generated": 0
        },
        "profiles": [],
        "analysis_summary": {
            "total_services": 0,
            "total_actions": 0,
            "total_state_variables": 0,
            "parsing_errors": []
        }
    }
    
    for device in devices:
        try:
            ip = device.get('ip')
            port = device.get('port', 1400)
            base_url = f"http://{ip}:{port}"
            
            ColoredOutput.info(f"🔍 Analyzing device: {device.get('friendlyName', f'{ip}:{port}')}")
            
            # Generate enhanced profile
            profile = await generate_enhanced_profile_with_scpd(device, base_url)
            
            if profile and profile.get('capabilities', {}).get('total_actions', 0) > 0:
                enhanced_profiles["profiles"].append(profile)
                enhanced_profiles["metadata"]["profiles_generated"] += 1
                
                # Update analysis summary
                scpd_analysis = profile["metadata"]["scpd_analysis"]
                enhanced_profiles["analysis_summary"]["total_services"] += scpd_analysis["services_analyzed"]
                enhanced_profiles["analysis_summary"]["total_actions"] += scpd_analysis["total_actions"]
                enhanced_profiles["analysis_summary"]["parsing_errors"].extend(scpd_analysis["parsing_errors"])
                
                # Count state variables
                for service_vars in profile["upnp"]["state_variables"].values():
                    enhanced_profiles["analysis_summary"]["total_state_variables"] += len(service_vars)
                
                ColoredOutput.success(f"✅ Enhanced profile created for {profile['name']}")
            else:
                ColoredOutput.warning(f"⚠️  No actionable profile generated for {device.get('friendlyName', 'Unknown')}")
        
        except Exception as e:
            error_msg = f"Failed to generate enhanced profile for {device.get('friendlyName', 'Unknown')}: {e}"
            logger.error(error_msg)
            enhanced_profiles["analysis_summary"]["parsing_errors"].append(error_msg)
    
    ColoredOutput.success(f"🎯 Generated {enhanced_profiles['metadata']['profiles_generated']} enhanced profiles")
    
    return enhanced_profiles


async def save_enhanced_profiles(enhanced_profiles: Dict[str, Any], output_dir: Path, individual_files: bool = True) -> Path:
    """Save enhanced profiles to files."""
    
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    
    # Save main profiles file
    main_file = output_dir / f"enhanced_profiles_{timestamp}.json"
    with open(main_file, 'w') as f:
        json.dump(enhanced_profiles, f, indent=2)
    
    ColoredOutput.success(f"📁 Enhanced profiles saved to: {main_file}")
    
    # Save individual profile files if requested
    if individual_files and enhanced_profiles["profiles"]:
        individual_dir = output_dir / f"enhanced_profiles_{timestamp}_individual"
        individual_dir.mkdir(exist_ok=True)
        
        for profile in enhanced_profiles["profiles"]:
            profile_name = profile["name"].replace(" ", "_").replace("/", "_")
            total_actions = profile.get("capabilities", {}).get("total_actions", 0)
            individual_file = individual_dir / f"{profile_name}_{total_actions}actions.json"
            
            with open(individual_file, 'w') as f:
                json.dump(profile, f, indent=2)
        
        ColoredOutput.info(f"📂 Individual enhanced profiles saved to: {individual_dir}")
    
    return main_file 