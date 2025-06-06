# UPnP CLI: The Ultimate UPnP Penetration Testing Toolkit

## 🎯 **What Is This?**

**UPnP CLI** is the most comprehensive UPnP (Universal Plug and Play) security analysis toolkit available. It transforms the complex world of UPnP device testing into accessible, automated penetration testing workflows.

### **The Complete UPnP Security Pipeline:**
```
Network Discovery → Enhanced Profiles → REST APIs → Security Testing
      ↓                    ↓              ↓             ↓
   Find Devices    →  Analyze Actions  →  HTTP Endpoints → Burp/ZAP/Scripts
```

## 🚀 **Why UPnP CLI?**

### **The Problem: UPnP Security Gap**
- **UPnP is everywhere**: Smart TVs, speakers, routers, IoT devices
- **Legacy protocol**: Complex SOAP/XML from the 1990s  
- **Tool incompatibility**: Modern security tools don't understand UPnP
- **Manual analysis**: Tedious SCPD parsing and SOAP crafting
- **Hidden attack surface**: Devices have hundreds of undiscovered actions

### **Our Solution: Complete Automation**
- ✅ **Automated Discovery**: Find all UPnP devices and services instantly
- ✅ **Enhanced Profiling**: Extract every available action with complete specifications
- ✅ **REST API Generation**: Convert SOAP actions to modern HTTP endpoints
- ✅ **Security Tool Integration**: Works with Burp Suite, OWASP ZAP, scripting
- ✅ **Penetration Testing Focus**: Built specifically for security professionals

## 🎯 **Core Value Propositions**

### 1. **Complete Attack Surface Discovery**
Transform this painful manual process:
```bash
# Traditional approach (hours of work)
ssdp-scan                    # Find devices manually
wget device_description.xml  # Download descriptions
cat *.xml | grep -i scpd    # Extract SCPD URLs manually  
wget scpd_urls...           # Download SCPD documents
xml-parse scpd/*.xml        # Parse action specifications manually
craft-soap-envelope.py      # Hand-craft SOAP requests
```

Into this single command:
```bash
# UPnP CLI approach (minutes)
upnp-cli enhanced-profile mass --save-profiles --individual-files

# Result: Complete analysis of ALL devices with:
# - 196 actions discovered on Sonos device
# - 1 critical security action (EditAccountPasswordX)
# - Complete argument specifications
# - Action categorization and complexity assessment
```

### 2. **Modern Security Tool Integration**
Transform this incompatible workflow:
```xml
<!-- Traditional SOAP (unusable in modern tools) -->
<?xml version="1.0" encoding="utf-8"?>
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
  <s:Body>
    <u:EditAccountPasswordX xmlns:u="urn:schemas-upnp-org:service:SystemProperties:1">
      <AccountType>admin</AccountType>
      <NewAccountPassword>backdoor</NewAccountPassword>
    </u:EditAccountPasswordX>
  </s:Body>
</s:Envelope>
```

Into this modern REST API:
```bash
# Generated REST API (works with all modern tools)
curl -X POST "http://localhost:8000/systemproperties/edit_account_password_x" \
  -H "Content-Type: application/json" \
  -d '{"AccountType": "admin", "NewAccountPassword": "backdoor"}'

# ✅ Works in Burp Suite
# ✅ Works in OWASP ZAP  
# ✅ Works in Python scripts
# ✅ Works in Postman
```

### 3. **Penetration Testing Efficiency**
**Before UPnP CLI**: Days of manual work per device
**With UPnP CLI**: Minutes to analyze entire networks

## 🔧 **System Components**

### **1. Enhanced Profile Generator**
**Purpose**: Extract complete device capabilities with SCPD analysis

```bash
upnp-cli enhanced-profile mass --save-profiles --individual-files
```

**What it discovers**:
- **All available actions** (often 100-200+ per device)
- **Complete argument specifications** with data types
- **Security-critical actions** automatically identified
- **Action complexity ratings** (🟢 Easy, 🟡 Medium, 🔴 Complex)
- **Service categorization** (media, volume, security, configuration)

**Output**: Comprehensive JSON profiles with complete attack surface maps

### **2. Interactive Controller** 
**Purpose**: Execute any discovered UPnP action with guided parameter input

```bash
upnp-cli --host 192.168.1.100 --port 1400 interactive
```

**Features**:
- **Service/action browser** with 196 actions on typical Sonos device
- **Smart argument prompting** based on SCPD data types
- **Search functionality** across all services and actions
- **Real-time SOAP execution** with response parsing
- **Keyboard shortcuts** for efficient navigation

### **3. REST API Generator**
**Purpose**: Convert enhanced profiles into modern HTTP APIs

```python
# Generate from enhanced profile (demo implementation working)
from upnp_cli.api_generator.profile_to_api import generate_profile_api

# Creates FastAPI application with:
# - HTTP endpoint for every UPnP action
# - Interactive documentation at /docs
# - Request validation and error handling
# - Integration with modern security tools
```

**Result**: Working REST APIs that enable:
- **Burp Suite integration** for request interception/modification
- **OWASP ZAP scanning** with automatic endpoint discovery  
- **Python scripting** with simple `requests` library calls
- **Postman collections** for team collaboration

### **4. Mass Scanner & Prioritization**
**Purpose**: Automatically analyze entire networks and prioritize targets

```bash
upnp-cli mass-scan --save-report
```

**Intelligence provided**:
- **Priority scoring** (High ≥20, Medium ≥10, Low ≥1 points)
- **Protocol ranking** (Cast, Samsung WAM, Roku ECP, UPnP)
- **Security assessment** with vulnerability indicators
- **Target recommendations** for focused penetration testing

## 🎯 **Real-World Penetration Testing Scenarios**

### **Scenario 1: Corporate Network Assessment**
```bash
# 1. Discover all UPnP devices
upnp-cli mass-scan --save-report

# 2. Generate enhanced profiles for high-priority targets  
upnp-cli enhanced-profile mass --save-profiles --individual-files

# 3. Generate REST APIs for discovered devices
# (Command implementation in progress)

# 4. Integrate with Burp Suite for comprehensive testing
# Start generated APIs and proxy through Burp
```

### **Scenario 2: IoT Device Security Assessment**
```bash
# Target: Smart TV with 34 discovered actions
upnp-cli --host 192.168.1.150 --port 8080 interactive

# Interactive exploration reveals:
# - Remote control simulation capabilities (IRCC service)
# - Channel/input manipulation actions  
# - Network configuration modifications
# - Potential for unauthorized device control
```

### **Scenario 3: Home Network Penetration Test**
```bash
# Target: Sonos speaker with 196 actions discovered
upnp-cli enhanced-profile single --host 192.168.1.100 --save-profile

# Profile analysis reveals:
# - 1 critical security action: EditAccountPasswordX
# - 23 media control actions (service disruption)
# - 52 configuration actions (persistence opportunities)
# - Complete argument specifications for exploitation
```

## 📋 **Command Reference**

### **Discovery & Analysis**
```bash
# Find all UPnP devices with prioritization
upnp-cli mass-scan --save-report

# Enhanced profile generation (recommended)
upnp-cli enhanced-profile mass --save-profiles --individual-files

# Single device analysis
upnp-cli enhanced-profile single --host IP --save-profile
```

### **Interactive Control**  
```bash
# Full interactive control (196 actions on Sonos)
upnp-cli --host IP --port PORT interactive

# Quick device information
upnp-cli --host IP info

# Media control shortcuts
upnp-cli --host IP play
upnp-cli --host IP pause
upnp-cli --host IP set-volume 50
```

### **Security Testing**
```bash
# Security-focused scanning
upnp-cli --host IP security-scan

# Service enumeration with vulnerability assessment
upnp-cli --host IP enum-services --check-vulns

# Generate device profile for API creation
upnp-cli enhanced-profile single --host IP --save-profile profiles/target.json
```

## 🔍 **Discovery Results Example**

### **Sonos Port Analysis**
```json
{
  "device": "Sonos Port", 
  "total_actions": 196,
  "services": 15,
  "security_actions": 1,
  "critical_findings": [
    {
      "action": "EditAccountPasswordX",
      "service": "SystemProperties", 
      "risk": "🔴 CRITICAL - Direct password manipulation",
      "arguments": ["AccountType", "AccountID", "NewAccountPassword"]
    }
  ],
  "categories": {
    "media_control": 23,
    "volume_control": 20, 
    "information": 51,
    "configuration": 52,
    "security": 1
  }
}
```

## 🚀 **Getting Started**

### **Installation**
```bash
# Clone and install
git clone https://github.com/your-username/upnp-cli.git
cd upnp-cli
pip install -e .

# Verify installation
upnp-cli --help
```

### **Quick Start Workflow**
```bash
# 1. Network discovery
upnp-cli mass-scan

# 2. Enhanced analysis of interesting targets
upnp-cli enhanced-profile mass --save-profiles --individual-files

# 3. Interactive exploration of high-value devices
upnp-cli --host 192.168.1.100 --port 1400 interactive

# 4. Generate profiles for API creation
# Enhanced profiles are automatically saved for API generation
```

## 📁 **Project Structure**

```
upnp-cli/
├── upnp_cli/
│   ├── cli/                    # Command-line interface
│   ├── profile_generation/     # Enhanced profiling system
│   ├── api_generator/          # REST API generation
│   ├── routines/               # Automated testing workflows
│   └── core/                   # Core UPnP functionality
├── docs/
│   ├── ENHANCED_PROFILES_GUIDE.md    # Complete profiling documentation
│   ├── API_GENERATOR_GUIDE.md        # REST API generation guide
│   └── SECURITY_TESTING_GUIDE.md     # Penetration testing workflows
├── profiles/                   # Device profile storage
├── enhanced_profiles/          # Enhanced SCPD analysis results
├── generated_apis/             # Generated REST APIs
└── tests/                      # Comprehensive test suite
```

## 🎯 **Target Use Cases**

### **For Penetration Testers**
- **Corporate network assessments** with UPnP device discovery
- **IoT security testing** with comprehensive action analysis
- **Red team operations** using modern tool integration
- **Vulnerability research** with complete protocol coverage

### **For Security Researchers**  
- **Protocol analysis** with automated SCPD parsing
- **Device fingerprinting** with enhanced profiling
- **Exploit development** using REST API interfaces
- **Vulnerability disclosure** with detailed capability mapping

### **For Network Administrators**
- **Asset discovery** of all UPnP-enabled devices
- **Security assessment** of IoT device exposure
- **Compliance validation** with comprehensive auditing
- **Risk evaluation** using automated prioritization

## ⚠️ **Security & Legal Considerations**

### **Responsible Usage**
- ✅ **Only test devices you own** or have explicit permission to assess
- ✅ **Use isolated test networks** to prevent service disruption
- ✅ **Follow responsible disclosure** for discovered vulnerabilities
- ✅ **Document all testing activities** for audit compliance

### **Security Features**
- **No credential storage** - all actions require explicit authorization
- **Local operation** - no data transmitted to external services  
- **Controlled access** - APIs generated for localhost only by default
- **Audit logging** - comprehensive activity tracking

## 🚀 **Advanced Features**

### **Automation & Scripting**
```python
# Python integration example
from upnp_cli import UPnPClient

client = UPnPClient()
devices = client.discover_all()

for device in devices:
    profile = client.generate_enhanced_profile(device)
    if profile.has_security_actions():
        print(f"🔴 High-value target: {device.name}")
        api = client.generate_api(profile)
        api.start(port=8000 + device.id)
```

### **Integration Examples**
```bash
# Burp Suite integration
generated_api --host localhost --port 8000 &
burp-proxy-config --target http://localhost:8000

# OWASP ZAP integration  
zap-api-import --openapi http://localhost:8000/docs/openapi.json
zap-active-scan --target http://localhost:8000

# Metasploit integration
use auxiliary/scanner/upnp/upnp_cli_import
set PROFILE_FILE enhanced_profiles/target_device.json
run
```

## 📚 **Documentation**

- **[Enhanced Profiles Guide](docs/ENHANCED_PROFILES_GUIDE.md)** - Complete profiling system documentation
- **[API Generator Guide](docs/API_GENERATOR_GUIDE.md)** - REST API generation and usage  
- **[Security Testing Guide](docs/SECURITY_TESTING_GUIDE.md)** - Penetration testing workflows
- **[Command Reference](docs/COMMAND_REFERENCE.md)** - Complete CLI documentation

## 🤝 **Contributing**

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📄 **License**

This project is licensed under the MIT License - see [LICENSE](LICENSE) for details.

---

**UPnP CLI: Bridging the gap between legacy IoT protocols and modern penetration testing.** 