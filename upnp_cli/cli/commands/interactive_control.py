#!/usr/bin/env python3
"""
Interactive SOAP Action Execution System

This module provides an interactive interface for executing SOAP actions
discovered through comprehensive SCPD parsing.
"""

import asyncio
import logging
import json
import sys
from typing import Dict, List, Any, Optional, Tuple
from urllib.parse import urljoin

# Import core modules - fix import mess
import sys
from pathlib import Path

# Ensure we can import from the upnp_cli package
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import upnp_cli.discovery as discovery
import upnp_cli.soap_client as soap_client
from upnp_cli.profile_generation.scpd_parser import parse_device_scpds, EnhancedSCPDParser
from upnp_cli.cli.output import ColoredOutput, ProgressReporter

logger = logging.getLogger(__name__)


class InteractiveSOAPController:
    """Interactive controller for executing SOAP actions on UPnP devices."""
    
    def __init__(self, host: str, port: int = 1400, use_ssl: bool = False):
        self.host = host
        self.port = port
        self.use_ssl = use_ssl
        self.device_info = None
        self.scpd_documents = []
        self.available_actions = {}  # service_type -> list of actions
        self.soap_client = soap_client.get_soap_client()
        
    async def initialize(self) -> bool:
        """Initialize the controller by discovering device and parsing SCPD files."""
        try:
            ColoredOutput.info(f"🔍 Initializing interactive control for {self.host}:{self.port}")
            
            # Try to fetch device description
            device_url = None
            
            # Try common device description paths
            common_paths = [
                "/xml/device_description.xml",
                "/description.xml", 
                "/MediaServer/rendererdevicedesc.xml",
                "/upnp/desc.xml",
                "/device_description.xml"
            ]
            
            protocol = "https" if self.use_ssl else "http"
            
            for path in common_paths:
                try:
                    test_url = f"{protocol}://{self.host}:{self.port}{path}"
                    import aiohttp
                    async with aiohttp.ClientSession() as session:
                        async with session.get(test_url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                            if resp.status == 200:
                                device_url = test_url
                                break
                except:
                    continue
            
            if not device_url:
                ColoredOutput.error("❌ Could not find device description")
                return False
                
            ColoredOutput.success(f"✅ Found device description: {device_url}")
            
            # Fetch and parse device description
            import aiohttp
            async with aiohttp.ClientSession() as session:
                self.device_info = await discovery.fetch_device_description(session, device_url)
                
            if not self.device_info:
                ColoredOutput.error("❌ Failed to parse device description")
                return False
                
            services = self.device_info.get('services', [])
            
            # Also check for embedded devices (like Sonos MediaRenderer)
            embedded_devices = self.device_info.get('devices', [])
            for embedded_device in embedded_devices:
                embedded_services = embedded_device.get('services', [])
                services.extend(embedded_services)
                ColoredOutput.info(f"📱 Found embedded device: {embedded_device.get('deviceType', 'Unknown')} with {len(embedded_services)} services")
            
            ColoredOutput.info(f"📋 Found {len(services)} total services (including embedded devices)")
            
            if not services:
                ColoredOutput.warning("⚠️  No services found in device description")
                return False
            
            # Parse SCPD documents to get available actions
            base_url = device_url.rsplit('/', 1)[0]
            ColoredOutput.info(f"🔍 Parsing SCPD files from base URL: {base_url}")
            
            self.scpd_documents = await parse_device_scpds(self.device_info, base_url)
            
            if not self.scpd_documents:
                ColoredOutput.error("❌ No SCPD documents could be parsed")
                return False
                
            successful_docs = len([doc for doc in self.scpd_documents if doc.parsing_success])
            total_actions = sum(doc.get_action_count() for doc in self.scpd_documents)
            
            ColoredOutput.success(f"✅ Successfully parsed {successful_docs}/{len(self.scpd_documents)} SCPD documents")
            ColoredOutput.success(f"✅ Discovered {total_actions} total SOAP actions")
            
            # Organize actions by service
            for doc in self.scpd_documents:
                if doc.parsing_success and doc.actions:
                    service_name = doc.service_type.split(':')[-2] if ':' in doc.service_type else doc.service_type
                    self.available_actions[service_name] = {
                        'service_type': doc.service_type,
                        'control_url': None,
                        'actions': doc.actions,
                        'scpd_doc': doc
                    }
                    
                    # Find control URL from device info
                    for service in services:
                        if service.get('serviceType') == doc.service_type:
                            control_url = service.get('controlURL', '')
                            if control_url:
                                if not control_url.startswith('http'):
                                    control_url = urljoin(base_url + '/', control_url)
                                self.available_actions[service_name]['control_url'] = control_url
                            break
            
            if not self.available_actions:
                ColoredOutput.error("❌ No executable actions found")
                return False
                
            return True
            
        except Exception as e:
            ColoredOutput.error(f"❌ Initialization failed: {e}")
            logger.exception("Interactive controller initialization error")
            return False
    
    def display_services_menu(self):
        """Display available services menu."""
        ColoredOutput.header("🎮 Available Services")
        
        services = list(self.available_actions.keys())
        for i, service_name in enumerate(services, 1):
            service_info = self.available_actions[service_name]
            action_count = len(service_info['actions'])
            has_control = "✅" if service_info['control_url'] else "❌"
            
            # Color code by action count for better visual hierarchy
            if action_count > 15:
                color, weight = 'cyan', True
            elif action_count > 5:
                color, weight = 'yellow', False
            else:
                color, weight = 'white', False
            
            ColoredOutput.print(f"  {i}. {service_name}", color, bold=weight)
            ColoredOutput.print(f"     📊 Actions: {action_count} | 🎯 Control: {has_control}", 'white')
        
        # Add shortcuts and help
        ColoredOutput.print(f"\n⚡ Shortcuts:", 'gray')
        ColoredOutput.print(f"  s - Search actions across all services", 'gray')
        ColoredOutput.print(f"  h - Show help", 'gray')
        ColoredOutput.print(f"  q - Quit", 'gray')
        ColoredOutput.print(f"  0 - Exit", 'red')
        
        return services
    
    def display_actions_menu(self, service_name: str):
        """Display available actions for a service."""
        service_info = self.available_actions[service_name]
        actions = list(service_info['actions'].values())
        
        ColoredOutput.header(f"🎯 Actions for {service_name}")
        ColoredOutput.print(f"📊 Total Actions: {len(actions)}", 'cyan')
        
        for i, action in enumerate(actions, 1):
            args_in = len(action.arguments_in)
            args_out = len(action.arguments_out)
            
            # Color code by complexity for better UX
            if args_in == 0:
                color = 'green'  # Easy - no input required
                complexity = "🟢 Easy"
            elif args_in <= 2:
                color = 'yellow'  # Medium
                complexity = "🟡 Medium"
            else:
                color = 'red'  # Complex
                complexity = "🔴 Complex"
            
            ColoredOutput.print(f"  {i}. {action.name}", color, bold=True)
            ColoredOutput.print(f"     {complexity} | 📥 Input: {args_in} | 📤 Output: {args_out}", 'white')
            
            # Show argument preview for better understanding
            if action.arguments_in:
                arg_names = [arg.name for arg in action.arguments_in[:3]]
                preview = ", ".join(arg_names)
                if len(action.arguments_in) > 3:
                    preview += f", +{len(action.arguments_in) - 3} more"
                ColoredOutput.print(f"     🔧 Args: {preview}", 'gray')
        
        # Add filtering options
        ColoredOutput.print(f"\n🔍 Filters:", 'gray')
        ColoredOutput.print(f"  e - Show only easy actions (no input)", 'gray')
        ColoredOutput.print(f"  m - Show only medium actions (1-2 inputs)", 'gray')
        ColoredOutput.print(f"  c - Show only complex actions (3+ inputs)", 'gray')
        ColoredOutput.print(f"  f - Search by name", 'gray')
        ColoredOutput.print(f"  0 - Back to services", 'red')
        
        return actions
    
    async def execute_action(self, service_name: str, action) -> Dict[str, Any]:
        """Execute a SOAP action with user-provided arguments."""
        service_info = self.available_actions[service_name]
        control_url = service_info['control_url']
        service_type = service_info['service_type']
        
        if not control_url:
            return {"status": "error", "message": "No control URL available for this service"}
        
        ColoredOutput.header(f"🚀 Executing {action.name}")
        ColoredOutput.print(f"Service: {service_name}", 'cyan')
        ColoredOutput.print(f"Control URL: {control_url}", 'cyan')
        
        # Collect arguments from user
        arguments = {}
        if action.arguments_in:
            ColoredOutput.print(f"\n📝 This action requires {len(action.arguments_in)} arguments:", 'yellow')
            
            for arg in action.arguments_in:
                # Show argument details
                ColoredOutput.print(f"\n  Argument: {arg.name}", 'cyan', bold=True)
                ColoredOutput.print(f"  Type: {arg.data_type or 'unknown'}", 'white')
                if arg.related_state_variable:
                    ColoredOutput.print(f"  State Variable: {arg.related_state_variable}", 'white')
                
                # Get default values and constraints from state variables
                default_value = ""
                allowed_values = []
                if arg.related_state_variable:
                    state_vars = service_info['scpd_doc'].state_variables
                    if arg.related_state_variable in state_vars:
                        state_var = state_vars[arg.related_state_variable]
                        default_value = state_var.default_value
                        allowed_values = state_var.allowed_values
                        if state_var.minimum is not None:
                            ColoredOutput.print(f"  Range: {state_var.minimum} - {state_var.maximum}", 'white')
                
                if allowed_values:
                    ColoredOutput.print(f"  Allowed values: {', '.join(allowed_values)}", 'white')
                
                # Prompt for value with smart defaults
                prompt = f"  Enter value for {arg.name}"
                
                # Add default value (either from state variable or smart suggestion)
                suggested_default = default_value
                if not suggested_default:
                    # Smart defaults for common UPnP arguments
                    if arg.name == "InstanceID":
                        suggested_default = "0"
                    elif arg.name == "Speed" and allowed_values and "1" in allowed_values:
                        suggested_default = "1"
                
                if suggested_default:
                    prompt += f" (default: {suggested_default})"
                prompt += ": "
                
                try:
                    value = input(ColoredOutput.format_text(prompt, 'yellow')).strip()
                    if not value and suggested_default:
                        value = suggested_default
                    
                    # Basic validation
                    if allowed_values and value not in allowed_values:
                        ColoredOutput.warning(f"⚠️  Warning: '{value}' not in allowed values")
                    
                    arguments[arg.name] = value
                    
                except KeyboardInterrupt:
                    ColoredOutput.warning("\n⚠️  Action cancelled by user")
                    return {"status": "cancelled", "message": "User cancelled input"}
        
        # Show execution summary
        ColoredOutput.print(f"\n🎯 Executing Action Summary:", 'green', bold=True)
        ColoredOutput.print(f"Action: {action.name}", 'white')
        ColoredOutput.print(f"Service: {service_type}", 'white')
        ColoredOutput.print(f"Arguments: {len(arguments)}", 'white')
        for arg_name, arg_value in arguments.items():
            ColoredOutput.print(f"  {arg_name}: {arg_value}", 'cyan')
        
        # Confirm execution
        try:
            confirm = input(ColoredOutput.format_text("\n🚀 Execute this action? (y/N): ", 'yellow')).strip().lower()
            if confirm not in ['y', 'yes']:
                ColoredOutput.info("⏸️  Execution cancelled")
                return {"status": "cancelled", "message": "User cancelled execution"}
        except KeyboardInterrupt:
            ColoredOutput.warning("\n⚠️  Execution cancelled by user")
            return {"status": "cancelled", "message": "User cancelled execution"}
        
        # Execute the SOAP action
        try:
            ColoredOutput.info(f"⚡ Sending SOAP request...")
            
            result = await self.soap_client.execute_soap_action(
                control_url=control_url,
                service_type=service_type,
                action_name=action.name,
                arguments=arguments
            )
            
            ColoredOutput.success(f"✅ Action executed successfully!")
            
            # Parse and display results
            status_code = result.status if hasattr(result, 'status') else result.status_code if hasattr(result, 'status_code') else 'unknown'
            ColoredOutput.print(f"HTTP Status: {status_code}", 'cyan')
            
            # Get response text
            if hasattr(result, 'text'):
                # Check if text is callable (method)
                if callable(result.text):
                    response_text = result.text()  # Our wrapper returns text directly
                else:
                    response_text = result.text  # already text
                
                # Try to parse SOAP response
                parsed_response = self.soap_client.parse_soap_response(result, response_text, verbose=True)
                
                return {
                    "status": "success", 
                    "action": action.name,
                    "arguments": arguments,
                    "raw_response": response_text[:1000],  # Limit response size
                    "parsed_response": parsed_response
                }
            else:
                return {
                    "status": "success",
                    "action": action.name, 
                    "arguments": arguments,
                    "result": str(result)
                }
                
        except Exception as e:
            ColoredOutput.error(f"❌ Action execution failed: {e}")
            logger.exception(f"SOAP action execution error")
            return {
                "status": "error",
                "action": action.name,
                "arguments": arguments, 
                "error": str(e)
            }
    
    def display_result(self, result: Dict[str, Any]):
        """Display the result of an action execution."""
        status = result.get('status', 'unknown')
        
        if status == 'success':
            ColoredOutput.success(f"🎉 Action '{result.get('action', 'unknown')}' completed successfully!")
            
            # Show parsed response if available
            parsed = result.get('parsed_response')
            if parsed:
                ColoredOutput.print(f"\n📋 Response Data:", 'green', bold=True)
                if isinstance(parsed, dict):
                    for key, value in parsed.items():
                        ColoredOutput.print(f"  {key}: {value}", 'white')
                else:
                    ColoredOutput.print(f"  {parsed}", 'white')
            
            # Show raw response for debugging
            raw = result.get('raw_response')
            if raw:
                ColoredOutput.print(f"\n🔍 Raw Response (first 500 chars):", 'cyan')
                ColoredOutput.print(f"  {raw[:500]}{'...' if len(raw) > 500 else ''}", 'gray')
                
        elif status == 'error':
            ColoredOutput.error(f"❌ Action '{result.get('action', 'unknown')}' failed!")
            error = result.get('error', 'Unknown error')
            ColoredOutput.print(f"Error: {error}", 'red')
            
        elif status == 'cancelled':
            ColoredOutput.info(f"⏸️  Action cancelled")
    
    async def run_interactive_session(self):
        """Run the main interactive session loop."""
        ColoredOutput.header("🎮 Interactive SOAP Action Controller")
        ColoredOutput.print(f"Device: {self.host}:{self.port}", 'cyan')
        ColoredOutput.print(f"Services: {len(self.available_actions)}", 'cyan')
        
        total_actions = sum(len(info['actions']) for info in self.available_actions.values())
        ColoredOutput.print(f"Total Actions: {total_actions}", 'cyan')
        
        while True:
            try:
                # Service selection menu
                services = self.display_services_menu()
                
                try:
                    choice = input(ColoredOutput.format_text("\n🎯 Select service (number): ", 'yellow')).strip()
                except KeyboardInterrupt:
                    ColoredOutput.warning("\n👋 Goodbye!")
                    break
                
                if choice == '0':
                    ColoredOutput.info("👋 Goodbye!")
                    break
                
                # Handle shortcuts
                if choice.lower() == 's':
                    self._global_search()
                    continue
                elif choice.lower() == 'h':
                    self._show_help()
                    continue
                elif choice.lower() == 'q':
                    ColoredOutput.info("👋 Goodbye!")
                    break
                
                try:
                    service_idx = int(choice) - 1
                    if 0 <= service_idx < len(services):
                        selected_service = services[service_idx]
                    else:
                        ColoredOutput.warning("⚠️  Invalid service selection. Please enter a number from the menu.")
                        continue
                except ValueError:
                    ColoredOutput.warning("⚠️  Please enter a valid number or shortcut (s, h, q, 0)")
                    continue
                
                # Action selection loop for the selected service
                while True:
                    try:
                        actions = self.display_actions_menu(selected_service)
                        
                        try:
                            action_choice = input(ColoredOutput.format_text("\n🎯 Select action (number): ", 'yellow')).strip()
                        except KeyboardInterrupt:
                            break  # Go back to service selection
                        
                        if action_choice == '0':
                            break  # Go back to service selection
                        
                        try:
                            action_idx = int(action_choice) - 1
                            if 0 <= action_idx < len(actions):
                                selected_action = actions[action_idx]
                                
                                # Execute the selected action
                                result = await self.execute_action(selected_service, selected_action)
                                self.display_result(result)
                                
                                # Pause before continuing
                                try:
                                    input(ColoredOutput.format_text("\n⏸️  Press Enter to continue...", 'gray'))
                                except KeyboardInterrupt:
                                    break
                            else:
                                ColoredOutput.warning("⚠️  Invalid action selection")
                        except ValueError:
                            ColoredOutput.warning("⚠️  Please enter a valid number")
                            
                    except KeyboardInterrupt:
                        break  # Go back to service selection
                        
            except KeyboardInterrupt:
                ColoredOutput.warning("\n👋 Goodbye!")
                break

    def _global_search(self):
        """Search for actions across all services."""
        ColoredOutput.header("🔍 Global Action Search")
        
        try:
            search_term = input(ColoredOutput.format_text("Enter search term: ", 'yellow')).strip()
        except KeyboardInterrupt:
            return
        
        if not search_term:
            return
        
        matches = []
        for service_name, service_info in self.available_actions.items():
            for action_name, action in service_info['actions'].items():
                if search_term.lower() in action_name.lower():
                    matches.append((service_name, action_name, action))
        
        if matches:
            ColoredOutput.success(f"✅ Found {len(matches)} matching actions:")
            for i, (service_name, action_name, action) in enumerate(matches[:10], 1):  # Limit to top 10
                args_count = len(action.arguments_in)
                ColoredOutput.print(f"  {i}. {service_name}.{action_name} ({args_count} args)", 'yellow')
            
            if len(matches) > 10:
                ColoredOutput.info(f"... and {len(matches) - 10} more matches")
        else:
            ColoredOutput.warning(f"❌ No actions found matching '{search_term}'")
        
        input(ColoredOutput.format_text("\nPress Enter to continue...", 'gray'))

    def _show_help(self):
        """Display help information."""
        ColoredOutput.header("📚 Interactive Controller Help")
        
        ColoredOutput.print("🎮 Navigation:", 'cyan', bold=True)
        ColoredOutput.print("  • Use numbers to select services and actions", 'white')
        ColoredOutput.print("  • Type 's' to search across all actions", 'white')
        ColoredOutput.print("  • Type 'h' to show this help", 'white')
        ColoredOutput.print("  • Type 'q' or '0' to quit", 'white')
        ColoredOutput.print("  • Use Ctrl+C to cancel at any time", 'white')
        
        ColoredOutput.print("\n🎯 Action Complexity:", 'cyan', bold=True)
        ColoredOutput.print("  🟢 Easy: No input required - safe to try", 'green')
        ColoredOutput.print("  🟡 Medium: 1-2 inputs needed", 'yellow')
        ColoredOutput.print("  🔴 Complex: 3+ inputs required", 'red')
        
        ColoredOutput.print("\n💡 Tips:", 'cyan', bold=True)
        ColoredOutput.print("  • Start with easy (green) actions to explore", 'white')
        ColoredOutput.print("  • GetProtocolInfo is usually safe to try", 'white')
        ColoredOutput.print("  • Browse actions let you explore content", 'white')
        ColoredOutput.print("  • Arguments have smart defaults when possible", 'white')
        
        input(ColoredOutput.format_text("\nPress Enter to continue...", 'gray'))


async def cmd_interactive_control(args) -> Dict[str, Any]:
    """Interactive SOAP action control command."""
    try:
        # Auto-discover if no host specified
        if not args.host:
            ColoredOutput.info("No host specified, auto-discovering devices...")
            devices = await discovery.discover_ssdp_devices(timeout=5)
            if devices:
                device = devices[0]
                args.host = device.get('ip') or device.get('addr')
                if not args.host:
                    return {"status": "error", "message": "Could not determine device IP"}
                ColoredOutput.info(f"Auto-discovered device: {args.host}")
            else:
                return {"status": "error", "message": "No devices found for auto-discovery"}
        
        # Create and initialize controller
        controller = InteractiveSOAPController(
            host=args.host,
            port=args.port,
            use_ssl=args.use_ssl
        )
        
        # Initialize (discover device and parse SCPD)
        if not await controller.initialize():
            return {"status": "error", "message": "Failed to initialize interactive controller"}
        
        # Run interactive session
        await controller.run_interactive_session()
        
        return {"status": "success", "message": "Interactive session completed"}
        
    except Exception as e:
        ColoredOutput.error(f"Interactive control failed: {e}")
        logger.exception("Interactive control error")
        return {"status": "error", "message": str(e)} 