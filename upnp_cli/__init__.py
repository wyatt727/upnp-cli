"""
Ultimate UPnP Pentest & Control CLI

A modular, extensible command-line toolkit for discovering, enumerating, and controlling
any UPnP-compliant device (e.g. Sonos, Chromecast, Roku, smart TVs, media renderers, etc.).
Built for penetration testers, red teams, and network administrators.
"""

__version__ = "0.1.0"
__author__ = "UPnP CLI Team"
__description__ = "Ultimate UPnP Pentest & Control CLI"

# Core modules
from . import config
from . import logging_utils
from . import utils

__all__ = [
    "__version__",
    "__author__", 
    "__description__",
    "config",
    "logging_utils",
    "utils",
] 