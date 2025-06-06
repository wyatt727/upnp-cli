# UPnP CLI System Architecture

## Overview

UPnP CLI is a comprehensive penetration testing toolkit designed around a multi-stage pipeline that transforms legacy UPnP protocols into modern, security-tool-compatible interfaces. This document describes the complete system architecture, component relationships, and data flow.

## 🏗️ **System Architecture Overview**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            UPnP CLI System Architecture                      │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌───────────────┐
│   Network       │    │   Enhanced      │    │   REST API      │    │   Security    │
│   Discovery     │───▶│   Profiling     │───▶│   Generation    │───▶│   Testing     │
│                 │    │                 │    │                 │    │               │
│ • SSDP Scan     │    │ • SCPD Analysis │    │ • FastAPI Apps  │    │ • Burp Suite  │
│ • Device Enum   │    │ • Action Maps   │    │ • HTTP Endpoints│    │ • OWASP ZAP   │
│ • Service IDs   │    │ • Categories    │    │ • OpenAPI Docs  │    │ • Scripting   │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └───────────────┘
         │                       │                       │                      │
         │                       │                       │                      │
         ▼                       ▼                       ▼                      ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌───────────────┐
│  Data Storage   │    │  Profile Store  │    │  API Registry   │    │  Test Results │
│                 │    │                 │    │                 │    │               │
│ • Device Cache  │    │ • JSON Profiles │    │ • Generated APIs│    │ • Vuln Reports│
│ • Service Maps  │    │ • Action Specs  │    │ • API Metadata  │    │ • Evidence    │
│ • History       │    │ • Metadata      │    │ • Startup Scripts│    │ • Logs        │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └───────────────┘
```

## 🔧 **Core Components**

### 1. **Network Discovery Engine**
**Location**: `upnp_cli/core/discovery.py`
**Purpose**: Automated UPnP device and service discovery

#### **Capabilities:**
- **SSDP (Simple Service Discovery Protocol)** scanning
- **Multi-cast discovery** with configurable timeouts
- **Device description** fetching and parsing
- **Service enumeration** with endpoint identification
- **Network topology mapping**

#### **Discovery Methods:**
```python
# Standard SSDP discovery
devices = await discover_upnp_devices(timeout=10)

# Aggressive network scanning  
devices = await aggressive_discover(port_range="1-65535")

# Targeted device discovery
device = await discover_device(host="192.168.1.100", port=1400)
```

#### **Data Flow:**
```
SSDP Multicast → Device Responses → Description XML → Service URLs → Device Objects
```

### 2. **Enhanced Profile Generator**
**Location**: `upnp_cli/profile_generation/`
**Purpose**: Deep SCPD analysis and comprehensive capability mapping

#### **Profile Generation Pipeline:**
```python
1. Device Discovery      → Find all UPnP devices
2. SCPD Retrieval       → Download all service descriptions  
3. Action Extraction    → Parse every available action
4. Argument Analysis    → Extract parameter specifications
5. Categorization       → Classify by security relevance
6. Enhancement          → Add metadata and complexity ratings
7. Serialization        → Generate JSON profiles
```

#### **Enhanced Profile Schema:**
```json
{
  "metadata": {
    "generated_at": "2025-06-05T20:07:35",
    "generator_version": "1.0.0",
    "scpd_analysis": {
      "services_analyzed": 15,
      "total_actions": 196,
      "parsing_errors": [],
      "analysis_duration": 12.34
    }
  },
  "device_info": {
    "name": "Sonos Port",
    "manufacturer": "Sonos, Inc.",
    "model": "Sonos Port",
    "ip_address": "192.168.4.152",
    "port": 1400
  },
  "upnp": {
    "action_inventory": {
      "service_name": {
        "ActionName": {
          "complexity": "🟢 Easy | 🟡 Medium | 🔴 Complex",
          "category": "media_control | volume_control | information | configuration | security",
          "arguments_in": [
            {
              "name": "ArgumentName",
              "data_type": "string",
              "allowed_values": [],
              "required": true
            }
          ],
          "arguments_out": [...],
          "description": "Human-readable action description",
          "service_type": "urn:schemas-upnp-org:service:ServiceName:1",
          "control_url": "/ServiceName/Control"
        }
      }
    },
    "state_variables": {
      "VariableName": {
        "data_type": "string",
        "allowed_values": ["value1", "value2"],
        "default_value": "default"
      }
    },
    "services": {
      "service_name": {
        "serviceType": "urn:schemas-upnp-org:service:ServiceName:1",
        "serviceId": "urn:upnp-org:serviceId:ServiceName",
        "controlURL": "/ServiceName/Control",
        "eventSubURL": "/ServiceName/Event",
        "SCPDURL": "/ServiceName/scpd.xml"
      }
    }
  },
  "capabilities": {
    "total_actions": 196,
    "media_control_actions": 23,
    "volume_control_actions": 20,
    "information_actions": 51,
    "configuration_actions": 52,
    "security_actions": 1,
    "complexity_distribution": {
      "easy": 145,
      "medium": 48, 
      "complex": 3
    }
  },
  "security_assessment": {
    "risk_score": 85,
    "critical_actions": [
      {
        "action": "EditAccountPasswordX",
        "service": "SystemProperties",
        "risk_level": "CRITICAL",
        "description": "Direct password manipulation capability"
      }
    ],
    "vulnerability_indicators": [],
    "attack_surface_score": 92
  }
}
```

### 3. **Interactive Controller**
**Location**: `upnp_cli/cli/interactive.py`
**Purpose**: Real-time SOAP action execution with user guidance

#### **Controller Features:**
- **Service Browser**: Navigate through 15+ services with 196+ actions
- **Smart Prompting**: Guided parameter input based on SCPD data types
- **Search Functionality**: Find actions across all services quickly
- **Real-time Execution**: Execute SOAP actions with immediate response
- **Keyboard Shortcuts**: Efficient navigation (s=search, h=help, q=quit)

#### **Interactive Session Flow:**
```
Device Connection → Service Discovery → Action Browser → Parameter Input → SOAP Execution → Response Analysis
```

#### **Example Session:**
```bash
$ upnp-cli --host 192.168.4.152 --port 1400 interactive

🎮 Interactive UPnP Controller - Sonos Port
📊 196 actions available across 15 services

📋 Available Services:
 1. AVTransport (34 actions) 🎵
 2. RenderingControl (20 actions) 🔊  
 3. SystemProperties (1 actions) 🔒
 ...

🔍 [s]earch | [h]elp | [q]quit | Select service (1-15): 3

🔒 SystemProperties Service (1 actions):
 1. EditAccountPasswordX 🔴 Complex

Select action (1): 1

🔴 EditAccountPasswordX - Edit user account password
📝 Required Arguments:
  AccountType (string): admin
  AccountID (string): root  
  NewAccountPassword (string): [hidden]

Execute action? [y/N]: y

✅ Action executed successfully!
📤 Response: { ... }
```

### 4. **REST API Generator**
**Location**: `upnp_cli/api_generator/profile_to_api.py`
**Purpose**: Convert enhanced profiles into modern HTTP APIs

#### **API Generation Process:**
```python
1. Profile Parsing       → Load enhanced JSON profile
2. Service Analysis      → Extract action specifications
3. Endpoint Generation   → Create HTTP endpoints for each action
4. Validation Logic      → Build request validation from SCPD types
5. Documentation Gen     → Auto-generate OpenAPI specs
6. FastAPI Assembly      → Compile complete application
7. Deployment Package    → Create startup scripts and requirements
```

#### **Generated API Structure:**
```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Auto-generated from enhanced profile
app = FastAPI(
    title="Sonos Port API",
    description="Auto-generated REST API for Sonos Port UPnP control",
    version="1.0.0"
)

# Connection management
@app.post("/init")
async def initialize_device(host: str, port: int = 1400):
    """Initialize connection to UPnP device."""
    global DEVICE_HOST, DEVICE_PORT
    DEVICE_HOST = host
    DEVICE_PORT = port
    return {"status": "connected", "device": f"{host}:{port}"}

# Action endpoints (auto-generated for each UPnP action)
@app.post("/systemproperties/edit_account_password_x")
async def edit_account_password_x(request: EditAccountPasswordXRequest):
    """
    Edit user account password
    
    Complexity: 🔴 Complex
    Category: security
    Service: SystemProperties
    
    This action allows direct manipulation of device account passwords.
    Use with caution as it can permanently alter device security.
    """
    # Validate connection
    _check_device_connection()
    
    # Execute SOAP action
    result = await soap_client.call_action(
        f"http://{DEVICE_HOST}:{DEVICE_PORT}/SystemProperties/Control",
        "urn:schemas-upnp-org:service:SystemProperties:1",
        "EditAccountPasswordX",
        request.dict()
    )
    
    return {
        "status": "success",
        "action": "EditAccountPasswordX",
        "arguments": request.dict(),
        "result": result
    }

# Auto-generated request models
class EditAccountPasswordXRequest(BaseModel):
    AccountType: str
    AccountID: str  
    NewAccountPassword: str
```

#### **Generated Files:**
```
generated_apis/sonos_port/
├── sonos_port_api.py              # Main FastAPI application
├── requirements.txt               # Python dependencies  
├── start_sonos_port_api.sh        # Startup script
├── sonos_port_api_docs.md         # API documentation
└── openapi.json                   # OpenAPI specification
```

### 5. **Mass Scanner & Prioritization Engine**
**Location**: `upnp_cli/cli/commands/mass_scan.py`
**Purpose**: Network-wide analysis with intelligent target prioritization

#### **Scanning Pipeline:**
```python
1. Network Discovery     → Find all UPnP devices
2. Service Analysis      → Analyze capabilities per device
3. Vulnerability Check   → Assess security exposure
4. Priority Scoring      → Rank devices by testing value
5. Report Generation     → Create actionable intelligence
```

#### **Priority Scoring Algorithm:**
```python
def calculate_priority_score(device):
    score = 0
    
    # Protocol bonuses
    if device.has_cast_protocol():
        score += 15  # Google Cast = high value
    if device.has_samsung_wam():
        score += 12  # Samsung WAM = medium-high value
    if device.has_roku_ecp():
        score += 10  # Roku ECP = medium value
    
    # Service bonuses
    score += device.upnp_service_count * 2
    score += device.security_action_count * 10
    score += device.admin_interface_count * 8
    
    # Vulnerability indicators
    if device.has_security_actions():
        score += 20  # Critical security actions
    if device.has_exposed_admin():
        score += 15  # Exposed admin interfaces
    if device.has_media_capabilities():
        score += 5   # Media manipulation potential
    
    return min(score, 100)  # Cap at 100

# Priority classification
if score >= 20: priority = "🔴 HIGH"
elif score >= 10: priority = "🟡 MEDIUM" 
else: priority = "🟢 LOW"
```

## 📊 **Data Flow Architecture**

### **Discovery to API Pipeline:**
```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Network   │    │   Device    │    │  Enhanced   │    │    REST     │
│  Discovery  │───▶│  Profiling  │───▶│  Profiles   │───▶│     API     │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
       │                   │                   │                   │
       ▼                   ▼                   ▼                   ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ Device List │    │SCPD Analysis│    │JSON Profiles│    │FastAPI Apps │
│ Service IDs │    │Action Maps  │    │Metadata     │    │HTTP Endpoints│
│ Capabilities│    │Categories   │    │Security Info│    │Documentation│
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

### **Information Flow:**
1. **Raw Discovery Data** → Basic device and service information
2. **Enhanced Profiles** → Complete capability analysis with security context
3. **REST APIs** → Modern HTTP interfaces for security tool integration
4. **Test Results** → Vulnerability findings and exploitation evidence

## 🗂️ **File System Organization**

```
upnp-cli/
├── upnp_cli/                          # Main package
│   ├── __init__.py                    # Package initialization
│   ├── cli/                           # Command-line interface
│   │   ├── __init__.py
│   │   ├── cli.py                     # Main CLI dispatcher
│   │   ├── output.py                  # Colored output utilities
│   │   ├── interactive.py             # Interactive controller
│   │   └── commands/                  # Command implementations
│   │       ├── discovery.py           # Device discovery commands
│   │       ├── mass_scan.py           # Mass scanning operations
│   │       ├── enhanced_profiles.py   # Profile generation commands
│   │       └── security.py            # Security testing commands
│   ├── core/                          # Core UPnP functionality
│   │   ├── __init__.py
│   │   ├── discovery.py               # SSDP discovery engine
│   │   ├── soap_client.py             # SOAP action execution
│   │   ├── device.py                  # Device abstraction
│   │   └── exceptions.py              # Custom exceptions
│   ├── profile_generation/            # Enhanced profiling system
│   │   ├── __init__.py
│   │   ├── enhanced_profiler.py       # Main profiling engine
│   │   ├── scpd_analyzer.py           # SCPD parsing and analysis
│   │   └── categorization.py          # Action categorization logic
│   ├── api_generator/                 # REST API generation
│   │   ├── __init__.py
│   │   ├── profile_to_api.py          # Main API generator
│   │   ├── templates/                 # FastAPI code templates
│   │   └── validators.py              # Request validation logic
│   └── utils/                         # Utility modules
│       ├── __init__.py
│       ├── cache.py                   # Device caching
│       ├── config.py                  # Configuration management
│       └── logging_utils.py           # Logging utilities
├── docs/                              # Comprehensive documentation
│   ├── ENHANCED_PROFILES_GUIDE.md     # Profiling system guide
│   ├── API_GENERATOR_GUIDE.md         # API generation guide
│   ├── ARCHITECTURE.md                # This document
│   └── SECURITY_TESTING_GUIDE.md      # Security testing workflows
├── enhanced_profiles/                 # Generated enhanced profiles
│   ├── enhanced_profiles_TIMESTAMP.json          # Master profile file
│   └── enhanced_profiles_TIMESTAMP_individual/   # Individual profiles
│       ├── Sonos_Port_196actions.json
│       └── Samsung_TV_34actions.json
├── generated_apis/                    # Generated REST APIs
│   ├── sonos_port/                    # Sonos device API
│   │   ├── sonos_port_api.py
│   │   ├── requirements.txt
│   │   └── start_sonos_port_api.sh
│   └── samsung_tv/                    # Samsung TV API
├── profiles/                          # Legacy profile storage
├── tests/                             # Comprehensive test suite
│   ├── unit/                          # Unit tests
│   ├── integration/                   # Integration tests
│   └── e2e/                           # End-to-end tests
└── pyproject.toml                     # Project configuration
```

## 🔄 **Component Interactions**

### **Discovery → Profiling:**
```python
# Discovery Engine finds devices
devices = await discovery.discover_upnp_devices()

# Enhanced Profiler analyzes each device  
for device in devices:
    profile = await enhanced_profiler.generate_profile(device)
    profiles.append(profile)
```

### **Profiling → API Generation:**
```python
# Load enhanced profile
with open('enhanced_profiles/sonos_port.json') as f:
    profile = json.load(f)

# Generate REST API
api_generator = ProfileToAPIGenerator(profile)
api_code = await api_generator.generate_fastapi_application()
```

### **API → Security Testing:**
```python
# Start generated API
api_process = subprocess.run(['python', 'sonos_port_api.py'])

# Integrate with security tools
burp_config = {
    'target': 'http://localhost:8000',
    'proxy': 'http://127.0.0.1:8080'
}
```

## 🔧 **Extension Points**

### **Adding New Device Types:**
1. **Discovery Extension**: Add device-specific discovery patterns in `core/discovery.py`
2. **Profile Enhancement**: Extend categorization logic in `profile_generation/categorization.py`
3. **API Templates**: Create device-specific API templates in `api_generator/templates/`

### **Adding New Analysis Methods:**
1. **Analyzer Plugins**: Create new analyzer classes inheriting from `BaseAnalyzer`
2. **Categorization Rules**: Extend action categorization in `categorization.py`
3. **Security Assessments**: Add vulnerability checks in `security_analyzer.py`

### **Adding New Output Formats:**
1. **Report Generators**: Create new report formatters in `utils/reporters.py`
2. **API Formats**: Extend API generator with new framework templates
3. **Export Options**: Add new export formats for profiles and results

## 📈 **Performance Characteristics**

### **Discovery Performance:**
- **Standard Discovery**: 2-5 seconds for typical home networks
- **Aggressive Discovery**: 30-60 seconds with port scanning
- **Device Count**: Handles 50+ devices efficiently

### **Profile Generation:**
- **Single Device**: 5-15 seconds depending on service count
- **Network-wide**: 2-5 minutes for 10 devices
- **SCPD Parsing**: Concurrent analysis of all service descriptions

### **API Generation:**
- **Small Profile** (10-50 actions): < 1 second
- **Large Profile** (100-200 actions): 2-5 seconds  
- **Generated API Size**: 500-2000 lines of FastAPI code

## 🔒 **Security Design**

### **Principle of Least Privilege:**
- **No credential storage** - all actions require explicit authorization
- **Local operation only** - no external network communication
- **Controlled API exposure** - generated APIs bind to localhost by default

### **Data Protection:**
- **Sensitive data masking** in logs and output
- **Profile encryption** option for sensitive device information
- **Audit trail** of all executed actions

### **Validation & Sanitization:**
- **Input validation** based on SCPD specifications
- **SOAP envelope sanitization** prevents injection attacks
- **API request validation** using Pydantic models

## 🚀 **Deployment Architecture**

### **Development Environment:**
```bash
# Local development setup
git clone https://github.com/your-username/upnp-cli.git
cd upnp-cli
pip install -e .
upnp-cli discover
```

### **Security Testing Environment:**
```bash
# Isolated testing network
upnp-cli mass-scan --save-report
upnp-cli enhanced-profile mass --save-profiles --individual-files

# Generate APIs for discovered devices
for profile in enhanced_profiles/individual/*.json; do
    upnp-cli generate-api "$profile" --output-dir "apis/"
done

# Start APIs and integrate with security tools
cd apis/sonos_port && python sonos_port_api.py &
burp-suite-pro --proxy-config burp_upnp.json
```

### **Production Security Assessment:**
```bash
# Production-safe scanning
upnp-cli mass-scan --minimal --stealth
upnp-cli enhanced-profile mass --minimal --save-profiles

# Generate comprehensive report
upnp-cli generate-security-report enhanced_profiles/ --output assessment_report.pdf
```

This architecture provides a robust, extensible foundation for comprehensive UPnP security testing while maintaining clean separation of concerns and enabling seamless integration with modern security tools and workflows. 