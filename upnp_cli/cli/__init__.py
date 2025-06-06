#!/usr/bin/env python3
"""
UPnP CLI Package

Main entry point for the refactored CLI system.
Provides command registration and argument parsing.
"""

from .output import ColoredOutput, ProgressReporter

# Import main_entry from the main cli.py module (avoiding naming conflict)
def main_entry():
    """Entry point for backward compatibility."""
    # Import here to avoid circular imports
    import importlib.util
    import os
    
    # Get the path to the cli.py file in the parent directory
    cli_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'cli.py')
    
    # Load the module
    spec = importlib.util.spec_from_file_location("main_cli", cli_path)
    main_cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(main_cli)
    
    return main_cli.main_entry()

__all__ = ['ColoredOutput', 'ProgressReporter', 'main_entry'] 