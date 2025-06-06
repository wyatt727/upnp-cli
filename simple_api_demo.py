#!/usr/bin/env python3
"""
Simple API Generation Demo

Creates a basic FastAPI from the Sonos profile to demonstrate the concept.
"""

import json
from pathlib import Path

def generate_simple_api_demo():
    """Generate a simple working API demo from the Sonos profile."""
    
    print("🚀 Creating Simple API Demo from Sonos Profile")
    print("=" * 50)
    
    # Load the Sonos profile
    profile_file = Path('enhanced_profiles/enhanced_profiles_20250605_200735_individual/Sonos,_Inc._Sonos_Port_147actions.json')
    
    if not profile_file.exists():
        print(f"❌ Profile file not found: {profile_file}")
        return
    
    with open(profile_file, 'r') as f:
        profile = json.load(f)
    
    print(f"📱 Device: {profile['name']}")
    
    # Get action inventory
    action_inventory = profile.get('upnp', {}).get('action_inventory', {})
    services = profile.get('upnp', {}).get('services', {})
    
    total_actions = sum(len(actions) for actions in action_inventory.values())
    print(f"🎯 Total Actions: {total_actions}")
    
    # Create output directory
    output_dir = Path('demo_api')
    output_dir.mkdir(exist_ok=True)
    
    # Generate a simple FastAPI
    api_code = generate_demo_api_code(profile, action_inventory, services)
    
    # Write API file
    api_file = output_dir / "sonos_api_demo.py"
    with open(api_file, 'w') as f:
        f.write(api_code)
    
    # Create requirements
    requirements = """fastapi==0.104.1
uvicorn==0.24.0
aiohttp==3.9.1
"""
    with open(output_dir / "requirements.txt", 'w') as f:
        f.write(requirements)
    
    # Create startup script
    startup_script = """#!/bin/bash
echo "🚀 Starting Sonos API Demo..."
cd demo_api
pip install -r requirements.txt
uvicorn sonos_api_demo:app --host 0.0.0.0 --port 8000 --reload
"""
    with open(output_dir / "start_api.sh", 'w') as f:
        f.write(startup_script)
    
    Path(output_dir / "start_api.sh").chmod(0o755)
    
    print(f"✅ Generated API demo in: {output_dir}")
    print(f"📄 API file: {api_file}")
    print(f"🚀 To start: cd {output_dir} && ./start_api.sh")
    print(f"📚 Docs at: http://localhost:8000/docs")

def generate_demo_api_code(profile, action_inventory, services):
    """Generate simplified API code."""
    
    device_name = profile['name']
    total_actions = sum(len(actions) for actions in action_inventory.values())
    
    code = f'''#!/usr/bin/env python3
"""
{device_name} REST API Demo

Auto-generated FastAPI demonstration for {device_name} control.
This API provides REST endpoints for {total_actions} UPnP actions.
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, Optional
import aiohttp
import json

# FastAPI app
app = FastAPI(
    title="{device_name} Demo API",
    description="Demo REST API for {device_name} UPnP device control",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Device configuration
DEVICE_HOST = None
DEVICE_PORT = None

@app.get("/")
async def root():
    """API root with overview."""
    return {{
        "api": "{device_name} Demo API",
        "total_actions": {total_actions},
        "services": {len(action_inventory)},
        "status": "ready",
        "device_connected": DEVICE_HOST is not None,
        "docs": "/docs"
    }}

@app.post("/init")
async def initialize_device(host: str = Query(...), port: int = Query(default=1400)):
    """Initialize connection to the UPnP device."""
    global DEVICE_HOST, DEVICE_PORT
    
    DEVICE_HOST = host
    DEVICE_PORT = port
    
    return {{
        "status": "success", 
        "message": f"Connected to {{host}}:{{port}}",
        "device": "{device_name}"
    }}

@app.get("/actions")
async def list_all_actions():
    """List all available UPnP actions by service."""
    actions_by_service = {{}}
    
'''
    
    # Add action listings for each service
    for service_name, actions in action_inventory.items():
        code += f'    actions_by_service["{service_name}"] = {{\n'
        for action_name, action_info in actions.items():
            complexity = action_info.get('complexity', '🟢 Easy')
            category = action_info.get('category', 'other')
            args_count = len(action_info.get('arguments_in', []))
            
            code += f'        "{action_name}": {{\n'
            code += f'            "complexity": "{complexity}",\n'
            code += f'            "category": "{category}",\n'
            code += f'            "arguments_required": {args_count}\n'
            code += f'        }},\n'
        code += f'    }}\n'
    
    code += f'''
    return {{
        "total_actions": {total_actions},
        "actions_by_service": actions_by_service
    }}

@app.get("/services")
async def list_services():
    """List all UPnP services."""
    services_info = {{}}
'''
    
    # Add service information
    for service_name, service_info in services.items():
        action_count = service_info.get('action_count', 0)
        service_type = service_info.get('serviceType', '')
        
        code += f'    services_info["{service_name}"] = {{\n'
        code += f'        "type": "{service_type}",\n'
        code += f'        "actions": {action_count},\n'
        code += f'        "control_url": "{service_info.get("controlURL", "")}"\n'
        code += f'    }}\n'
    
    code += '''
    return {
        "services": services_info
    }

# Example action endpoints (first few for demo)
'''
    
    # Add a few example action endpoints
    example_count = 0
    for service_name, actions in action_inventory.items():
        if example_count >= 5:  # Limit to 5 examples
            break
            
        service_info = services.get(service_name, {})
        control_url = service_info.get('controlURL', '')
        
        for action_name, action_info in actions.items():
            if example_count >= 5:
                break
            
            endpoint_name = action_name.lower().replace('get', '').replace('set', '')
            complexity = action_info.get('complexity', '🟢 Easy')
            category = action_info.get('category', 'other')
            
            code += f'''
@app.post("/{service_name.lower()}/{endpoint_name}")
async def {action_name.lower()}():
    """
    Execute {action_name} action
    
    Complexity: {complexity}
    Category: {category}
    Service: {service_name}
    """
    if not DEVICE_HOST:
        raise HTTPException(status_code=400, detail="Device not initialized. Call /init first.")
    
    return {{
        "status": "demo",
        "action": "{action_name}",
        "service": "{service_name}",
        "message": "This is a demo endpoint - would execute {action_name} on real device"
    }}
'''
            example_count += 1
    
    code += '''
@app.get("/security")
async def security_analysis():
    """Show security-relevant actions."""
    security_actions = []
'''
    
    # Add security actions
    for service_name, actions in action_inventory.items():
        for action_name, action_info in actions.items():
            if action_info.get('category') == 'security':
                code += f'    security_actions.append({{\n'
                code += f'        "action": "{action_name}",\n'
                code += f'        "service": "{service_name}",\n'
                code += f'        "complexity": "{action_info.get("complexity", "🟢 Easy")}"\n'
                code += f'    }})\n'
    
    code += '''
    return {
        "security_actions": security_actions,
        "warning": "These actions could modify device security settings!"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
'''
    
    return code

if __name__ == "__main__":
    generate_simple_api_demo() 