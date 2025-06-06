#!/usr/bin/env python3
"""
CLI Commands Package

Organized command modules for the UPnP CLI toolkit.
"""

# Import command modules for easy access
from . import discovery
from . import scpd_analysis
from . import interactive_control
from . import media_control
from . import security_scanning
from . import routine_commands
from . import mass_operations
from . import cache_server
from . import auto_profile

__all__ = [
    'discovery',
    'scpd_analysis', 
    'interactive_control',
    'media_control',
    'security_scanning',
    'routine_commands',
    'mass_operations',
    'cache_server',
    'auto_profile'
] 