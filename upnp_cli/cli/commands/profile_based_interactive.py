#!/usr/bin/env python3
"""
Profile-Based Interactive Controller

Uses enhanced profiles with complete SCPD data for intelligent 
action execution with validation and guidance.
"""

import asyncio
import json
from typing import Dict, List, Any, Optional

from upnp_cli.profiles import get_profile_manager
from upnp_cli.cli.output import ColoredOutput
from upnp_cli.cli.ux_improvements import InteractiveInput
from upnp_cli.cli.utils import auto_discover_target
import upnp_cli.discovery as discovery
import upnp_cli.soap_client as soap_client

class ProfileBasedController:
    """Interactive controller using enhanced profiles with SCPD data."""
    
    def __init__(self, host: str, port: int = 1400):
        self.host = host
        self.port = port
        self.profile = None
        self.device_info = None
        self.soap_client = soap_client.get_soap_client()
        self.input_handler = InteractiveInput()
    
    async def initialize(self) -> bool:
        """Initialize with profile matching."""
        ColoredOutput.info(f"🔍 Initializing profile-based controller for {self.host}:{self.port}")
        
        # Get device info
        self.device_info = await self._get_device_info()
        if not self.device_info:
            ColoredOutput.error("❌ Could not fetch device information")
            return False
        
        # Try to match device to profile
        profile_manager = get_profile_manager()
        self.profile = profile_manager.get_best_profile(self.device_info)
        
        if not self.profile:
            ColoredOutput.error("❌ No matching profile found")
            return False
        
        # Check if profile has enhanced SCPD data
        if not hasattr(self.profile, 'upnp') or not self.profile.upnp:
            ColoredOutput.error("❌ Profile lacks UPnP configuration")
            return False
        
        # Check for enhanced profile data
        if isinstance(self.profile.upnp, dict) and 'action_inventory' in self.profile.upnp:
            ColoredOutput.success(f"✅ Loaded enhanced profile: {self.profile.name}")
            self._display_profile_capabilities()
        else:
            ColoredOutput.warning("⚠️  Profile lacks enhanced SCPD data - using basic functionality")
        
        return True
    
    async def _get_device_info(self) -> Optional[Dict[str, Any]]:
        """Get device information."""
        try:
            device_url = f"http://{self.host}:{self.port}/xml/device_description.xml"
            
            import aiohttp
            async with aiohttp.ClientSession() as session:
                return await discovery.fetch_device_description(session, device_url)
        except Exception as e:
            ColoredOutput.error(f"Failed to get device info: {e}")
            return None
    
    def _display_profile_capabilities(self):
        """Display profile capabilities summary."""
        if not hasattr(self.profile, 'upnp') or not isinstance(self.profile.upnp, dict):
            return
        
        # Check for enhanced capabilities
        if 'capabilities' in self.profile.upnp:
            caps = self.profile.upnp['capabilities']
            ColoredOutput.print("\n📊 Enhanced Device Capabilities:", 'cyan', bold=True)
            ColoredOutput.print(f"  🎵 Media Control: {len(caps.get('media_control', []))} actions", 'white')
            ColoredOutput.print(f"  🔊 Volume Control: {len(caps.get('volume_control', []))} actions", 'white')
            ColoredOutput.print(f"  ℹ️  Information: {len(caps.get('information_retrieval', []))} actions", 'white')
            ColoredOutput.print(f"  ⚙️  Configuration: {len(caps.get('configuration', []))} actions", 'white')
            ColoredOutput.print(f"  🔒 Security: {len(caps.get('security', []))} actions", 'white')
            
            total_actions = sum(len(actions) for actions in caps.values())
            ColoredOutput.print(f"  📋 Total Actions: {total_actions}", 'green', bold=True)
        else:
            # Basic profile info
            basic_services = len(self.profile.upnp) if isinstance(self.profile.upnp, dict) else 0
            ColoredOutput.print(f"\n📊 Basic Profile: {basic_services} services available", 'cyan')
    
    async def run_interactive_session(self):
        """Run interactive session with profile-based actions."""
        while True:
            self._display_main_menu()
            choice = self.input_handler.get_input("\nSelect option")
            
            if choice == 'q':
                break
            elif choice == '1':
                await self._browse_actions_by_category()
            elif choice == '2':
                await self._search_actions()
            elif choice == '3':
                await self._browse_services()
            elif choice == '4':
                await self._quick_actions()
            elif choice == '5':
                self._display_profile_info()
            elif choice == 'h':
                self._display_help()
    
    def _display_main_menu(self):
        """Display main interactive menu."""
        ColoredOutput.print(f"\n🎮 {self.profile.name} Controller", 'cyan', bold=True)
        ColoredOutput.print("=" * 50, 'cyan')
        
        # Check if enhanced profile
        if isinstance(self.profile.upnp, dict) and 'action_inventory' in self.profile.upnp:
            ColoredOutput.print("1. Browse Actions by Category", 'white')
            ColoredOutput.print("2. Search Actions", 'white')
            ColoredOutput.print("3. Browse by Service", 'white')
        else:
            ColoredOutput.print("1. Basic Service Control", 'white')
            ColoredOutput.print("2. Available Services", 'white')
            ColoredOutput.print("3. Manual SOAP Action", 'white')
        
        ColoredOutput.print("4. Quick Actions", 'white')
        ColoredOutput.print("5. Profile Information", 'white')
        ColoredOutput.print("h. Help", 'gray')
        ColoredOutput.print("q. Quit", 'gray')
    
    async def _browse_actions_by_category(self):
        """Browse actions organized by category."""
        if not isinstance(self.profile.upnp, dict) or 'capabilities' not in self.profile.upnp:
            ColoredOutput.error("Enhanced profile data not available")
            return
        
        capabilities = self.profile.upnp['capabilities']
        
        ColoredOutput.print("\n📂 Action Categories:", 'yellow', bold=True)
        categories = [(k, v) for k, v in capabilities.items() if v]
        
        if not categories:
            ColoredOutput.warning("No categorized actions available")
            return
        
        for i, (category, actions) in enumerate(categories, 1):
            ColoredOutput.print(f"{i}. {category.replace('_', ' ').title()} ({len(actions)} actions)", 'white')
        
        try:
            choice = int(self.input_handler.get_input("Select category (number)")) - 1
            if 0 <= choice < len(categories):
                category, actions = categories[choice]
                await self._display_category_actions(category, actions)
        except (ValueError, IndexError):
            ColoredOutput.error("Invalid selection")
    
    async def _display_category_actions(self, category: str, actions: List[str]):
        """Display actions in a specific category."""
        ColoredOutput.print(f"\n🎯 {category.replace('_', ' ').title()} Actions:", 'green', bold=True)
        
        for i, action_name in enumerate(actions, 1):
            # Find action details
            action_info = self._find_action_info(action_name)
            if action_info:
                complexity = action_info.get('complexity', '🟢 Easy')
                ColoredOutput.print(f"{i:2d}. {action_name} {complexity}", 'white')
            else:
                ColoredOutput.print(f"{i:2d}. {action_name}", 'white')
        
        try:
            choice = int(self.input_handler.get_input("Select action to execute (number)")) - 1
            if 0 <= choice < len(actions):
                await self._execute_action_with_guidance(actions[choice])
        except (ValueError, IndexError):
            ColoredOutput.error("Invalid selection")
    
    def _find_action_info(self, action_name: str) -> Optional[Dict[str, Any]]:
        """Find action information across all services."""
        if not isinstance(self.profile.upnp, dict) or 'action_inventory' not in self.profile.upnp:
            return None
        
        action_inventory = self.profile.upnp['action_inventory']
        
        for service_name, actions in action_inventory.items():
            if action_name in actions:
                return actions[action_name]
        
        return None
    
    async def _execute_action_with_guidance(self, action_name: str):
        """Execute action with intelligent guidance and validation."""
        action_info = self._find_action_info(action_name)
        if not action_info:
            ColoredOutput.error(f"Action {action_name} not found in profile")
            return
        
        # Find service and control URL
        service_name, control_url = self._find_action_service(action_name)
        if not control_url:
            ColoredOutput.error(f"No control URL found for action {action_name}")
            return
        
        ColoredOutput.print(f"\n🎬 Executing: {action_name}", 'cyan', bold=True)
        ColoredOutput.print(f"Service: {service_name}", 'white')
        ColoredOutput.print(f"Complexity: {action_info.get('complexity', 'Unknown')}", 'white')
        
        # Show description if available
        if action_info.get('description'):
            ColoredOutput.print(f"Description: {action_info['description']}", 'gray')
        
        # Collect arguments with validation
        arguments = {}
        for arg_info in action_info.get('arguments_in', []):
            value = await self._prompt_for_argument(arg_info)
            if value is not None:
                arguments[arg_info['name']] = value
        
        # Confirm execution
        if arguments:
            ColoredOutput.print(f"\nArguments: {arguments}", 'yellow')
        
        confirm = self.input_handler.get_input("Execute action? (y/n)", default="y")
        if confirm.lower() != 'y':
            ColoredOutput.info("Action cancelled")
            return
        
        # Execute the action
        try:
            full_control_url = f"http://{self.host}:{self.port}{control_url}"
            service_type = self._get_service_type(service_name)
            
            result = await self.soap_client.call_action(
                full_control_url,
                service_type,
                action_name,
                arguments
            )
            
            ColoredOutput.success(f"✅ Action {action_name} executed successfully")
            self._display_action_result(result, action_info.get('arguments_out', []))
            
        except Exception as e:
            ColoredOutput.error(f"❌ Action failed: {e}")
    
    def _find_action_service(self, action_name: str) -> tuple[str, str]:
        """Find the service and control URL for an action."""
        if not isinstance(self.profile.upnp, dict):
            return "", ""
        
        # Enhanced profile
        if 'action_inventory' in self.profile.upnp:
            action_inventory = self.profile.upnp['action_inventory']
            services = self.profile.upnp.get('services', {})
            
            for service_name, actions in action_inventory.items():
                if action_name in actions:
                    control_url = services.get(service_name, {}).get('controlURL', '')
                    return service_name, control_url
        
        # Basic profile - try to find in upnp services
        for service_name, service_config in self.profile.upnp.items():
            if isinstance(service_config, dict) and 'controlURL' in service_config:
                return service_name, service_config['controlURL']
        
        return "", ""
    
    def _get_service_type(self, service_name: str) -> str:
        """Get service type for a service name."""
        if isinstance(self.profile.upnp, dict) and 'services' in self.profile.upnp:
            services = self.profile.upnp['services']
            return services.get(service_name, {}).get('serviceType', '')
        
        # Fallback for basic profiles
        service_mapping = {
            'avtransport': 'urn:schemas-upnp-org:service:AVTransport:1',
            'rendering': 'urn:schemas-upnp-org:service:RenderingControl:1',
            'connectionmanager': 'urn:schemas-upnp-org:service:ConnectionManager:1',
            'contentdirectory': 'urn:schemas-upnp-org:service:ContentDirectory:1'
        }
        
        return service_mapping.get(service_name.lower(), '')
    
    async def _prompt_for_argument(self, arg_info: Dict[str, Any]) -> Optional[str]:
        """Prompt for argument with intelligent validation."""
        arg_name = arg_info['name']
        validation = arg_info.get('validation', {})
        
        ColoredOutput.print(f"\n📝 Argument: {arg_name}", 'yellow', bold=True)
        
        # Show data type
        if 'data_type' in validation:
            ColoredOutput.print(f"Type: {validation['data_type']}", 'white')
        
        # Show allowed values
        if 'allowed_values' in validation and validation['allowed_values']:
            ColoredOutput.print(f"Allowed values: {', '.join(validation['allowed_values'])}", 'white')
        
        # Show range
        if 'minimum' in validation and 'maximum' in validation:
            ColoredOutput.print(f"Range: {validation['minimum']} - {validation['maximum']}", 'white')
        
        # Suggest common values
        suggestions = self._get_argument_suggestions(arg_name)
        if suggestions:
            ColoredOutput.print(f"Suggestions: {', '.join(suggestions)}", 'cyan')
        
        # Get user input with validation
        while True:
            value = self.input_handler.get_input(f"Enter {arg_name} (or 'skip')")
            
            if value.lower() == 'skip':
                return None
            
            # Validate input
            if self._validate_argument(value, validation):
                return value
            else:
                ColoredOutput.error("Invalid value - please try again")
    
    def _get_argument_suggestions(self, arg_name: str) -> List[str]:
        """Get common value suggestions for arguments."""
        suggestions_map = {
            'InstanceID': ['0'],
            'Speed': ['1'],
            'CurrentURI': ['http://example.com/audio.mp3'],
            'DesiredVolume': ['50', '25', '75'],
            'Channel': ['Master'],
            'DesiredMute': ['0', '1'],
            'ObjectID': ['0'],
            'BrowseFlag': ['BrowseDirectChildren', 'BrowseMetadata']
        }
        
        return suggestions_map.get(arg_name, [])
    
    def _validate_argument(self, value: str, validation: Dict[str, Any]) -> bool:
        """Validate argument value against constraints."""
        if not value:
            return False
        
        # Check allowed values
        if 'allowed_values' in validation and validation['allowed_values']:
            return value in validation['allowed_values']
        
        # Check numeric range
        if 'minimum' in validation and 'maximum' in validation:
            try:
                num_value = float(value)
                return validation['minimum'] <= num_value <= validation['maximum']
            except ValueError:
                return False
        
        return True
    
    def _display_action_result(self, result: Dict[str, Any], expected_outputs: List[Dict[str, Any]]):
        """Display action execution result."""
        if not result:
            ColoredOutput.info("Action completed (no response data)")
            return
        
        ColoredOutput.print("\n📋 Action Result:", 'green', bold=True)
        
        # Show expected vs actual outputs
        if expected_outputs:
            ColoredOutput.print("Expected outputs:", 'cyan')
            for output in expected_outputs:
                ColoredOutput.print(f"  • {output['name']} ({output.get('data_type', 'unknown')})", 'gray')
        
        # Show actual result
        ColoredOutput.print("\nActual result:", 'white')
        for key, value in result.items():
            ColoredOutput.print(f"  {key}: {value}", 'white')
    
    async def _search_actions(self):
        """Search for actions by name."""
        if not isinstance(self.profile.upnp, dict) or 'action_inventory' not in self.profile.upnp:
            ColoredOutput.error("Enhanced profile data not available for search")
            return
        
        search_term = self.input_handler.get_input("Enter search term")
        if not search_term:
            return
        
        # Find matching actions
        matches = []
        action_inventory = self.profile.upnp['action_inventory']
        
        for service_name, actions in action_inventory.items():
            for action_name, action_info in actions.items():
                if search_term.lower() in action_name.lower():
                    matches.append((service_name, action_name, action_info))
        
        if not matches:
            ColoredOutput.warning(f"No actions found matching '{search_term}'")
            return
        
        ColoredOutput.print(f"\n🔍 Search Results for '{search_term}':", 'yellow', bold=True)
        
        for i, (service, action, info) in enumerate(matches, 1):
            complexity = info.get('complexity', '🟢 Easy')
            category = info.get('category', 'other')
            ColoredOutput.print(f"{i:2d}. {action} {complexity} ({service})", 'white')
            ColoredOutput.print(f"     Category: {category}", 'gray')
        
        try:
            choice = int(self.input_handler.get_input("Select action to execute (number)")) - 1
            if 0 <= choice < len(matches):
                _, action_name, _ = matches[choice]
                await self._execute_action_with_guidance(action_name)
        except (ValueError, IndexError):
            ColoredOutput.error("Invalid selection")
    
    async def _browse_services(self):
        """Browse actions by service."""
        if isinstance(self.profile.upnp, dict) and 'action_inventory' in self.profile.upnp:
            # Enhanced profile
            action_inventory = self.profile.upnp['action_inventory']
            services = list(action_inventory.keys())
        else:
            # Basic profile
            services = list(self.profile.upnp.keys()) if isinstance(self.profile.upnp, dict) else []
        
        if not services:
            ColoredOutput.warning("No services available")
            return
        
        ColoredOutput.print("\n🔧 Available Services:", 'magenta', bold=True)
        
        for i, service_name in enumerate(services, 1):
            if isinstance(self.profile.upnp, dict) and 'action_inventory' in self.profile.upnp:
                action_count = len(self.profile.upnp['action_inventory'].get(service_name, {}))
                ColoredOutput.print(f"{i}. {service_name.title()} ({action_count} actions)", 'white')
            else:
                ColoredOutput.print(f"{i}. {service_name.title()}", 'white')
        
        try:
            choice = int(self.input_handler.get_input("Select service (number)")) - 1
            if 0 <= choice < len(services):
                await self._display_service_actions(services[choice])
        except (ValueError, IndexError):
            ColoredOutput.error("Invalid selection")
    
    async def _display_service_actions(self, service_name: str):
        """Display actions for a specific service."""
        if isinstance(self.profile.upnp, dict) and 'action_inventory' in self.profile.upnp:
            actions = self.profile.upnp['action_inventory'].get(service_name, {})
            
            ColoredOutput.print(f"\n🔧 {service_name.title()} Service Actions:", 'cyan', bold=True)
            
            action_list = list(actions.keys())
            for i, action_name in enumerate(action_list, 1):
                action_info = actions[action_name]
                complexity = action_info.get('complexity', '🟢 Easy')
                ColoredOutput.print(f"{i:2d}. {action_name} {complexity}", 'white')
            
            try:
                choice = int(self.input_handler.get_input("Select action to execute (number)")) - 1
                if 0 <= choice < len(action_list):
                    await self._execute_action_with_guidance(action_list[choice])
            except (ValueError, IndexError):
                ColoredOutput.error("Invalid selection")
        else:
            ColoredOutput.info(f"Basic service: {service_name}")
            ColoredOutput.info("Use manual SOAP action execution")
    
    async def _quick_actions(self):
        """Quick access to common actions."""
        quick_actions = [
            ('GetTransportInfo', 'Get playback status'),
            ('Play', 'Start playback'),
            ('Pause', 'Pause playback'),
            ('Stop', 'Stop playback'),
            ('GetVolume', 'Get current volume'),
            ('SetVolume', 'Set volume level'),
            ('GetMute', 'Get mute status'),
            ('SetMute', 'Set mute on/off')
        ]
        
        ColoredOutput.print("\n⚡ Quick Actions:", 'yellow', bold=True)
        
        available_quick = []
        for action, description in quick_actions:
            if self._find_action_info(action):
                available_quick.append((action, description))
        
        if not available_quick:
            ColoredOutput.warning("No quick actions available for this device")
            return
        
        for i, (action, description) in enumerate(available_quick, 1):
            ColoredOutput.print(f"{i}. {action} - {description}", 'white')
        
        try:
            choice = int(self.input_handler.get_input("Select quick action (number)")) - 1
            if 0 <= choice < len(available_quick):
                action_name = available_quick[choice][0]
                await self._execute_action_with_guidance(action_name)
        except (ValueError, IndexError):
            ColoredOutput.error("Invalid selection")
    
    def _display_profile_info(self):
        """Display detailed profile information."""
        ColoredOutput.print(f"\n📋 Profile Information: {self.profile.name}", 'cyan', bold=True)
        ColoredOutput.print("=" * 50, 'cyan')
        
        if hasattr(self.profile, 'notes') and self.profile.notes:
            ColoredOutput.print(f"Notes: {self.profile.notes}", 'white')
        
        # Show match criteria
        if hasattr(self.profile, 'match_criteria'):
            ColoredOutput.print("\nMatch Criteria:", 'yellow')
            for key, values in self.profile.match_criteria.items():
                ColoredOutput.print(f"  {key}: {', '.join(values)}", 'gray')
        
        # Show enhanced data if available
        if isinstance(self.profile.upnp, dict) and 'metadata' in self.profile.upnp:
            metadata = self.profile.upnp['metadata']
            ColoredOutput.print(f"\nProfile Generated: {metadata.get('generated_at', 'Unknown')}", 'white')
            
            if 'scpd_analysis' in metadata:
                scpd = metadata['scpd_analysis']
                ColoredOutput.print(f"Services Analyzed: {scpd.get('services_analyzed', 0)}", 'white')
                ColoredOutput.print(f"Total Actions: {scpd.get('total_actions', 0)}", 'green')
    
    def _display_help(self):
        """Display help information."""
        ColoredOutput.print("\n❓ Help", 'blue', bold=True)
        ColoredOutput.print("=" * 30, 'blue')
        ColoredOutput.print("• Use number keys to select options", 'white')
        ColoredOutput.print("• Type 'skip' during argument input to skip optional parameters", 'white')
        ColoredOutput.print("• Enhanced profiles provide validation and suggestions", 'white')
        ColoredOutput.print("• Use search to quickly find specific actions", 'white')
        ColoredOutput.print("• Quick actions provide common operations", 'white')


async def cmd_profile_interactive(args) -> Dict[str, Any]:
    """Command entry point for profile-based interactive control."""
    try:
        # Auto-discover if no host specified
        if not args.host:
            devices = await auto_discover_target(args)
            if not devices:
                return {"status": "error", "message": "No devices found"}
            device = devices[0]
            args.host = device['ip']
            args.port = device.get('port', args.port)
        
        # Initialize controller
        controller = ProfileBasedController(args.host, args.port)
        
        if not await controller.initialize():
            return {"status": "error", "message": "Failed to initialize profile-based controller"}
        
        # Run interactive session
        await controller.run_interactive_session()
        
        return {"status": "success", "message": "Interactive session completed"}
        
    except Exception as e:
        ColoredOutput.error(f"Profile-based interactive control failed: {e}")
        return {"status": "error", "message": str(e)} 