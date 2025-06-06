#!/usr/bin/env python3
"""
UX Improvements Module

Enhanced user experience features including intelligent help,
command suggestions, tutorials, and improved navigation.
"""

import sys
import readline
import difflib
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

from upnp_cli.cli.output import ColoredOutput


class SmartHelp:
    """Enhanced help system with examples and suggestions."""
    
    COMMAND_EXAMPLES = {
        'discover': [
            'upnp-cli discover',
            'upnp-cli discover --ssdp-only',
            'upnp-cli discover --network 192.168.1.0/24 --json'
        ],
        'play': [
            'upnp-cli play --host 192.168.1.100',
            'upnp-cli play --host 192.168.1.100 --use-ssl',
            'upnp-cli --host 192.168.1.100 play  # Auto-discover'
        ],
        'interactive': [
            'upnp-cli interactive --host 192.168.1.100',
            'upnp-cli interactive  # Auto-discover first device'
        ],
        'mass-scan': [
            'upnp-cli mass-scan --save-report scan_results.json',
            'upnp-cli mass-scan --minimal --json'
        ]
    }
    
    COMMAND_DESCRIPTIONS = {
        'discover': 'Find UPnP devices on your network',
        'info': 'Get detailed information about a specific device',
        'services': 'List all services available on a device',
        'play': 'Start media playback on a device',
        'pause': 'Pause media playback',
        'stop': 'Stop media playback',
        'interactive': 'Interactive SOAP action controller (most powerful)',
        'mass-scan': 'Scan and prioritize multiple devices',
        'auto-profile': 'Comprehensive device fuzzing and profiling',
        'ssl-scan': 'Security scan for SSL/TLS vulnerabilities',
        'rtsp-scan': 'Discover RTSP video streams'
    }
    
    WORKFLOWS = {
        'getting_started': [
            ('1. Discover devices', 'upnp-cli discover'),
            ('2. Get device info', 'upnp-cli info --host <IP>'),
            ('3. List services', 'upnp-cli services --host <IP>'),
            ('4. Interactive control', 'upnp-cli interactive --host <IP>')
        ],
        'media_control': [
            ('1. Auto-discover', 'upnp-cli discover'),
            ('2. Start playback', 'upnp-cli play'),
            ('3. Control volume', 'upnp-cli set-volume 50'),
            ('4. Stop playback', 'upnp-cli stop')
        ],
        'security_testing': [
            ('1. Mass scan network', 'upnp-cli mass-scan --save-report'),
            ('2. Auto-profile devices', 'upnp-cli auto-profile --aggressive'),
            ('3. SSL vulnerability scan', 'upnp-cli ssl-scan'),
            ('4. Interactive SOAP testing', 'upnp-cli interactive')
        ]
    }
    
    @classmethod
    def show_command_help(cls, command: str, full_help: bool = False):
        """Show enhanced help for a specific command."""
        ColoredOutput.header(f"Help: {command}")
        
        # Description
        description = cls.COMMAND_DESCRIPTIONS.get(command, "No description available")
        ColoredOutput.info(description)
        
        # Examples
        examples = cls.COMMAND_EXAMPLES.get(command, [])
        if examples:
            ColoredOutput.print("\n📚 Examples:", 'cyan', bold=True)
            for i, example in enumerate(examples, 1):
                ColoredOutput.print(f"  {i}. {example}", 'yellow')
        
        # Related commands
        related = cls._get_related_commands(command)
        if related:
            ColoredOutput.print("\n🔗 Related commands:", 'cyan', bold=True)
            for cmd in related:
                desc = cls.COMMAND_DESCRIPTIONS.get(cmd, "")
                ColoredOutput.print(f"  • {cmd} - {desc}", 'white')
    
    @classmethod
    def show_workflow_help(cls, workflow: str):
        """Show step-by-step workflow help."""
        if workflow not in cls.WORKFLOWS:
            ColoredOutput.error(f"Unknown workflow: {workflow}")
            ColoredOutput.info(f"Available workflows: {', '.join(cls.WORKFLOWS.keys())}")
            return
        
        ColoredOutput.header(f"Workflow: {workflow.replace('_', ' ').title()}")
        
        steps = cls.WORKFLOWS[workflow]
        for step_desc, command in steps:
            ColoredOutput.print(f"  {step_desc}", 'cyan', bold=True)
            ColoredOutput.print(f"    $ {command}", 'yellow')
            ColoredOutput.print("")
    
    @classmethod
    def suggest_commands(cls, partial: str) -> List[str]:
        """Suggest commands based on partial input."""
        all_commands = list(cls.COMMAND_DESCRIPTIONS.keys())
        
        # Exact matches first
        exact_matches = [cmd for cmd in all_commands if cmd.startswith(partial)]
        
        # Fuzzy matches
        fuzzy_matches = difflib.get_close_matches(partial, all_commands, n=5, cutoff=0.3)
        
        # Combine and deduplicate
        suggestions = exact_matches + [cmd for cmd in fuzzy_matches if cmd not in exact_matches]
        
        return suggestions[:5]  # Limit to 5 suggestions
    
    @classmethod
    def _get_related_commands(cls, command: str) -> List[str]:
        """Get commands related to the given command."""
        related_groups = {
            'discover': ['info', 'services', 'mass-scan'],
            'info': ['discover', 'services', 'interactive'],
            'services': ['info', 'interactive', 'scpd-analyze'],
            'play': ['pause', 'stop', 'set-volume', 'get-volume'],
            'pause': ['play', 'stop'],
            'stop': ['play', 'pause'],
            'interactive': ['services', 'scpd-analyze'],
            'mass-scan': ['discover', 'auto-profile'],
            'auto-profile': ['mass-scan', 'ssl-scan'],
            'ssl-scan': ['rtsp-scan', 'auto-profile']
        }
        
        return related_groups.get(command, [])


class InteractiveInput:
    """Enhanced input handling with autocomplete and history."""
    
    def __init__(self):
        self.history = []
        self.setup_readline()
    
    def setup_readline(self):
        """Configure readline for better input experience."""
        try:
            # Set up history
            histfile = Path.home() / '.upnp_cli_history'
            try:
                readline.read_history_file(str(histfile))
            except FileNotFoundError:
                pass
            
            # Save history on exit
            import atexit
            atexit.register(readline.write_history_file, str(histfile))
            
            # Set history length
            readline.set_history_length(1000)
            
            # Enable tab completion
            readline.parse_and_bind('tab: complete')
            
        except ImportError:
            # readline not available on some systems
            pass
    
    def get_input(self, prompt: str, suggestions: Optional[List[str]] = None, 
                  validator: Optional[callable] = None) -> str:
        """Get user input with validation and suggestions."""
        
        # Set up tab completion if suggestions provided
        if suggestions:
            self._setup_completion(suggestions)
        
        while True:
            try:
                user_input = input(ColoredOutput.format_text(prompt, 'yellow')).strip()
                
                # Validate input
                if validator:
                    if not validator(user_input):
                        ColoredOutput.warning("Invalid input. Please try again.")
                        continue
                
                # Add to history
                if user_input and user_input not in self.history[-5:]:  # Avoid recent duplicates
                    self.history.append(user_input)
                
                return user_input
                
            except KeyboardInterrupt:
                raise KeyboardInterrupt
            except EOFError:
                return ""
    
    def _setup_completion(self, suggestions: List[str]):
        """Set up tab completion for the current input."""
        def completer(text, state):
            matches = [s for s in suggestions if s.startswith(text)]
            if state < len(matches):
                return matches[state]
            return None
        
        try:
            readline.set_completer(completer)
        except:
            pass  # readline not available


class NavigationHelper:
    """Enhanced navigation with breadcrumbs and shortcuts."""
    
    def __init__(self):
        self.breadcrumb = []
        self.shortcuts = {
            'q': 'quit',
            'b': 'back',
            'h': 'help',
            'm': 'menu',
            '?': 'help'
        }
    
    def push_location(self, location: str):
        """Add a location to the breadcrumb trail."""
        self.breadcrumb.append(location)
    
    def pop_location(self) -> Optional[str]:
        """Remove and return the last location."""
        return self.breadcrumb.pop() if self.breadcrumb else None
    
    def show_breadcrumb(self):
        """Display the current navigation breadcrumb."""
        if self.breadcrumb:
            path = " > ".join(self.breadcrumb)
            ColoredOutput.print(f"📍 Location: {path}", 'gray')
    
    def show_shortcuts(self):
        """Display available shortcuts."""
        ColoredOutput.print("\n⚡ Shortcuts:", 'cyan', bold=True)
        for shortcut, action in self.shortcuts.items():
            ColoredOutput.print(f"  {shortcut} - {action}", 'white')
    
    def handle_shortcut(self, input_text: str) -> Optional[str]:
        """Handle shortcut input and return the action."""
        return self.shortcuts.get(input_text.lower())


class ProgressTracker:
    """Enhanced progress tracking with detailed feedback."""
    
    def __init__(self, total_steps: int, operation_name: str):
        self.total_steps = total_steps
        self.current_step = 0
        self.operation_name = operation_name
        self.start_time = None
        self.step_details = []
    
    def start(self):
        """Start tracking progress."""
        import time
        self.start_time = time.time()
        ColoredOutput.header(f"🚀 Starting: {self.operation_name}")
    
    def update(self, step_name: str, details: str = ""):
        """Update progress with step information."""
        self.current_step += 1
        self.step_details.append((step_name, details))
        
        # Progress bar
        progress = self.current_step / self.total_steps
        bar_length = 20
        filled = int(bar_length * progress)
        bar = "█" * filled + "░" * (bar_length - filled)
        
        percentage = int(progress * 100)
        
        ColoredOutput.print(
            f"[{bar}] {percentage}% - {step_name}", 'cyan'
        )
        
        if details:
            ColoredOutput.print(f"  {details}", 'white')
    
    def finish(self, success: bool = True, summary: str = ""):
        """Complete progress tracking with summary."""
        if self.start_time:
            import time
            elapsed = time.time() - self.start_time
            
            if success:
                ColoredOutput.success(f"✅ {self.operation_name} completed in {elapsed:.2f}s")
            else:
                ColoredOutput.error(f"❌ {self.operation_name} failed after {elapsed:.2f}s")
            
            if summary:
                ColoredOutput.info(summary)


class TutorialSystem:
    """Interactive tutorial system for new users."""
    
    TUTORIALS = {
        'basic': {
            'title': 'UPnP CLI Basics',
            'steps': [
                {
                    'title': 'Welcome to UPnP CLI',
                    'content': 'This tool helps you discover and control UPnP devices on your network.',
                    'action': None
                },
                {
                    'title': 'Device Discovery', 
                    'content': 'First, let\'s discover devices on your network.',
                    'action': 'upnp-cli discover'
                },
                {
                    'title': 'Device Information',
                    'content': 'Get detailed information about a device.',
                    'action': 'upnp-cli info --host <IP>'
                },
                {
                    'title': 'Interactive Control',
                    'content': 'Use interactive mode for full control.',
                    'action': 'upnp-cli interactive --host <IP>'
                }
            ]
        },
        'security': {
            'title': 'Security Testing Tutorial',
            'steps': [
                {
                    'title': 'Mass Network Scanning',
                    'content': 'Scan your entire network for UPnP devices.',
                    'action': 'upnp-cli mass-scan'
                },
                {
                    'title': 'Device Profiling',
                    'content': 'Generate comprehensive device profiles.',
                    'action': 'upnp-cli auto-profile --aggressive'
                },
                {
                    'title': 'SSL Vulnerability Testing',
                    'content': 'Test for SSL/TLS vulnerabilities.',
                    'action': 'upnp-cli ssl-scan --host <IP>'
                }
            ]
        }
    }
    
    @classmethod
    def run_tutorial(cls, tutorial_name: str = 'basic'):
        """Run an interactive tutorial."""
        if tutorial_name not in cls.TUTORIALS:
            ColoredOutput.error(f"Tutorial '{tutorial_name}' not found")
            ColoredOutput.info(f"Available tutorials: {', '.join(cls.TUTORIALS.keys())}")
            return
        
        tutorial = cls.TUTORIALS[tutorial_name]
        ColoredOutput.header(f"📚 Tutorial: {tutorial['title']}")
        
        for i, step in enumerate(tutorial['steps'], 1):
            ColoredOutput.print(f"\n📖 Step {i}: {step['title']}", 'cyan', bold=True)
            ColoredOutput.print(f"   {step['content']}", 'white')
            
            if step['action']:
                ColoredOutput.print(f"\n💡 Try this command:", 'yellow')
                ColoredOutput.print(f"   $ {step['action']}", 'green')
            
            try:
                input(ColoredOutput.format_text("\n⏭️  Press Enter to continue (Ctrl+C to exit)...", 'gray'))
            except KeyboardInterrupt:
                ColoredOutput.warning("\n📚 Tutorial interrupted")
                return
        
        ColoredOutput.success("🎉 Tutorial completed! You're ready to use UPnP CLI.")


def show_main_menu():
    """Display an enhanced main menu with workflows."""
    ColoredOutput.header("🎮 UPnP CLI - Interactive Menu")
    
    ColoredOutput.print("🔍 Quick Actions:", 'cyan', bold=True)
    ColoredOutput.print("  1. Discover devices on network", 'white')
    ColoredOutput.print("  2. Control media devices", 'white')  
    ColoredOutput.print("  3. Security testing workflow", 'white')
    ColoredOutput.print("  4. Interactive device control", 'white')
    
    ColoredOutput.print("\n📚 Learning:", 'cyan', bold=True)
    ColoredOutput.print("  5. Run basic tutorial", 'white')
    ColoredOutput.print("  6. Run security tutorial", 'white')
    ColoredOutput.print("  7. Show command examples", 'white')
    
    ColoredOutput.print("\n⚙️  Advanced:", 'cyan', bold=True)
    ColoredOutput.print("  8. Comprehensive device profiling", 'white')
    ColoredOutput.print("  9. Custom SOAP actions", 'white')
    ColoredOutput.print("  0. Exit", 'red')
    
    print()  # Extra spacing


def handle_menu_choice(choice: str) -> Optional[str]:
    """Handle main menu choice and return command to execute."""
    menu_commands = {
        '1': 'discover',
        '2': 'play',  # Will auto-discover
        '3': 'mass-scan',
        '4': 'interactive',
        '5': 'tutorial:basic',
        '6': 'tutorial:security', 
        '7': 'help:examples',
        '8': 'auto-profile',
        '9': 'interactive',
        '0': 'exit'
    }
    
    return menu_commands.get(choice)