#!/usr/bin/env python3
"""
Profile Generation Package

Provides comprehensive device profile generation with enhanced SCPD parsing
and action discovery capabilities.
"""

from .scpd_parser import (
    EnhancedSCPDParser,
    SCPDDocument,
    SOAPAction,
    ActionArgument,
    StateVariable,
    parse_device_scpds,
    generate_comprehensive_action_inventory
)

from .enhanced_profile_generator import (
    generate_enhanced_profile_with_scpd,
    generate_enhanced_profiles_for_devices,
    save_enhanced_profiles
)

__all__ = [
    'EnhancedSCPDParser',
    'SCPDDocument', 
    'SOAPAction',
    'ActionArgument',
    'StateVariable',
    'parse_device_scpds',
    'generate_comprehensive_action_inventory',
    'generate_enhanced_profile_with_scpd',
    'generate_enhanced_profiles_for_devices',
    'save_enhanced_profiles'
] 