#!/usr/bin/env python3
"""
Configuration Management System

Manages user preferences, device profiles, and persistent settings
to improve the overall user experience.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

from upnp_cli.cli.output import ColoredOutput


@dataclass
class DeviceProfile:
    """User device profile with preferences."""
    name: str
    ip: str
    port: int
    use_ssl: bool = False
    alias: str = ""
    favorite_actions: List[str] = None
    last_used: Optional[str] = None
    notes: str = ""
    
    def __post_init__(self):
        if self.favorite_actions is None:
            self.favorite_actions = []


@dataclass
class UserPreferences:
    """User preferences and settings."""
    default_timeout: int = 10
    default_network: str = ""
    auto_discover: bool = True
    show_progress: bool = True
    colored_output: bool = True
    save_history: bool = True
    max_history: int = 100
    default_output_format: str = "table"  # table, json, minimal
    stealth_mode: bool = False
    verbose_by_default: bool = False
    
    # Interactive preferences
    show_tutorials: bool = True
    show_breadcrumbs: bool = True
    show_shortcuts: bool = True
    auto_suggest: bool = True


class ConfigManager:
    """Manages user configuration and device profiles."""
    
    def __init__(self, config_dir: Optional[str] = None):
        self.config_dir = Path(config_dir) if config_dir else Path.home() / '.upnp_cli'
        self.config_file = self.config_dir / 'config.json'
        self.devices_file = self.config_dir / 'devices.json'
        self.history_file = self.config_dir / 'history.json'
        
        # Ensure config directory exists
        self.config_dir.mkdir(exist_ok=True)
        
        self.preferences = UserPreferences()
        self.device_profiles: Dict[str, DeviceProfile] = {}
        self.command_history: List[Dict[str, Any]] = []
        
        self.load_config()
    
    def load_config(self):
        """Load configuration from files."""
        try:
            # Load user preferences
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    config_data = json.load(f)
                    self.preferences = UserPreferences(**config_data.get('preferences', {}))
            
            # Load device profiles
            if self.devices_file.exists():
                with open(self.devices_file, 'r') as f:
                    devices_data = json.load(f)
                    self.device_profiles = {
                        name: DeviceProfile(**data) 
                        for name, data in devices_data.items()
                    }
            
            # Load command history
            if self.history_file.exists():
                with open(self.history_file, 'r') as f:
                    self.command_history = json.load(f)
        
        except Exception as e:
            ColoredOutput.warning(f"Failed to load configuration: {e}")
    
    def save_config(self):
        """Save configuration to files."""
        try:
            # Save user preferences
            config_data = {
                'preferences': asdict(self.preferences),
                'version': '1.0'
            }
            with open(self.config_file, 'w') as f:
                json.dump(config_data, f, indent=2)
            
            # Save device profiles
            devices_data = {
                name: asdict(profile) 
                for name, profile in self.device_profiles.items()
            }
            with open(self.devices_file, 'w') as f:
                json.dump(devices_data, f, indent=2)
            
            # Save command history
            with open(self.history_file, 'w') as f:
                json.dump(self.command_history[-self.preferences.max_history:], f, indent=2)
        
        except Exception as e:
            ColoredOutput.error(f"Failed to save configuration: {e}")
    
    def add_device_profile(self, name: str, ip: str, port: int = 1400, 
                          use_ssl: bool = False, alias: str = "") -> DeviceProfile:
        """Add or update a device profile."""
        profile = DeviceProfile(
            name=name,
            ip=ip,
            port=port,
            use_ssl=use_ssl,
            alias=alias
        )
        
        self.device_profiles[name] = profile
        self.save_config()
        return profile
    
    def get_device_profile(self, identifier: str) -> Optional[DeviceProfile]:
        """Get device profile by name, alias, or IP."""
        # Try by name first
        if identifier in self.device_profiles:
            return self.device_profiles[identifier]
        
        # Try by alias
        for profile in self.device_profiles.values():
            if profile.alias == identifier:
                return profile
        
        # Try by IP
        for profile in self.device_profiles.values():
            if profile.ip == identifier:
                return profile
        
        return None
    
    def list_device_profiles(self) -> List[DeviceProfile]:
        """Get all device profiles."""
        return list(self.device_profiles.values())
    
    def remove_device_profile(self, name: str) -> bool:
        """Remove a device profile."""
        if name in self.device_profiles:
            del self.device_profiles[name]
            self.save_config()
            return True
        return False
    
    def add_favorite_action(self, device_name: str, action: str):
        """Add an action to device favorites."""
        if device_name in self.device_profiles:
            profile = self.device_profiles[device_name]
            if action not in profile.favorite_actions:
                profile.favorite_actions.append(action)
                self.save_config()
    
    def get_favorite_actions(self, device_name: str) -> List[str]:
        """Get favorite actions for a device."""
        if device_name in self.device_profiles:
            return self.device_profiles[device_name].favorite_actions
        return []
    
    def record_command(self, command: str, args: Dict[str, Any], 
                      result: Dict[str, Any], duration: float):
        """Record a command execution in history."""
        if not self.preferences.save_history:
            return
        
        import time
        history_entry = {
            'timestamp': time.time(),
            'command': command,
            'args': args,
            'result': result,
            'duration': duration,
            'success': result.get('status') == 'success'
        }
        
        self.command_history.append(history_entry)
        
        # Keep only recent history
        if len(self.command_history) > self.preferences.max_history:
            self.command_history = self.command_history[-self.preferences.max_history:]
        
        self.save_config()
    
    def get_command_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent command history."""
        return self.command_history[-limit:]
    
    def get_successful_commands(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent successful commands."""
        successful = [cmd for cmd in self.command_history if cmd.get('success')]
        return successful[-limit:]
    
    def update_preferences(self, **kwargs):
        """Update user preferences."""
        for key, value in kwargs.items():
            if hasattr(self.preferences, key):
                setattr(self.preferences, key, value)
        self.save_config()
    
    def reset_config(self):
        """Reset configuration to defaults."""
        self.preferences = UserPreferences()
        self.device_profiles = {}
        self.command_history = []
        self.save_config()
    
    def export_config(self, export_path: str):
        """Export configuration to a file."""
        export_data = {
            'preferences': asdict(self.preferences),
            'device_profiles': {name: asdict(profile) for name, profile in self.device_profiles.items()},
            'command_history': self.command_history
        }
        
        with open(export_path, 'w') as f:
            json.dump(export_data, f, indent=2)
    
    def import_config(self, import_path: str):
        """Import configuration from a file."""
        with open(import_path, 'r') as f:
            import_data = json.load(f)
        
        # Import preferences
        if 'preferences' in import_data:
            self.preferences = UserPreferences(**import_data['preferences'])
        
        # Import device profiles
        if 'device_profiles' in import_data:
            self.device_profiles = {
                name: DeviceProfile(**data)
                for name, data in import_data['device_profiles'].items()
            }
        
        # Import command history
        if 'command_history' in import_data:
            self.command_history = import_data['command_history']
        
        self.save_config()
    
    def show_status(self):
        """Display current configuration status."""
        ColoredOutput.header("🔧 UPnP CLI Configuration")
        
        # User preferences
        ColoredOutput.print("👤 User Preferences:", 'cyan', bold=True)
        ColoredOutput.print(f"  Default timeout: {self.preferences.default_timeout}s", 'white')
        ColoredOutput.print(f"  Auto-discover: {self.preferences.auto_discover}", 'white')
        ColoredOutput.print(f"  Colored output: {self.preferences.colored_output}", 'white')
        ColoredOutput.print(f"  Save history: {self.preferences.save_history}", 'white')
        ColoredOutput.print(f"  Output format: {self.preferences.default_output_format}", 'white')
        
        # Device profiles
        ColoredOutput.print(f"\n📱 Device Profiles ({len(self.device_profiles)}):", 'cyan', bold=True)
        if self.device_profiles:
            for name, profile in self.device_profiles.items():
                status = "✅" if profile.use_ssl else "🔓"
                alias_text = f" ({profile.alias})" if profile.alias else ""
                ColoredOutput.print(f"  • {name}{alias_text}: {profile.ip}:{profile.port} {status}", 'white')
                if profile.favorite_actions:
                    ColoredOutput.print(f"    Favorites: {', '.join(profile.favorite_actions[:3])}", 'gray')
        else:
            ColoredOutput.print("  No device profiles saved", 'gray')
        
        # Command history
        recent_commands = len(self.command_history)
        successful_rate = 0
        if recent_commands > 0:
            successful = len([cmd for cmd in self.command_history if cmd.get('success')])
            successful_rate = (successful / recent_commands) * 100
        
        ColoredOutput.print(f"\n📊 Command History:", 'cyan', bold=True)
        ColoredOutput.print(f"  Total commands: {recent_commands}", 'white')
        ColoredOutput.print(f"  Success rate: {successful_rate:.1f}%", 'white')
        
        # Configuration location
        ColoredOutput.print(f"\n📂 Configuration Files:", 'cyan', bold=True)
        ColoredOutput.print(f"  Config dir: {self.config_dir}", 'white')
        ColoredOutput.print(f"  Config file: {self.config_file.exists()}", 'white')
        ColoredOutput.print(f"  Devices file: {self.devices_file.exists()}", 'white')
        ColoredOutput.print(f"  History file: {self.history_file.exists()}", 'white')


# Global config manager instance
_config_manager = None

def get_config_manager() -> ConfigManager:
    """Get the global configuration manager instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def cmd_config(args) -> Dict[str, Any]:
    """Configuration management command."""
    config = get_config_manager()
    
    if args.subcommand == 'show':
        config.show_status()
        return {"status": "success"}
    
    elif args.subcommand == 'reset':
        confirm = input("Are you sure you want to reset all configuration? (y/N): ")
        if confirm.lower() in ['y', 'yes']:
            config.reset_config()
            ColoredOutput.success("Configuration reset to defaults")
        else:
            ColoredOutput.info("Reset cancelled")
        return {"status": "success"}
    
    elif args.subcommand == 'add-device':
        profile = config.add_device_profile(
            name=args.name,
            ip=args.ip,
            port=args.port,
            use_ssl=args.use_ssl,
            alias=args.alias or ""
        )
        ColoredOutput.success(f"Added device profile: {profile.name}")
        return {"status": "success", "profile": asdict(profile)}
    
    elif args.subcommand == 'remove-device':
        if config.remove_device_profile(args.name):
            ColoredOutput.success(f"Removed device profile: {args.name}")
        else:
            ColoredOutput.error(f"Device profile not found: {args.name}")
        return {"status": "success"}
    
    elif args.subcommand == 'list-devices':
        profiles = config.list_device_profiles()
        if profiles:
            ColoredOutput.header("📱 Device Profiles")
            for profile in profiles:
                alias_text = f" ({profile.alias})" if profile.alias else ""
                ssl_text = " (SSL)" if profile.use_ssl else ""
                ColoredOutput.print(f"  • {profile.name}{alias_text}: {profile.ip}:{profile.port}{ssl_text}", 'cyan')
                if profile.notes:
                    ColoredOutput.print(f"    Notes: {profile.notes}", 'gray')
        else:
            ColoredOutput.warning("No device profiles configured")
        return {"status": "success", "profiles": [asdict(p) for p in profiles]}
    
    elif args.subcommand == 'export':
        config.export_config(args.file)
        ColoredOutput.success(f"Configuration exported to {args.file}")
        return {"status": "success"}
    
    elif args.subcommand == 'import':
        config.import_config(args.file)
        ColoredOutput.success(f"Configuration imported from {args.file}")
        return {"status": "success"}
    
    elif args.subcommand == 'set':
        # Set a preference
        if hasattr(config.preferences, args.key):
            # Convert string values to appropriate types
            value = args.value
            current_value = getattr(config.preferences, args.key)
            if isinstance(current_value, bool):
                value = value.lower() in ['true', '1', 'yes', 'on']
            elif isinstance(current_value, int):
                value = int(value)
            
            config.update_preferences(**{args.key: value})
            ColoredOutput.success(f"Set {args.key} = {value}")
        else:
            ColoredOutput.error(f"Unknown preference: {args.key}")
        return {"status": "success"}
    
    else:
        ColoredOutput.error(f"Unknown config subcommand: {args.subcommand}")
        return {"status": "error", "message": f"Unknown subcommand: {args.subcommand}"}


def apply_user_preferences(args):
    """Apply user preferences to command line arguments."""
    config = get_config_manager()
    prefs = config.preferences
    
    # Apply defaults if not explicitly set
    if not hasattr(args, 'timeout') or args.timeout == 10:  # Default timeout
        args.timeout = prefs.default_timeout
    
    if not hasattr(args, 'network') or not args.network:
        if prefs.default_network:
            args.network = prefs.default_network
    
    if not hasattr(args, 'verbose') or not args.verbose:
        args.verbose = prefs.verbose_by_default
    
    if not hasattr(args, 'stealth') or not args.stealth:
        args.stealth = prefs.stealth_mode
    
    # Try to resolve device from profiles
    if hasattr(args, 'host') and args.host:
        profile = config.get_device_profile(args.host)
        if profile:
            args.host = profile.ip
            args.port = profile.port
            args.use_ssl = profile.use_ssl
            ColoredOutput.info(f"Using device profile: {profile.name} ({profile.ip}:{profile.port})")


def create_config_parser(subparsers):
    """Create configuration management subparser."""
    config_parser = subparsers.add_parser('config', help='Configuration management')
    config_subparsers = config_parser.add_subparsers(dest='subcommand', help='Config commands')
    
    # Show configuration
    config_subparsers.add_parser('show', help='Show current configuration')
    
    # Reset configuration
    config_subparsers.add_parser('reset', help='Reset configuration to defaults')
    
    # Device management
    add_device_parser = config_subparsers.add_parser('add-device', help='Add device profile')
    add_device_parser.add_argument('name', help='Device profile name')
    add_device_parser.add_argument('ip', help='Device IP address')
    add_device_parser.add_argument('--port', type=int, default=1400, help='Device port')
    add_device_parser.add_argument('--use-ssl', action='store_true', help='Use SSL')
    add_device_parser.add_argument('--alias', help='Device alias')
    
    remove_device_parser = config_subparsers.add_parser('remove-device', help='Remove device profile')
    remove_device_parser.add_argument('name', help='Device profile name')
    
    config_subparsers.add_parser('list-devices', help='List device profiles')
    
    # Export/Import
    export_parser = config_subparsers.add_parser('export', help='Export configuration')
    export_parser.add_argument('file', help='Export file path')
    
    import_parser = config_subparsers.add_parser('import', help='Import configuration')
    import_parser.add_argument('file', help='Import file path')
    
    # Set preferences
    set_parser = config_subparsers.add_parser('set', help='Set preference value')
    set_parser.add_argument('key', help='Preference key')
    set_parser.add_argument('value', help='Preference value')
    
    return config_parser