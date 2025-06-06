"""
Routines package for user-extensible UPnP pranks.

This package provides a plugin system for users to create and contribute
their own custom routines beyond the basic fart loop.
"""

import importlib
import inspect
import pkgutil
from pathlib import Path
from typing import Dict, List, Type, Any, Optional

from .base_routine import BaseRoutine


class RoutineManager:
    """Manager for discovering and executing user routines."""
    
    def __init__(self):
        self.routines: Dict[str, Type[BaseRoutine]] = {}
        self.loaded = False
    
    def discover_routines(self) -> None:
        """Discover all available routines in the routines directory."""
        if self.loaded:
            return
        
        routines_dir = Path(__file__).parent
        
        # Scan for Python files in routines directory
        for module_info in pkgutil.iter_modules([str(routines_dir)]):
            if module_info.name.startswith('_') or module_info.name == 'base_routine':
                continue
            
            try:
                module = importlib.import_module(f'routines.{module_info.name}')
                
                # Find BaseRoutine subclasses in the module
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if (issubclass(obj, BaseRoutine) and 
                        obj != BaseRoutine and 
                        hasattr(obj, 'name')):
                        
                        routine_name = obj.name.lower().replace(' ', '_')
                        self.routines[routine_name] = obj
                        
            except Exception as e:
                print(f"Warning: Failed to load routine module {module_info.name}: {e}")
        
        self.loaded = True
    
    def get_routine(self, name: str) -> Optional[Type[BaseRoutine]]:
        """Get a routine class by name."""
        self.discover_routines()
        return self.routines.get(name.lower())
    
    def list_routines(self) -> List[Dict[str, Any]]:
        """List all available routines with their metadata."""
        self.discover_routines()
        
        routine_list = []
        for name, routine_class in self.routines.items():
            routine_list.append({
                'name': name,
                'display_name': routine_class.name,
                'description': routine_class.description,
                'category': getattr(routine_class, 'category', 'misc'),
                'media_files': getattr(routine_class, 'media_files', []),
                'supported_protocols': getattr(routine_class, 'supported_protocols', ['upnp'])
            })
        
        return sorted(routine_list, key=lambda x: x['name'])
    
    def execute_routine(self, name: str, devices: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        """Execute a routine on the specified devices."""
        routine_class = self.get_routine(name)
        if not routine_class:
            return {'error': f'Routine "{name}" not found'}
        
        try:
            routine = routine_class()
            return routine.execute(devices, **kwargs)
        except Exception as e:
            return {'error': f'Failed to execute routine: {e}'}


# Global routine manager
_routine_manager = RoutineManager()


def get_routine_manager() -> RoutineManager:
    """Get the global routine manager."""
    return _routine_manager


def list_available_routines() -> List[Dict[str, Any]]:
    """List all available routines."""
    return _routine_manager.list_routines()


def execute_routine(name: str, devices: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
    """Execute a routine by name."""
    return _routine_manager.execute_routine(name, devices, **kwargs)


def get_routine_info(name: str) -> Optional[Dict[str, Any]]:
    """Get information about a specific routine."""
    routine_class = _routine_manager.get_routine(name)
    if not routine_class:
        return None
    
    return {
        'name': name,
        'display_name': routine_class.name,
        'description': routine_class.description,
        'category': getattr(routine_class, 'category', 'misc'),
        'media_files': getattr(routine_class, 'media_files', []),
        'supported_protocols': getattr(routine_class, 'supported_protocols', ['upnp']),
        'parameters': getattr(routine_class, 'parameters', {}),
        'examples': getattr(routine_class, 'examples', [])
    } 