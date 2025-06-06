# Next Phase Development Plan

## **Phase 6: "Prank" Routines Implementation**

### **Current Status**
- ✅ Core foundation complete (Phases 1-5, 98% test coverage)
- ✅ Device profiles and media control ready
- ✅ All prerequisites satisfied
- 🎯 Ready to implement "prank" routines as key feature

### **Implementation Strategy**

#### **6.1 HTTP Server Infrastructure**
**Priority: HIGH**
- **File:** `upnp_cli/http_server.py`
- **Purpose:** Local HTTP server to serve media files (fart.mp3, etc.)
- **Features:**
  - Threaded HTTP server on configurable port (default: 8080)
  - Serve files from current directory or specified path
  - Auto-detect local IP for URL generation
  - Graceful start/stop with status tracking
  - CORS headers for cross-origin requests

#### **6.2 Universal Fart Loop Engine**
**Priority: HIGH**
- **File:** `upnp_cli/fart_routines.py` 
- **Purpose:** Universal "fart loop" that works with ANY UPnP MediaRenderer
- **Features:**
  - Auto-detect device capabilities using profiles
  - Device-specific protocol selection (UPnP/SOAP, ECP, WAM, Cast)
  - Fallback chain: Specific → Generic UPnP → Manual loop
  - Background thread for manual loop maintenance
  - Proper cleanup and reset functionality

#### **6.3 Device-Specific Implementations**
**Priority: MEDIUM**
- **Sonos:** Queue-based repeat using existing media_control
- **Roku:** ECP launch + media injection
- **Samsung:** WAM API URL playback
- **LG/Sony:** DLNA with proper DIDL metadata
- **Generic UPnP:** Standard SetAVTransportURI + repeat detection

#### **6.4 Mass Attack Coordinator**
**Priority: MEDIUM**
- **File:** `upnp_cli/mass_attack.py`
- **Purpose:** Parallel mass "fart" deployment across all discovered devices
- **Features:**
  - Parallel execution using asyncio/ThreadPoolExecutor
  - Live progress reporting with device status
  - Success/failure tracking and reporting
  - Graceful error handling and cleanup
  - Attack summary with statistics

### **Phase 7: CLI Interface Implementation**

#### **7.1 Main CLI Framework**
**Priority: HIGH**
- **File:** `upnp_cli/cli.py`
- **Purpose:** Complete command-line interface
- **Features:**
  - Comprehensive argument parsing with subcommands
  - Global options: `--host`, `--port`, `--cache`, `--verbose`, `--stealth`
  - Colored output and progress indicators
  - JSON output option for scripting

#### **7.2 Discovery Commands**
```bash
upnp-cli discover [--cache] [--network CIDR]
upnp-cli scan-network [--ports LIST] [--cache]
upnp-cli info --host IP [--port PORT]
upnp-cli services --host IP [--port PORT]
```

#### **7.3 Media Control Commands**
```bash
upnp-cli play --host IP [--port PORT]
upnp-cli pause --host IP [--port PORT]  
upnp-cli stop --host IP [--port PORT]
upnp-cli volume get|set LEVEL --host IP [--port PORT]
upnp-cli queue list|add|clear --host IP [--port PORT]
```

#### **7.4 "Prank" Commands**
```bash
upnp-cli start-server [--port PORT] [--path DIR]
upnp-cli stop-server
upnp-cli fart-loop --host IP [--volume LEVEL] [--server-port PORT]
upnp-cli stop-fart-loop --host IP [--port PORT]
upnp-cli mass-fart-attack [--cache] [--volume LEVEL]
```

#### **7.5 Security Scanning Commands**
```bash
upnp-cli ssl-scan --host IP [--port PORT]
upnp-cli rtsp-scan --host IP [--port PORT]
upnp-cli security-report --host IP [--output FILE]
```

### **Implementation Timeline**

#### **Week 1: Core Infrastructure**
- [x] HTTP Server implementation
- [x] Basic fart loop for UPnP devices
- [x] Integration with existing media_control
- [x] Unit tests for new modules

#### **Week 2: Device-Specific Implementations**
- [x] Sonos queue-based fart loop
- [x] Roku ECP fart injection
- [x] Samsung WAM fart playback
- [x] Generic UPnP fallbacks
- [x] Manual loop thread management

#### **Week 3: Mass Attack & CLI Foundation**
- [ ] Mass attack coordinator
- [ ] CLI framework and argument parsing
- [ ] Discovery and info subcommands
- [ ] Basic media control subcommands

#### **Week 4: CLI Completion & Polish**
- [ ] Fart routine subcommands
- [ ] Security scanning subcommands
- [ ] Progress indicators and colored output
- [ ] Documentation and examples

### **Technical Architecture**

#### **Module Dependencies**
```
cli.py
├── discovery.py (device finding)
├── profiles.py (device matching)
├── media_control.py (universal control)
├── fart_routines.py (prank implementation)
├── mass_attack.py (parallel coordination)
├── http_server.py (media serving)
└── ssl_rtsp_scan.py (security scanning)
```

#### **Data Flow**
```
1. Discovery → Device List
2. Profile Matching → Protocol Selection
3. Media Control → Device-Specific Commands
4. HTTP Server → Media URL Generation
5. Fart Routines → Coordinated Attack
6. Mass Attack → Parallel Execution
```

### **Quality Assurance**

#### **Testing Strategy**
- Unit tests for all new modules
- Integration tests with mock devices
- Real device testing for validation
- Performance testing for mass attacks
- Security testing for ethical use

#### **Documentation**
- API documentation for all modules
- CLI usage examples and tutorials
- Troubleshooting guide for common issues
- Ethical use guidelines and warnings

### **Success Criteria**

#### **Phase 6 Complete When:**
- ✅ HTTP server starts/stops reliably
- ✅ Universal fart loop works on 5+ device types
- ✅ Mass attack deploys to 10+ devices in parallel
- ✅ All device-specific protocols implemented
- ✅ Proper cleanup and error handling

#### **Phase 7 Complete When:**
- ✅ CLI supports all major operations
- ✅ Comprehensive help and usage examples
- ✅ Colored output and progress indicators
- ✅ JSON output for scripting
- ✅ Full integration with existing modules

This plan leverages our solid foundation to deliver the core "prank" functionality while building a professional CLI interface. The modular design ensures each component can be developed and tested independently. 