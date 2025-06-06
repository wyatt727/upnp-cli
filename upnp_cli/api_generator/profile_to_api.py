#!/usr/bin/env python3
"""
Profile to API Generator

Generates REST API endpoints from enhanced profiles with complete SCPD data.
Creates FastAPI or Flask applications for device control.
"""

import json
import time
from typing import Dict, List, Any, Optional
from pathlib import Path

from upnp_cli.cli.output import ColoredOutput
from upnp_cli.logging_utils import get_logger

logger = get_logger(__name__)


def generate_fastapi_from_profile(profile: Dict[str, Any], output_dir: Path) -> Path:
    """Generate FastAPI application from enhanced profile."""
    
    ColoredOutput.info(f"🚀 Generating FastAPI for {profile['name']}")
    
    # Extract profile data
    device_name = profile['name'].replace(' ', '_').replace('/', '_').lower()
    action_inventory = profile.get('upnp', {}).get('action_inventory', {})
    state_variables = profile.get('upnp', {}).get('state_variables', {})
    services = profile.get('upnp', {}).get('services', {})
    
    if not action_inventory:
        raise ValueError("Profile lacks enhanced SCPD data - cannot generate API")
    
    # Generate FastAPI code
    api_code = _generate_fastapi_code(profile, action_inventory, state_variables, services)
    
    # Write API file
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    api_file = output_dir / f"{device_name}_api.py"
    
    with open(api_file, 'w') as f:
        f.write(api_code)
    
    # Generate requirements.txt
    requirements_file = output_dir / "requirements.txt"
    requirements_content = """fastapi==0.104.1
uvicorn==0.24.0
pydantic==2.5.0
aiohttp==3.9.1
python-multipart==0.0.6
"""
    
    with open(requirements_file, 'w') as f:
        f.write(requirements_content)
    
    # Generate startup script
    startup_file = output_dir / f"start_{device_name}_api.sh"
    startup_content = f"""#!/bin/bash
# Auto-generated startup script for {profile['name']} API
# Generated on {time.strftime('%Y-%m-%d %H:%M:%S')}

echo "Starting {profile['name']} API server..."
uvicorn {device_name}_api:app --host 0.0.0.0 --port 8000 --reload
"""
    
    with open(startup_file, 'w') as f:
        f.write(startup_content)
    
    startup_file.chmod(0o755)
    
    ColoredOutput.success(f"✅ Generated FastAPI: {api_file}")
    ColoredOutput.info(f"📋 Requirements: {requirements_file}")
    ColoredOutput.info(f"🚀 Startup script: {startup_file}")
    
    return api_file


def _generate_fastapi_code(profile: Dict[str, Any], action_inventory: Dict, state_variables: Dict, services: Dict) -> str:
    """Generate FastAPI application code."""
    
    device_name = profile['name']
    generation_time = time.strftime('%Y-%m-%d %H:%M:%S')
    
    # Generate imports and setup
    code = f'''#!/usr/bin/env python3
"""
{device_name} REST API

Auto-generated FastAPI application for {device_name} control.
Generated from enhanced UPnP profile on {generation_time}.

This API provides REST endpoints for all device actions discovered via SCPD analysis.
"""

from fastapi import FastAPI, HTTPException, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional
import aiohttp
import asyncio
import json
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="{device_name} API",
    description="Auto-generated REST API for {device_name} UPnP device control",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Device configuration (set via environment or initialization)
DEVICE_HOST = None
DEVICE_PORT = None

# Profile metadata
PROFILE_METADATA = {json.dumps(profile.get('metadata', {}), indent=4)}

# Service configuration
SERVICES = {json.dumps(services, indent=4)}

# SOAP client for UPnP actions
class SOAPClient:
    """Simple SOAP client for UPnP actions."""
    
    @staticmethod
    async def call_action(control_url: str, service_type: str, action_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute SOAP action."""
        
        # Build SOAP envelope
        soap_body = f'<u:{action_name} xmlns:u="{service_type}">'
        for arg_name, arg_value in arguments.items():
            soap_body += f'<{arg_name}>{arg_value}</{arg_name}>'
        soap_body += f'</u:{action_name}>'
        
        soap_envelope = f"""<?xml version="1.0" encoding="utf-8"?>
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
    <s:Body>
        {soap_body}
    </s:Body>
</s:Envelope>"""
        
        headers = {
            'Content-Type': 'text/xml; charset="utf-8"',
            'SOAPAction': f'"{service_type}#{action_name}"'
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(control_url, data=soap_envelope, headers=headers) as response:
                if response.status != 200:
                    raise HTTPException(status_code=response.status, detail=f"SOAP action failed: {response.status}")
                
                response_text = await response.text()
                
                # Simple XML parsing for response values
                result = {}
                import xml.etree.ElementTree as ET
                try:
                    root = ET.fromstring(response_text)
                    for elem in root.iter():
                        if elem.text and elem.tag.split('}')[-1] not in ['Envelope', 'Body', action_name + 'Response']:
                            tag_name = elem.tag.split('}')[-1]
                            result[tag_name] = elem.text
                except ET.ParseError:
                    pass
                
                return result

soap_client = SOAPClient()

# Pydantic models for request validation
'''

    # Generate Pydantic models for each action
    for service_name, actions in action_inventory.items():
        code += f'\n# === {service_name.title()} Service Models ===\n'
        
        for action_name, action_info in actions.items():
            arguments_in = action_info.get('arguments_in', [])
            
            if arguments_in:
                model_name = f"{action_name}Request"
                code += f'\nclass {model_name}(BaseModel):\n'
                code += f'    """Request model for {action_name} action."""\n'
                
                for arg in arguments_in:
                    arg_name = arg['name']
                    data_type = arg.get('data_type', 'str')
                    validation = arg.get('validation', {})
                    
                    # Map UPnP data types to Python types
                    python_type = _map_data_type(data_type)
                    
                    # Add validation constraints
                    field_params = []
                    if 'allowed_values' in validation:
                        allowed_values = validation['allowed_values']
                        field_params.append(f"description='Allowed values: {', '.join(allowed_values)}'")
                    
                    if 'minimum' in validation and 'maximum' in validation:
                        field_params.append(f"ge={validation['minimum']}, le={validation['maximum']}")
                    
                    field_str = f"Field({', '.join(field_params)})" if field_params else ""
                    
                    if field_str:
                        code += f'    {arg_name}: {python_type} = {field_str}\n'
                    else:
                        code += f'    {arg_name}: {python_type}\n'
                
                code += '\n'
    
    # Generate initialization endpoint
    code += '''
# === Device Initialization ===

@app.post("/init")
async def initialize_device(host: str = Query(..., description="Device IP address"), 
                          port: int = Query(default=1400, description="Device port")):
    """Initialize API with device connection details."""
    global DEVICE_HOST, DEVICE_PORT
    
    DEVICE_HOST = host
    DEVICE_PORT = port
    
    # Test connection
    try:
        device_url = f"http://{host}:{port}/xml/device_description.xml"
        async with aiohttp.ClientSession() as session:
            async with session.get(device_url) as response:
                if response.status != 200:
                    raise HTTPException(status_code=400, detail="Cannot connect to device")
        
        return {"status": "success", "message": f"Connected to device at {host}:{port}"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Connection failed: {e}")

@app.get("/status")
async def get_api_status():
    """Get API and device status."""
    return {
        "api_status": "running",
        "device_host": DEVICE_HOST,
        "device_port": DEVICE_PORT,
        "connected": DEVICE_HOST is not None,
        "profile_name": "''' + device_name + '''",
        "total_actions": ''' + str(sum(len(actions) for actions in action_inventory.values())) + '''
    }

@app.get("/profile")
async def get_profile_info():
    """Get complete profile information."""
    return {
        "profile": ''' + json.dumps(profile, indent=8) + ''',
        "services": SERVICES,
        "metadata": PROFILE_METADATA
    }

def _check_device_connection():
    """Check if device is initialized."""
    if not DEVICE_HOST:
        raise HTTPException(status_code=400, detail="Device not initialized. Call /init first.")

'''

    # Generate endpoints for each action
    for service_name, actions in action_inventory.items():
        code += f'\n# === {service_name.title()} Service Endpoints ===\n'
        
        service_info = services.get(service_name, {})
        control_url = service_info.get('controlURL', '')
        service_type = service_info.get('serviceType', '')
        
        for action_name, action_info in actions.items():
            arguments_in = action_info.get('arguments_in', [])
            arguments_out = action_info.get('arguments_out', [])
            description = action_info.get('description', f"Execute {action_name} action")
            complexity = action_info.get('complexity', '🟢 Easy')
            category = action_info.get('category', 'other')
            
            endpoint_path = f"/{service_name.lower()}/{_to_snake_case(action_name)}"
            
            # Generate endpoint
            if arguments_in:
                model_name = f"{action_name}Request"
                code += f'''
@app.post("{endpoint_path}")
async def {_to_snake_case(action_name)}(request: {model_name}):
    """
    {description}
    
    Complexity: {complexity}
    Category: {category}
    Service: {service_name}
    """
    _check_device_connection()
    
    control_url = f"http://{{{{DEVICE_HOST}}}}:{{{{DEVICE_PORT}}}}{control_url}"
    service_type = "{service_type}"
    
    # Convert request to arguments dict
    arguments = request.dict()
    
    try:
        result = await soap_client.call_action(control_url, service_type, "{action_name}", arguments)
        
        return {{
            "status": "success",
            "action": "{action_name}",
            "arguments": arguments,
            "result": result
        }}
    except Exception as e:
        logger.error(f"{action_name} failed: {{{{e}}}}")
        raise HTTPException(status_code=500, detail=f"Action failed: {{{{e}}}}")
'''
            else:
                code += f'''
@app.post("{endpoint_path}")
async def {_to_snake_case(action_name)}():
    """
    {description}
    
    Complexity: {complexity}
    Category: {category}
    Service: {service_name}
    """
    _check_device_connection()
    
    control_url = f"http://{{{{DEVICE_HOST}}}}:{{{{DEVICE_PORT}}}}{control_url}"
    service_type = "{service_type}"
    
    try:
        result = await soap_client.call_action(control_url, service_type, "{action_name}", {{}})
        
        return {{
            "status": "success",
            "action": "{action_name}",
            "result": result
        }}
    except Exception as e:
        logger.error(f"{action_name} failed: {{{{e}}}}")
        raise HTTPException(status_code=500, detail=f"Action failed: {{{{e}}}}")
'''

    # Add convenience endpoints
    code += '''

# === Convenience Endpoints ===

@app.get("/actions")
async def list_all_actions():
    """List all available actions organized by service."""
    actions_by_service = {}
    
'''
    
    for service_name, actions in action_inventory.items():
        code += f'''    actions_by_service["{service_name}"] = {{\n'''
        for action_name, action_info in actions.items():
            complexity = action_info.get('complexity', '🟢 Easy')
            category = action_info.get('category', 'other')
            args_count = len(action_info.get('arguments_in', []))
            
            code += f'''        "{action_name}": {{
            "endpoint": "/{service_name.lower()}/{_to_snake_case(action_name)}",
            "complexity": "{complexity}",
            "category": "{category}",
            "arguments_required": {args_count}
        }},\n'''
        code += f'    }}\n'
    
    code += '''
    return {
        "total_actions": ''' + str(sum(len(actions) for actions in action_inventory.values())) + ''',
        "actions_by_service": actions_by_service
    }

@app.get("/actions/category/{category}")
async def list_actions_by_category(category: str):
    """List actions by category."""
    categorized_actions = []
    
'''
    
    # Add categorized action listings
    for service_name, actions in action_inventory.items():
        for action_name, action_info in actions.items():
            code += f'''    if "{action_info.get('category', 'other')}" == category:
        categorized_actions.append({{
            "action": "{action_name}",
            "service": "{service_name}",
            "endpoint": "/{service_name.lower()}/{_to_snake_case(action_name)}",
            "complexity": "{action_info.get('complexity', '🟢 Easy')}"
        }})
'''
    
    code += '''
    return {
        "category": category,
        "actions": categorized_actions
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
'''
    
    return code


def _map_data_type(upnp_type: str) -> str:
    """Map UPnP data types to Python types."""
    type_mapping = {
        'string': 'str',
        'ui4': 'int',
        'ui2': 'int', 
        'ui1': 'int',
        'i4': 'int',
        'i2': 'int',
        'i1': 'int',
        'boolean': 'bool',
        'r4': 'float',
        'r8': 'float',
        'number': 'float',
        'fixed.14.4': 'float',
        'float': 'float',
        'char': 'str',
        'date': 'str',
        'dateTime': 'str',
        'dateTime.tz': 'str',
        'time': 'str',
        'time.tz': 'str',
        'bin.base64': 'str',
        'bin.hex': 'str',
        'uri': 'str',
        'uuid': 'str'
    }
    
    return type_mapping.get(upnp_type.lower(), 'str')


def _to_snake_case(camel_str: str) -> str:
    """Convert CamelCase to snake_case."""
    import re
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', camel_str)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


def generate_api_documentation(profile: Dict[str, Any], output_dir: Path) -> Path:
    """Generate comprehensive API documentation."""
    
    device_name = profile['name']
    action_inventory = profile.get('upnp', {}).get('action_inventory', {})
    
    doc_content = f"""# {device_name} REST API Documentation

Auto-generated REST API for {device_name} UPnP device control.
Generated on {time.strftime('%Y-%m-%d %H:%M:%S')}.

## Overview

This API provides REST endpoints for all {sum(len(actions) for actions in action_inventory.values())} actions discovered via SCPD analysis.

## Getting Started

1. Install dependencies: `pip install -r requirements.txt`
2. Start the API: `./start_{device_name.replace(' ', '_').lower()}_api.sh`
3. Initialize device connection: `POST /init?host=DEVICE_IP&port=DEVICE_PORT`
4. Access interactive docs at: `http://localhost:8000/docs`

## Quick Start

```bash
# Initialize connection
curl -X POST "http://localhost:8000/init?host=192.168.1.100&port=1400"

# Check status
curl "http://localhost:8000/status"

# List all actions
curl "http://localhost:8000/actions"
```

## Service Endpoints

"""
    
    for service_name, actions in action_inventory.items():
        doc_content += f"\n### {service_name.title()} Service\n\n"
        
        for action_name, action_info in actions.items():
            endpoint_path = f"/{service_name.lower()}/{_to_snake_case(action_name)}"
            complexity = action_info.get('complexity', '🟢 Easy')
            category = action_info.get('category', 'other')
            description = action_info.get('description', f"Execute {action_name} action")
            
            doc_content += f"#### `POST {endpoint_path}`\n\n"
            doc_content += f"**{action_name}** - {description}\n\n"
            doc_content += f"- Complexity: {complexity}\n"
            doc_content += f"- Category: {category}\n\n"
            
            arguments_in = action_info.get('arguments_in', [])
            if arguments_in:
                doc_content += "**Request Body:**\n```json\n{\n"
                for arg in arguments_in:
                    arg_name = arg['name']
                    data_type = arg.get('data_type', 'string')
                    validation = arg.get('validation', {})
                    
                    doc_content += f'  "{arg_name}": "{data_type}"'
                    if 'allowed_values' in validation:
                        doc_content += f"  // Allowed: {', '.join(validation['allowed_values'])}"
                    doc_content += "\n"
                doc_content += "}\n```\n\n"
            
            doc_content += f"**Example:**\n```bash\ncurl -X POST 'http://localhost:8000{endpoint_path}'"
            if arguments_in:
                doc_content += " \\\n  -H 'Content-Type: application/json' \\\n  -d '{"
                example_args = []
                for arg in arguments_in:
                    example_value = _get_example_value(arg)
                    example_args.append(f'"{arg["name"]}": "{example_value}"')
                doc_content += ", ".join(example_args) + "}'"
            doc_content += "\n```\n\n"
    
    # Write documentation
    output_dir = Path(output_dir)
    doc_file = output_dir / f"{device_name.replace(' ', '_').lower()}_api_docs.md"
    
    with open(doc_file, 'w') as f:
        f.write(doc_content)
    
    ColoredOutput.success(f"📚 Generated API documentation: {doc_file}")
    
    return doc_file


def _get_example_value(arg_info: Dict[str, Any]) -> str:
    """Get example value for an argument."""
    arg_name = arg_info['name']
    validation = arg_info.get('validation', {})
    
    # Use allowed values if available
    if 'allowed_values' in validation and validation['allowed_values']:
        return validation['allowed_values'][0]
    
    # Use common examples based on argument name
    example_map = {
        'InstanceID': '0',
        'Speed': '1',
        'CurrentURI': 'http://example.com/audio.mp3',
        'DesiredVolume': '50',
        'Channel': 'Master',
        'DesiredMute': '0',
        'ObjectID': '0',
        'BrowseFlag': 'BrowseDirectChildren'
    }
    
    if arg_name in example_map:
        return example_map[arg_name]
    
    # Use range midpoint if available
    if 'minimum' in validation and 'maximum' in validation:
        midpoint = (validation['minimum'] + validation['maximum']) // 2
        return str(midpoint)
    
    # Default examples by data type
    data_type = arg_info.get('data_type', 'string').lower()
    if 'int' in data_type or 'ui' in data_type or 'i' in data_type:
        return '0'
    elif 'bool' in data_type:
        return 'false'
    elif 'float' in data_type or 'r' in data_type:
        return '0.0'
    else:
        return 'example_value'


async def generate_profile_api(profile_file: Path, output_dir: Path) -> Dict[str, Any]:
    """Generate complete API from enhanced profile file."""
    
    ColoredOutput.header(f"🚀 Generating REST API from Enhanced Profile")
    
    # Load profile
    with open(profile_file, 'r') as f:
        profile_data = json.load(f)
    
    # Handle multiple profiles or single profile
    if 'profiles' in profile_data:
        profiles = profile_data['profiles']
    else:
        profiles = [profile_data]
    
    results = {"generated_apis": []}
    
    for profile in profiles:
        if not profile.get('upnp', {}).get('action_inventory'):
            ColoredOutput.warning(f"⚠️  Profile {profile.get('name', 'Unknown')} lacks enhanced SCPD data - skipping")
            continue
        
        device_name = profile['name'].replace(' ', '_').replace('/', '_').lower()
        device_output_dir = output_dir / device_name
        
        try:
            # Generate FastAPI
            api_file = generate_fastapi_from_profile(profile, device_output_dir)
            
            # Generate documentation
            doc_file = generate_api_documentation(profile, device_output_dir)
            
            results["generated_apis"].append({
                "device_name": profile['name'],
                "api_file": str(api_file),
                "doc_file": str(doc_file),
                "total_actions": sum(len(actions) for actions in profile['upnp']['action_inventory'].values())
            })
            
        except Exception as e:
            ColoredOutput.error(f"❌ Failed to generate API for {profile['name']}: {e}")
            results["generated_apis"].append({
                "device_name": profile['name'],
                "error": str(e)
            })
    
    # Generate summary
    successful_apis = [api for api in results["generated_apis"] if 'error' not in api]
    
    ColoredOutput.success(f"✅ Generated {len(successful_apis)} REST APIs")
    
    if successful_apis:
        ColoredOutput.print("\n📋 Generated APIs:", 'cyan', bold=True)
        for api in successful_apis:
            ColoredOutput.print(f"  🚀 {api['device_name']} ({api['total_actions']} actions)", 'white')
            ColoredOutput.print(f"     API: {api['api_file']}", 'gray')
            ColoredOutput.print(f"     Docs: {api['doc_file']}", 'gray')
    
    return results


async def cmd_generate_api(args) -> Dict[str, Any]:
    """Command entry point for API generation."""
    
    profile_file = Path(args.profile_file)
    if not profile_file.exists():
        return {"status": "error", "message": f"Profile file not found: {profile_file}"}
    
    output_dir = Path(args.output_dir) if args.output_dir else Path("generated_apis")
    
    try:
        result = await generate_profile_api(profile_file, output_dir)
        return {"status": "success", **result}
    
    except Exception as e:
        ColoredOutput.error(f"API generation failed: {e}")
        return {"status": "error", "message": str(e)} 