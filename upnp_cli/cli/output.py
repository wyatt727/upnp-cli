#!/usr/bin/env python3
"""
CLI Output Utilities

This module provides colored console output and progress reporting utilities
for the UPnP CLI toolkit.
"""

import sys
import time
from typing import List, Dict, Any, Optional


class ColoredOutput:
    """Utility class for colored console output."""
    
    COLORS = {
        'red': '\033[91m',
        'green': '\033[92m', 
        'yellow': '\033[93m',
        'blue': '\033[94m',
        'magenta': '\033[95m',
        'cyan': '\033[96m',
        'white': '\033[97m',
        'gray': '\033[90m',
        'bold': '\033[1m',
        'underline': '\033[4m',
        'reset': '\033[0m'
    }
    
    @classmethod
    def print(cls, text: str, color: str = 'white', bold: bool = False, end: str = '\n'):
        """Print colored text to console."""
        if not sys.stdout.isatty():
            print(text, end=end)
            return
            
        color_code = cls.COLORS.get(color, cls.COLORS['white'])
        if bold:
            color_code += cls.COLORS['bold']
        print(f"{color_code}{text}{cls.COLORS['reset']}", end=end)
    
    @classmethod
    def success(cls, text: str):
        """Print success message in green."""
        cls.print(f"✅ {text}", 'green', bold=True)
    
    @classmethod
    def error(cls, text: str):
        """Print error message in red."""
        cls.print(f"❌ {text}", 'red', bold=True)
    
    @classmethod
    def warning(cls, text: str):
        """Print warning message in yellow."""
        cls.print(f"⚠️ {text}", 'yellow', bold=True)
    
    @classmethod
    def info(cls, text: str):
        """Print info message in cyan."""
        cls.print(f"ℹ️ {text}", 'cyan')
    
    @classmethod
    def header(cls, text: str):
        """Print header in bold blue."""
        cls.print(f"\n🔍 {text}", 'blue', bold=True)
    
    @classmethod
    def format_text(cls, text: str, color: str = 'white', bold: bool = False) -> str:
        """Format text with color codes but return as string instead of printing."""
        if not sys.stdout.isatty():
            return text
            
        color_code = cls.COLORS.get(color, cls.COLORS['white'])
        if bold:
            color_code += cls.COLORS['bold']
        return f"{color_code}{text}{cls.COLORS['reset']}"


class ProgressReporter:
    """Simple progress reporting for long-running operations."""
    
    def __init__(self, total: int, description: str = "Processing"):
        self.total = total
        self.current = 0
        self.description = description
        self.start_time = time.time()
    
    def update(self, increment: int = 1, message: str = ""):
        """Update progress and optionally print status."""
        self.current += increment
        if message:
            elapsed = time.time() - self.start_time
            rate = self.current / elapsed if elapsed > 0 else 0
            ColoredOutput.print(
                f"[{self.current}/{self.total}] {self.description}: {message} "
                f"({rate:.1f}/sec)", 'cyan'
            )
    
    def finish(self, final_message: str = ""):
        """Mark progress as complete."""
        elapsed = time.time() - self.start_time
        ColoredOutput.success(
            f"{self.description} complete! {self.current}/{self.total} "
            f"processed in {elapsed:.2f}s. {final_message}"
        ) 