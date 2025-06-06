#!/usr/bin/env python3
"""
Enhanced Interactive Controller

Improved version of the interactive SOAP controller with better UX,
navigation, input validation, and user guidance.
"""

import asyncio
import logging
import json
from typing import Dict, List, Any, Optional, Tuple
from urllib.parse import urljoin

import upnp_cli.discovery as discovery
import upnp_cli.soap_client as soap_client
from upnp_cli.profile_generation.scpd_parser import parse_device_scpds, EnhancedSCPDParser
from upnp_cli.cli.output import ColoredOutput, ProgressReporter
from upnp_cli.cli.ux_improvements import (
    InteractiveInput, NavigationHelper, ProgressTracker, SmartHelp
)

logger = logging.getLogger(__name__)


class EnhancedInteractiveController:
    """Enhanced interactive SOAP controller with improved UX."""
    
    def __init__(self, host: str, port: int = 1400, use_ssl: bool = False):
        self.host = host
        self.port = port
        self.use_ssl = use_ssl
        self.device_info = None
        self.scpd_documents = []
        self.available_actions = {}
        self.soap_client = soap_client.get_soap_client()
        
        # UX enhancement components
        self.input_handler = InteractiveInput()
        self.navigator = NavigationHelper()
        self.recent_actions = []  # Track recent actions for quick access
        self.bookmarks = {}  # Allow users to bookmark frequently used actions
        
    async def initialize(self) -> bool:
        """Initialize with enhanced progress tracking."""
        progress = ProgressTracker(6, f"Device Analysis: {self.host}:{self.port}")
        progress.start()
        
        try:
            # Step 1: Device discovery
            progress.update("Device Discovery", f"Connecting to {self.host}:{self.port}")
            device_url = await self._find_device_description()
            if not device_url:
                progress.finish(False, "Could not find device description")
                return False
            
            # Step 2: Parse device description
            progress.update("Device Description", f"Parsing {device_url}")
            import aiohttp
            async with aiohttp.ClientSession() as session:
                self.device_info = await discovery.fetch_device_description(session, device_url)
            
            if not self.device_info:
                progress.finish(False, "Failed to parse device description")
                return False
                
            # Step 3: Enumerate services
            progress.update("Service Enumeration", "Discovering device services")
            services = self._collect_all_services()
            
            # Step 4: Parse SCPD documents
            progress.update("SCPD Analysis", f"Parsing {len(services)} service descriptions")
            base_url = device_url.rsplit('/', 1)[0]
            self.scpd_documents = await parse_device_scpds(self.device_info, base_url)
            
            # Step 5: Action discovery
            progress.update("Action Discovery", "Mapping available SOAP actions")
            self._organize_actions_by_service(services)
            
            # Step 6: Validation
            total_actions = sum(len(info['actions']) for info in self.available_actions.values())
            progress.update("Validation", f"Discovered {total_actions} total actions")
            
            if total_actions == 0:
                progress.finish(False, "No executable actions found")
                return False
                
            progress.finish(True, f"Ready for interactive control - {len(self.available_actions)} services, {total_actions} actions")
            return True
            
        except Exception as e:
            progress.finish(False, f"Initialization error: {e}")
            logger.exception("Enhanced controller initialization error")
            return False
    
    async def _find_device_description(self) -> Optional[str]:
        """Find device description with multiple fallback paths."""
        common_paths = [
            "/xml/device_description.xml",
            "/description.xml", 
            "/MediaServer/rendererdevicedesc.xml",
            "/upnp/desc.xml",
            "/device_description.xml",
            "/rootDesc.xml",
            "/root.xml"
        ]
        
        protocol = "https" if self.use_ssl else "http"
        
        for path in common_paths:
            try:
                test_url = f"{protocol}://{self.host}:{self.port}{path}"
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.get(test_url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                        if resp.status == 200:
                            return test_url
            except:
                continue
        
        return None
    
    def _collect_all_services(self) -> List[Dict[str, Any]]:
        """Collect services from main device and embedded devices."""
        services = self.device_info.get('services', [])
        
        # Also check embedded devices
        embedded_devices = self.device_info.get('devices', [])
        for embedded_device in embedded_devices:
            embedded_services = embedded_device.get('services', [])
            services.extend(embedded_services)
        
        return services
    
    def _organize_actions_by_service(self, services: List[Dict[str, Any]]):
        """Organize actions by service with control URLs."""
        for doc in self.scpd_documents:
            if doc.parsing_success and doc.actions:
                service_name = doc.service_type.split(':')[-2] if ':' in doc.service_type else doc.service_type
                self.available_actions[service_name] = {
                    'service_type': doc.service_type,
                    'control_url': None,
                    'actions': doc.actions,
                    'scpd_doc': doc,
                    'action_count': len(doc.actions)
                }
                
                # Find control URL
                for service in services:
                    if service.get('serviceType') == doc.service_type:
                        control_url = service.get('controlURL', '')
                        if control_url and not control_url.startswith('http'):
                            # Make absolute URL
                            base_url = f"http{'s' if self.use_ssl else ''}://{self.host}:{self.port}"
                            control_url = urljoin(base_url + '/', control_url)
                        self.available_actions[service_name]['control_url'] = control_url
                        break
    
    def display_main_dashboard(self):
        """Display enhanced main dashboard with device info and quick actions."""
        ColoredOutput.header(f"🎮 Interactive Control Dashboard")
        
        # Device summary
        device_name = self.device_info.get('friendlyName', 'Unknown Device')
        manufacturer = self.device_info.get('manufacturer', 'Unknown')
        model = self.device_info.get('modelName', 'Unknown')
        
        ColoredOutput.print(f"📱 Device: {device_name}", 'cyan', bold=True)
        ColoredOutput.print(f"🏢 Manufacturer: {manufacturer}", 'white')
        ColoredOutput.print(f"📦 Model: {model}", 'white')
        ColoredOutput.print(f"🌐 Address: {self.host}:{self.port}", 'white')
        
        # Services summary
        total_actions = sum(info['action_count'] for info in self.available_actions.values())
        ColoredOutput.print(f"⚙️  Services: {len(self.available_actions)}", 'white')
        ColoredOutput.print(f"🎯 Total Actions: {total_actions}", 'white')
        
        # Quick actions (most common UPnP actions)
        self._show_quick_actions()
        
        # Recent actions
        if self.recent_actions:
            ColoredOutput.print(f"\n🕒 Recent Actions:", 'cyan', bold=True)
            for i, action in enumerate(self.recent_actions[-3:], 1):
                ColoredOutput.print(f"  {i}. {action['service']}.{action['action']}", 'yellow')
        
        self.navigator.show_shortcuts()
    
    def _show_quick_actions(self):
        """Display common UPnP actions for quick access."""
        quick_actions = [
            ('GetProtocolInfo', 'Get supported protocols'),
            ('GetCurrentConnectionInfo', 'Get connection status'),
            ('GetDeviceCapabilities', 'Get device capabilities'),
            ('GetSystemUpdateID', 'Get system update ID'),
            ('Browse', 'Browse content directory')
        ]
        
        ColoredOutput.print(f"\n⚡ Quick Actions:", 'cyan', bold=True)
        available_quick = []
        
        for action_name, description in quick_actions:
            for service_name, service_info in self.available_actions.items():
                if action_name in service_info['actions']:
                    available_quick.append((len(available_quick) + 1, service_name, action_name, description))
                    break
        
        if available_quick:
            for idx, service_name, action_name, description in available_quick:
                ColoredOutput.print(f"  {idx}. {action_name} - {description}", 'yellow')
        else:
            ColoredOutput.print("  No quick actions available", 'gray')
        
        return available_quick
    
    def display_enhanced_services_menu(self):
        """Display services menu with enhanced information."""
        ColoredOutput.header("🎮 Available Services")
        self.navigator.show_breadcrumb()
        
        services = list(self.available_actions.keys())
        
        for i, service_name in enumerate(services, 1):
            service_info = self.available_actions[service_name]
            action_count = service_info['action_count']
            has_control = "✅" if service_info['control_url'] else "❌"
            
            # Highlight services with many actions
            color = 'cyan' if action_count > 10 else 'white'
            weight = True if action_count > 15 else False
            
            ColoredOutput.print(f"  {i}. {service_name}", color, bold=weight)
            ColoredOutput.print(f"     📊 Actions: {action_count} | 🎯 Control: {has_control}", 'white')
            
            # Show service type for clarity
            service_type = service_info['service_type'].split(':')[-2] if ':' in service_info['service_type'] else 'Unknown'
            ColoredOutput.print(f"     📋 Type: {service_type}", 'gray')
        
        ColoredOutput.print(f"\n  s. 🔍 Search actions across all services", 'magenta')
        ColoredOutput.print(f"  b. 📑 Show bookmarks", 'magenta')
        ColoredOutput.print(f"  0. ⬅️  Back to dashboard", 'red')
        
        return services
    
    def display_enhanced_actions_menu(self, service_name: str):
        """Display actions menu with search and filtering."""
        service_info = self.available_actions[service_name]
        actions = list(service_info['actions'].values())
        
        ColoredOutput.header(f"🎯 Actions for {service_name}")
        self.navigator.show_breadcrumb()
        
        ColoredOutput.print(f"📊 Total Actions: {len(actions)}", 'cyan')
        
        # Show actions with enhanced info
        for i, action in enumerate(actions, 1):
            args_in = len(action.arguments_in)
            args_out = len(action.arguments_out)
            
            # Color code by complexity
            if args_in == 0:
                color = 'green'  # Easy - no input required
            elif args_in <= 2:
                color = 'yellow'  # Medium
            else:
                color = 'red'  # Complex
            
            ColoredOutput.print(f"  {i}. {action.name}", color, bold=True)
            ColoredOutput.print(f"     📥 Input: {args_in} | 📤 Output: {args_out}", 'white')
            
            # Show input arguments preview
            if action.arguments_in:
                arg_preview = ", ".join([arg.name for arg in action.arguments_in[:3]])
                if len(action.arguments_in) > 3:
                    arg_preview += "..."
                ColoredOutput.print(f"     🔧 Args: {arg_preview}", 'gray')
        
        ColoredOutput.print(f"\n  f. 🔍 Filter actions", 'magenta')
        ColoredOutput.print(f"  s. 🔎 Search action by name", 'magenta')
        ColoredOutput.print(f"  0. ⬅️  Back to services", 'red')
        
        return actions
    
    async def enhanced_execute_action(self, service_name: str, action) -> Dict[str, Any]:
        """Execute action with enhanced input validation and guidance."""
        ColoredOutput.header(f"🚀 Action Execution: {action.name}")
        
        service_info = self.available_actions[service_name]
        control_url = service_info['control_url']
        
        if not control_url:
            return {"status": "error", "message": "No control URL available"}
        
        # Show action details
        ColoredOutput.print(f"🎯 Action: {action.name}", 'cyan', bold=True)
        ColoredOutput.print(f"⚙️  Service: {service_name}", 'white')
        ColoredOutput.print(f"🌐 URL: {control_url}", 'white')
        
        # Enhanced argument collection with smart defaults and validation
        arguments = {}
        if action.arguments_in:
            ColoredOutput.print(f"\n📝 Input Arguments ({len(action.arguments_in)}):", 'yellow', bold=True)
            
            arguments = await self._collect_arguments_enhanced(action, service_info)
            if arguments is None:  # User cancelled
                return {"status": "cancelled", "message": "User cancelled input"}
        
        # Show execution preview
        ColoredOutput.print(f"\n🎯 Execution Preview:", 'green', bold=True)
        ColoredOutput.print(f"Action: {action.name}", 'white')
        ColoredOutput.print(f"Service: {service_info['service_type']}", 'white')
        
        if arguments:
            ColoredOutput.print(f"Arguments ({len(arguments)}):", 'white')
            for arg_name, arg_value in arguments.items():
                ColoredOutput.print(f"  • {arg_name}: {arg_value}", 'cyan')
        else:
            ColoredOutput.print(f"Arguments: None", 'white')
        
        # Enhanced confirmation with options
        ColoredOutput.print(f"\n🚀 Ready to execute?", 'yellow', bold=True)
        ColoredOutput.print(f"  y/yes - Execute action", 'green')
        ColoredOutput.print(f"  d/dry  - Dry run (show request only)", 'yellow')
        ColoredOutput.print(f"  e/edit - Edit arguments", 'blue')
        ColoredOutput.print(f"  c/cancel - Cancel", 'red')
        
        choice = self.input_handler.get_input("Choice [y/d/e/c]: ").lower()
        
        if choice in ['c', 'cancel']:
            return {"status": "cancelled", "message": "User cancelled execution"}
        elif choice in ['e', 'edit']:
            # Re-collect arguments
            arguments = await self._collect_arguments_enhanced(action, service_info)
            if arguments is None:
                return {"status": "cancelled", "message": "User cancelled input"}
        elif choice in ['d', 'dry']:
            # Show what would be sent
            ColoredOutput.info("🧪 DRY RUN - SOAP request that would be sent:")
            # Here you could show the actual SOAP envelope
            ColoredOutput.print(f"POST {control_url}", 'yellow')
            ColoredOutput.print(f"Action: {action.name}", 'yellow')
            ColoredOutput.print(f"Arguments: {arguments}", 'yellow')
            return {"status": "dry_run", "action": action.name, "arguments": arguments}
        
        # Execute with progress indication
        try:
            ColoredOutput.info(f"⚡ Sending SOAP request to {control_url}...")
            
            result = await self.soap_client.execute_soap_action(
                control_url=control_url,
                service_type=service_info['service_type'],
                action_name=action.name,
                arguments=arguments
            )
            
            # Track this action for recent history
            self.recent_actions.append({
                'service': service_name,
                'action': action.name,
                'arguments': arguments
            })
            if len(self.recent_actions) > 10:
                self.recent_actions.pop(0)
            
            return await self._process_action_result(result, action, arguments)
            
        except Exception as e:
            ColoredOutput.error(f"❌ Action execution failed: {e}")
            return {"status": "error", "action": action.name, "error": str(e)}
    
    async def _collect_arguments_enhanced(self, action, service_info) -> Optional[Dict[str, Any]]:
        """Enhanced argument collection with smart defaults and validation."""
        arguments = {}
        
        for arg in action.arguments_in:
            # Get state variable info for smart defaults
            state_var_info = self._get_state_variable_info(arg, service_info)
            
            # Display argument info
            ColoredOutput.print(f"\n📋 Argument: {arg.name}", 'cyan', bold=True)
            ColoredOutput.print(f"   Type: {arg.data_type or 'unknown'}", 'white')
            
            if state_var_info:
                if state_var_info.get('allowed_values'):
                    ColoredOutput.print(f"   Allowed: {', '.join(state_var_info['allowed_values'])}", 'white')
                if state_var_info.get('range'):
                    ColoredOutput.print(f"   Range: {state_var_info['range']}", 'white')
            
            # Smart default suggestion
            suggested_default = self._get_smart_default(arg, state_var_info)
            
            # Create prompt with suggestions
            prompt = f"   Enter {arg.name}"
            suggestions = state_var_info.get('allowed_values', []) if state_var_info else []
            
            if suggested_default:
                prompt += f" (default: {suggested_default})"
            prompt += ": "
            
            # Validator function
            validator = self._create_validator(arg, state_var_info) if state_var_info else None
            
            try:
                value = self.input_handler.get_input(prompt, suggestions, validator)
                
                if not value and suggested_default:
                    value = suggested_default
                
                arguments[arg.name] = value
                
            except KeyboardInterrupt:
                ColoredOutput.warning("\n⚠️  Argument collection cancelled")
                return None
        
        return arguments
    
    def _get_state_variable_info(self, arg, service_info) -> Optional[Dict[str, Any]]:
        """Get enhanced state variable information for an argument."""
        if not arg.related_state_variable:
            return None
        
        state_vars = service_info['scpd_doc'].state_variables
        if arg.related_state_variable not in state_vars:
            return None
        
        state_var = state_vars[arg.related_state_variable]
        
        info = {
            'default_value': state_var.default_value,
            'allowed_values': state_var.allowed_values,
            'data_type': state_var.data_type
        }
        
        if state_var.minimum is not None and state_var.maximum is not None:
            info['range'] = f"{state_var.minimum} - {state_var.maximum}"
        
        return info
    
    def _get_smart_default(self, arg, state_var_info) -> Optional[str]:
        """Generate smart default values for common UPnP arguments."""
        if state_var_info and state_var_info.get('default_value'):
            return state_var_info['default_value']
        
        # Common UPnP argument defaults
        smart_defaults = {
            'InstanceID': '0',
            'ObjectID': '0',
            'ContainerID': '0',
            'Speed': '1',
            'StartingIndex': '0',
            'RequestedCount': '0',
            'SortCriteria': '',
            'Filter': '*',
            'BrowseFlag': 'BrowseDirectChildren'
        }
        
        default = smart_defaults.get(arg.name)
        if default and state_var_info and state_var_info.get('allowed_values'):
            # Verify default is in allowed values
            if default in state_var_info['allowed_values']:
                return default
            # Return first allowed value as fallback
            return state_var_info['allowed_values'][0] if state_var_info['allowed_values'] else None
        
        return default
    
    def _create_validator(self, arg, state_var_info) -> Optional[callable]:
        """Create a validator function for argument input."""
        def validator(value: str) -> bool:
            if not value:  # Allow empty for optional args
                return True
            
            # Check allowed values
            allowed_values = state_var_info.get('allowed_values')
            if allowed_values and value not in allowed_values:
                ColoredOutput.warning(f"⚠️  '{value}' not in allowed values: {', '.join(allowed_values)}")
                return False
            
            # Check numeric ranges
            if 'range' in state_var_info and state_var_info['range']:
                try:
                    numeric_value = float(value)
                    # Extract range (format: "min - max")
                    range_parts = state_var_info['range'].split(' - ')
                    if len(range_parts) == 2:
                        min_val, max_val = float(range_parts[0]), float(range_parts[1])
                        if not (min_val <= numeric_value <= max_val):
                            ColoredOutput.warning(f"⚠️  Value must be between {min_val} and {max_val}")
                            return False
                except ValueError:
                    pass  # Not numeric, skip range check
            
            return True
        
        return validator
    
    async def _process_action_result(self, result, action, arguments) -> Dict[str, Any]:
        """Process and display action results with enhanced formatting."""
        ColoredOutput.success(f"✅ Action '{action.name}' executed successfully!")
        
        # Display response status
        status_code = getattr(result, 'status', getattr(result, 'status_code', 'unknown'))
        ColoredOutput.print(f"📊 HTTP Status: {status_code}", 'cyan')
        
        # Parse response
        if hasattr(result, 'text'):
            response_text = result.text() if callable(result.text) else result.text
            parsed_response = self.soap_client.parse_soap_response(result, response_text, verbose=True)
            
            # Display parsed response with formatting
            if parsed_response:
                ColoredOutput.print(f"\n📋 Response Data:", 'green', bold=True)
                self._display_response_data(parsed_response)
            
            # Show raw response option
            ColoredOutput.print(f"\n🔍 View raw response? (y/N): ", 'gray', end='')
            if input().strip().lower() in ['y', 'yes']:
                ColoredOutput.print(f"\n📄 Raw Response:", 'cyan', bold=True)
                ColoredOutput.print(f"{response_text[:1000]}{'...' if len(response_text) > 1000 else ''}", 'gray')
            
            return {
                "status": "success",
                "action": action.name,
                "arguments": arguments,
                "parsed_response": parsed_response,
                "raw_response": response_text[:1000]
            }
        
        return {"status": "success", "action": action.name, "arguments": arguments}
    
    def _display_response_data(self, data, indent: int = 0):
        """Recursively display response data with proper formatting."""
        prefix = "  " * indent
        
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    ColoredOutput.print(f"{prefix}{key}:", 'yellow', bold=True)
                    self._display_response_data(value, indent + 1)
                else:
                    ColoredOutput.print(f"{prefix}{key}: {value}", 'white')
        elif isinstance(data, list):
            for i, item in enumerate(data):
                ColoredOutput.print(f"{prefix}[{i}]:", 'yellow', bold=True)
                self._display_response_data(item, indent + 1)
        else:
            ColoredOutput.print(f"{prefix}{data}", 'white')
    
    async def run_enhanced_session(self):
        """Run the enhanced interactive session with improved navigation."""
        ColoredOutput.header("🎮 Enhanced Interactive SOAP Controller")
        
        self.navigator.push_location("Dashboard")
        
        while True:
            try:
                self.display_main_dashboard()
                
                choice = self.input_handler.get_input("\n🎯 Enter choice: ")
                
                # Handle shortcuts
                shortcut_action = self.navigator.handle_shortcut(choice)
                if shortcut_action == 'quit':
                    break
                elif shortcut_action == 'help':
                    SmartHelp.show_workflow_help('getting_started')
                    continue
                elif shortcut_action == 'menu':
                    continue  # Redisplay menu
                
                if choice == '0' or choice.lower() in ['exit', 'quit']:
                    break
                elif choice.lower() == 's':
                    await self._handle_service_selection()
                else:
                    # Handle quick actions
                    quick_actions = self._show_quick_actions()
                    try:
                        quick_idx = int(choice) - 1
                        if 0 <= quick_idx < len(quick_actions):
                            _, service_name, action_name, _ = quick_actions[quick_idx]
                            action = self.available_actions[service_name]['actions'][action_name]
                            result = await self.enhanced_execute_action(service_name, action)
                            input(ColoredOutput.format_text("\n⏸️  Press Enter to continue...", 'gray'))
                        else:
                            ColoredOutput.warning("⚠️  Invalid choice")
                    except ValueError:
                        ColoredOutput.warning("⚠️  Please enter a valid number or command")
                        
            except KeyboardInterrupt:
                ColoredOutput.warning("\n👋 Session interrupted")
                break
        
        ColoredOutput.info("👋 Enhanced interactive session ended")
    
    async def _handle_service_selection(self):
        """Handle service selection with enhanced navigation."""
        self.navigator.push_location("Services")
        
        while True:
            try:
                services = self.display_enhanced_services_menu()
                choice = self.input_handler.get_input("\n🎯 Select service: ")
                
                if choice == '0':
                    break
                elif choice.lower() == 's':
                    await self._handle_global_search()
                    continue
                elif choice.lower() == 'b':
                    self._show_bookmarks()
                    continue
                
                try:
                    service_idx = int(choice) - 1
                    if 0 <= service_idx < len(services):
                        selected_service = services[service_idx]
                        await self._handle_action_selection(selected_service)
                    else:
                        ColoredOutput.warning("⚠️  Invalid service selection")
                except ValueError:
                    ColoredOutput.warning("⚠️  Please enter a valid number")
                    
            except KeyboardInterrupt:
                break
        
        self.navigator.pop_location()
    
    async def _handle_action_selection(self, service_name: str):
        """Handle action selection for a service."""
        self.navigator.push_location(f"Service: {service_name}")
        
        while True:
            try:
                actions = self.display_enhanced_actions_menu(service_name)
                choice = self.input_handler.get_input("\n🎯 Select action: ")
                
                if choice == '0':
                    break
                elif choice.lower() == 'f':
                    filtered_actions = self._filter_actions(actions)
                    if filtered_actions:
                        # Show filtered actions and allow selection
                        # Implementation details...
                        pass
                    continue
                elif choice.lower() == 's':
                    await self._search_actions_in_service(service_name, actions)
                    continue
                
                try:
                    action_idx = int(choice) - 1
                    if 0 <= action_idx < len(actions):
                        selected_action = actions[action_idx]
                        result = await self.enhanced_execute_action(service_name, selected_action)
                        input(ColoredOutput.format_text("\n⏸️  Press Enter to continue...", 'gray'))
                    else:
                        ColoredOutput.warning("⚠️  Invalid action selection")
                except ValueError:
                    ColoredOutput.warning("⚠️  Please enter a valid number")
                    
            except KeyboardInterrupt:
                break
        
        self.navigator.pop_location()
    
    async def _handle_global_search(self):
        """Handle global search across all services."""
        ColoredOutput.header("🔍 Global Action Search")
        
        search_term = self.input_handler.get_input("Enter search term: ")
        if not search_term:
            return
        
        matches = []
        for service_name, service_info in self.available_actions.items():
            for action_name, action in service_info['actions'].items():
                if search_term.lower() in action_name.lower():
                    matches.append((service_name, action_name, action))
        
        if matches:
            ColoredOutput.success(f"Found {len(matches)} matching actions:")
            for i, (service_name, action_name, action) in enumerate(matches, 1):
                ColoredOutput.print(f"  {i}. {service_name}.{action_name}", 'yellow')
            
            choice = self.input_handler.get_input("\nSelect action to execute (number): ")
            try:
                match_idx = int(choice) - 1
                if 0 <= match_idx < len(matches):
                    service_name, action_name, action = matches[match_idx]
                    result = await self.enhanced_execute_action(service_name, action)
            except (ValueError, IndexError):
                ColoredOutput.warning("Invalid selection")
        else:
            ColoredOutput.warning(f"No actions found matching '{search_term}'")
    
    def _filter_actions(self, actions) -> List[Any]:
        """Filter actions by complexity or type."""
        ColoredOutput.header("🔍 Filter Actions")
        ColoredOutput.print("1. No input required (easy)", 'green')
        ColoredOutput.print("2. Simple (1-2 inputs)", 'yellow')
        ColoredOutput.print("3. Complex (3+ inputs)", 'red')
        ColoredOutput.print("4. Browse/Search actions", 'cyan')
        
        choice = self.input_handler.get_input("Filter type: ")
        
        if choice == '1':
            return [a for a in actions if len(a.arguments_in) == 0]
        elif choice == '2':
            return [a for a in actions if 1 <= len(a.arguments_in) <= 2]
        elif choice == '3':
            return [a for a in actions if len(a.arguments_in) >= 3]
        elif choice == '4':
            return [a for a in actions if any(keyword in a.name.lower() for keyword in ['browse', 'search', 'get'])]
        
        return actions
    
    async def _search_actions_in_service(self, service_name: str, actions):
        """Search actions within a specific service."""
        search_term = self.input_handler.get_input(f"Search actions in {service_name}: ")
        if not search_term:
            return
        
        matches = [a for a in actions if search_term.lower() in a.name.lower()]
        
        if matches:
            ColoredOutput.success(f"Found {len(matches)} matching actions in {service_name}:")
            for i, action in enumerate(matches, 1):
                ColoredOutput.print(f"  {i}. {action.name}", 'yellow')
        else:
            ColoredOutput.warning(f"No actions found matching '{search_term}' in {service_name}")
    
    def _show_bookmarks(self):
        """Show bookmarked actions."""
        if not self.bookmarks:
            ColoredOutput.warning("No bookmarks saved")
            return
        
        ColoredOutput.header("📑 Bookmarked Actions")
        for i, (name, bookmark) in enumerate(self.bookmarks.items(), 1):
            ColoredOutput.print(f"  {i}. {name}: {bookmark['service']}.{bookmark['action']}", 'yellow')


async def cmd_enhanced_interactive(args) -> Dict[str, Any]:
    """Enhanced interactive SOAP control command."""
    try:
        # Auto-discover if no host specified
        if not args.host:
            ColoredOutput.info("🔍 Auto-discovering devices...")
            devices = await discovery.discover_ssdp_devices(timeout=5)
            if devices:
                device = devices[0]
                args.host = device.get('ip') or device.get('addr')
                if not args.host:
                    return {"status": "error", "message": "Could not determine device IP"}
                ColoredOutput.success(f"✅ Auto-discovered device: {args.host}")
            else:
                return {"status": "error", "message": "No devices found for auto-discovery"}
        
        # Create enhanced controller
        controller = EnhancedInteractiveController(
            host=args.host,
            port=args.port,
            use_ssl=args.use_ssl
        )
        
        # Initialize with progress tracking
        if not await controller.initialize():
            return {"status": "error", "message": "Failed to initialize enhanced controller"}
        
        # Run enhanced session
        await controller.run_enhanced_session()
        
        return {"status": "success", "message": "Enhanced interactive session completed"}
        
    except Exception as e:
        ColoredOutput.error(f"Enhanced interactive control failed: {e}")
        logger.exception("Enhanced interactive control error")
        return {"status": "error", "message": str(e)}