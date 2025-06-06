#!/usr/bin/env python3
"""
Simple Working Sonos API Demo

A minimal FastAPI example showing how UPnP profiles become REST APIs.
"""

from fastapi import FastAPI, HTTPException
import json

app = FastAPI(
    title="Sonos UPnP to REST API Demo",
    description="Demonstrates converting UPnP SOAP actions to REST endpoints",
    version="1.0.0"
)

# Simulated data from the real Sonos profile
SONOS_ACTIONS = {
    "renderingcontrol": {
        "GetVolume": {"complexity": "🟢 Easy", "category": "volume_control"},
        "SetVolume": {"complexity": "🟢 Easy", "category": "volume_control"},
        "GetMute": {"complexity": "🟢 Easy", "category": "volume_control"},
        "SetMute": {"complexity": "🟢 Easy", "category": "volume_control"}
    },
    "avtransport": {
        "Play": {"complexity": "🟢 Easy", "category": "media_control"},
        "Pause": {"complexity": "🟢 Easy", "category": "media_control"},
        "Stop": {"complexity": "🟢 Easy", "category": "media_control"},
        "SetAVTransportURI": {"complexity": "🟡 Medium", "category": "media_control"}
    },
    "systemproperties": {
        "EditAccountPasswordX": {"complexity": "🔴 Complex", "category": "security"}
    }
}

DEVICE_HOST = None

@app.get("/")
async def root():
    """API overview showing the power of UPnP to REST conversion."""
    total_actions = sum(len(actions) for actions in SONOS_ACTIONS.values())
    
    return {
        "message": "🚀 UPnP to REST API Demo",
        "device": "Sonos Port (from enhanced profile)",
        "total_actions_discovered": 196,
        "demo_actions_shown": total_actions,
        "connected": DEVICE_HOST is not None,
        "endpoints": {
            "/actions": "List all actions",
            "/security": "Show security actions",
            "/init": "Connect to device",
            "/docs": "Interactive API documentation"
        }
    }

@app.post("/init")
async def initialize_device(host: str, port: int = 1400):
    """Initialize connection to UPnP device."""
    global DEVICE_HOST
    DEVICE_HOST = f"{host}:{port}"
    
    return {
        "status": "success",
        "message": f"Connected to Sonos at {host}:{port}",
        "note": "In real implementation, this would test UPnP connectivity"
    }

@app.get("/actions")
async def list_actions():
    """List all UPnP actions converted to REST endpoints."""
    return {
        "total_services": len(SONOS_ACTIONS),
        "actions_by_service": SONOS_ACTIONS,
        "note": "Real implementation has 196 actions from SCPD analysis"
    }

@app.get("/security")
async def security_actions():
    """Show security-relevant UPnP actions."""
    security_actions = []
    
    for service, actions in SONOS_ACTIONS.items():
        for action, info in actions.items():
            if info.get("category") == "security":
                security_actions.append({
                    "action": action,
                    "service": service,
                    "complexity": info["complexity"],
                    "endpoint": f"/{service}/{action.lower()}"
                })
    
    return {
        "security_actions": security_actions,
        "warning": "⚠️ These actions can modify device security!",
        "penetration_testing_note": "Perfect targets for security research"
    }

# Example UPnP action converted to REST endpoint
@app.post("/renderingcontrol/set_volume")
async def set_volume(volume: int):
    """Set device volume (converted from UPnP SetVolume action)."""
    if not DEVICE_HOST:
        raise HTTPException(status_code=400, detail="Device not connected. Call /init first")
    
    if not 0 <= volume <= 100:
        raise HTTPException(status_code=400, detail="Volume must be 0-100")
    
    return {
        "status": "demo_success",
        "action": "SetVolume",
        "service": "RenderingControl", 
        "arguments": {"DesiredVolume": volume},
        "message": f"Would set volume to {volume} on {DEVICE_HOST}",
        "soap_equivalent": "This would send SOAP request to /RenderingControl/Control"
    }

@app.post("/systemproperties/edit_account_password")  
async def edit_account_password(account_type: str, account_id: str, new_password: str):
    """🔴 SECURITY ACTION: Edit account password (from UPnP SCPD analysis)."""
    if not DEVICE_HOST:
        raise HTTPException(status_code=400, detail="Device not connected")
    
    return {
        "status": "demo_warning",
        "action": "EditAccountPasswordX",
        "service": "SystemProperties",
        "complexity": "🔴 Complex",
        "category": "security", 
        "arguments": {
            "AccountType": account_type,
            "AccountID": account_id, 
            "NewAccountPassword": new_password
        },
        "warning": "⚠️ This would actually change device passwords!",
        "penetration_testing_value": "High - can compromise device accounts"
    }

@app.get("/demo/value")
async def penetration_testing_value():
    """Explain why this UPnP-to-REST conversion is valuable for pentesting."""
    return {
        "title": "🎯 Penetration Testing Value",
        "problems_solved": [
            "UPnP uses complex SOAP/XML - hard to integrate with modern tools",
            "Manual SOAP requests are tedious and error-prone", 
            "No easy way to script UPnP attack chains",
            "Security tools (Burp, ZAP) don't understand UPnP natively"
        ],
        "our_solution": [
            "Convert all UPnP actions to simple REST endpoints",
            "Auto-generate from enhanced profiles with SCPD analysis",
            "196 Sonos actions become 196 HTTP endpoints",
            "Perfect integration with existing security tools"
        ],
        "attack_scenarios": [
            "Use Burp Suite to intercept/modify all device actions",
            "Script device takeover with simple curl commands",
            "Fuzz all endpoints automatically",
            "Chain UPnP actions for complex attacks"
        ],
        "example_command": "curl -X POST 'http://localhost:8000/systemproperties/edit_account_password' -d '{\"account_type\":\"admin\",\"account_id\":\"root\",\"new_password\":\"pwned\"}'"
    }

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Simple Sonos API Demo...")
    print("📚 Visit http://localhost:8000/docs for interactive documentation")
    uvicorn.run(app, host="0.0.0.0", port=8000) 