#!/usr/bin/env python3
"""
Enhanced SCPD Parser

This module provides comprehensive parsing of UPnP Service Control Protocol 
Description (SCPD) files to extract complete action inventories with full 
argument specifications.

Implements ADR-015: Comprehensive SOAP Action Discovery from SCPD Files
"""

import logging
import aiohttp
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from urllib.parse import urljoin, urlparse
import xml.etree.ElementTree as ET

# Import robust XML parsing from discovery module - fix import mess
import sys
from pathlib import Path

# Ensure we can import from the upnp_cli package
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import upnp_cli.discovery as discovery

logger = logging.getLogger(__name__)


class SCPDParsingError(Exception):
    """Exception raised when SCPD parsing fails."""
    pass


class ActionArgument:
    """Represents a SOAP action argument with full specifications."""
    
    def __init__(self, name: str, direction: str, related_state_variable: str = ""):
        self.name = name
        self.direction = direction  # "in" or "out"
        self.related_state_variable = related_state_variable
        self.data_type = ""
        self.allowed_values = []
        self.default_value = ""
        self.minimum = None
        self.maximum = None
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        result = {
            "name": self.name,
            "direction": self.direction,
            "relatedStateVariable": self.related_state_variable
        }
        
        if self.data_type:
            result["dataType"] = self.data_type
        if self.allowed_values:
            result["allowedValues"] = self.allowed_values
        if self.default_value:
            result["defaultValue"] = self.default_value
        if self.minimum is not None:
            result["minimum"] = self.minimum
        if self.maximum is not None:
            result["maximum"] = self.maximum
            
        return result


class SOAPAction:
    """Represents a complete SOAP action with arguments and metadata."""
    
    def __init__(self, name: str):
        self.name = name
        self.arguments_in = []  # List of ActionArgument
        self.arguments_out = []  # List of ActionArgument
        self.description = ""
        
    def add_argument(self, argument: ActionArgument):
        """Add an argument to the appropriate list."""
        if argument.direction.lower() == "in":
            self.arguments_in.append(argument)
        else:
            self.arguments_out.append(argument)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "name": self.name,
            "description": self.description,
            "arguments_in": [arg.to_dict() for arg in self.arguments_in],
            "arguments_out": [arg.to_dict() for arg in self.arguments_out],
            "total_arguments": len(self.arguments_in) + len(self.arguments_out)
        }


class StateVariable:
    """Represents a UPnP state variable with data type and constraints."""
    
    def __init__(self, name: str, data_type: str):
        self.name = name
        self.data_type = data_type
        self.send_events = True
        self.allowed_values = []
        self.default_value = ""
        self.minimum = None
        self.maximum = None
        self.step = None
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        result = {
            "name": self.name,
            "dataType": self.data_type,
            "sendEvents": self.send_events
        }
        
        if self.allowed_values:
            result["allowedValues"] = self.allowed_values
        if self.default_value:
            result["defaultValue"] = self.default_value
        if self.minimum is not None:
            result["minimum"] = self.minimum
        if self.maximum is not None:
            result["maximum"] = self.maximum
        if self.step is not None:
            result["step"] = self.step
            
        return result


class SCPDDocument:
    """Represents a complete parsed SCPD document."""
    
    def __init__(self, service_type: str, scpd_url: str):
        self.service_type = service_type
        self.scpd_url = scpd_url
        self.actions = {}  # Dict[str, SOAPAction]
        self.state_variables = {}  # Dict[str, StateVariable]
        self.spec_version = {"major": 1, "minor": 0}
        self.parsing_success = False
        self.parsing_errors = []
        
    def add_action(self, action: SOAPAction):
        """Add a SOAP action to the document."""
        self.actions[action.name] = action
        
    def add_state_variable(self, variable: StateVariable):
        """Add a state variable to the document."""
        self.state_variables[variable.name] = variable
        
    def get_action_count(self) -> int:
        """Get total number of actions."""
        return len(self.actions)
        
    def get_actions_with_arguments(self) -> List[SOAPAction]:
        """Get actions that have input arguments."""
        return [action for action in self.actions.values() if action.arguments_in]
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "service_type": self.service_type,
            "scpd_url": self.scpd_url,
            "spec_version": self.spec_version,
            "parsing_success": self.parsing_success,
            "parsing_errors": self.parsing_errors,
            "action_count": self.get_action_count(),
            "actions": {name: action.to_dict() for name, action in self.actions.items()},
            "state_variables": {name: var.to_dict() for name, var in self.state_variables.items()}
        }


class EnhancedSCPDParser:
    """Enhanced SCPD parser with comprehensive action discovery."""
    
    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.session = None
        
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout),
            connector=aiohttp.TCPConnector(ssl=False)
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
            
    async def fetch_and_parse_scpd(self, base_url: str, scpd_path: str, service_type: str) -> SCPDDocument:
        """
        Fetch and comprehensively parse an SCPD file.
        
        Args:
            base_url: Base URL of the device
            scpd_path: Relative path to SCPD file
            service_type: UPnP service type
            
        Returns:
            SCPDDocument with complete action and state variable information
        """
        scpd_url = urljoin(base_url, scpd_path)
        logger.debug(f"Fetching SCPD from: {scpd_url}")
        
        document = SCPDDocument(service_type, scpd_url)
        
        try:
            # Fetch SCPD content
            content = await self._fetch_scpd_content(scpd_url)
            if not content:
                document.parsing_errors.append("Failed to fetch SCPD content")
                return document
                
            # Parse SCPD XML
            await self._parse_scpd_content(content, document)
            
            # Resolve state variable references in arguments
            self._resolve_state_variable_references(document)
            
            document.parsing_success = True
            logger.info(f"Successfully parsed SCPD for {service_type}: {document.get_action_count()} actions")
            
        except Exception as e:
            error_msg = f"SCPD parsing failed for {service_type}: {e}"
            logger.error(error_msg)
            document.parsing_errors.append(error_msg)
            
        return document
        
    async def _fetch_scpd_content(self, scpd_url: str) -> Optional[str]:
        """Fetch SCPD content with error handling."""
        try:
            async with self.session.get(scpd_url) as response:
                if response.status == 200:
                    content = await response.text()
                    logger.debug(f"Fetched SCPD content: {len(content)} characters")
                    return content
                else:
                    logger.warning(f"SCPD fetch failed with status {response.status}: {scpd_url}")
                    return None
        except Exception as e:
            logger.error(f"Exception fetching SCPD from {scpd_url}: {e}")
            return None
            
    async def _parse_scpd_content(self, content: str, document: SCPDDocument):
        """Parse SCPD XML content using robust parsing."""
        # Clean and prepare XML content
        content = discovery._sanitize_xml_content(content)
        content = discovery._remove_xml_namespaces(content)
        
        # Parse with fallbacks
        root = discovery._parse_xml_with_fallbacks(content)
        if root is None:
            raise SCPDParsingError("Could not parse SCPD XML")
            
        # Parse spec version
        self._parse_spec_version(root, document)
        
        # Parse action list
        await self._parse_action_list(root, document)
        
        # Parse service state table
        self._parse_state_table(root, document)
        
    def _parse_spec_version(self, root: ET.Element, document: SCPDDocument):
        """Parse SCPD specification version."""
        try:
            spec_version = root.find('.//specVersion')
            if spec_version is not None:
                major_elem = spec_version.find('major')
                minor_elem = spec_version.find('minor')
                
                if major_elem is not None and major_elem.text:
                    document.spec_version["major"] = int(major_elem.text)
                if minor_elem is not None and minor_elem.text:
                    document.spec_version["minor"] = int(minor_elem.text)
                    
                logger.debug(f"SCPD spec version: {document.spec_version}")
        except Exception as e:
            logger.debug(f"Could not parse spec version: {e}")
            
    async def _parse_action_list(self, root: ET.Element, document: SCPDDocument):
        """Parse action list with comprehensive argument extraction."""
        # Find action list with multiple strategies
        action_list = None
        for tag in ['actionList', 'ActionList', 'ACTIONLIST']:
            action_list = root.find(f'.//{tag}')
            if action_list is not None:
                break
                
        if action_list is None:
            logger.warning("No actionList found in SCPD")
            return
            
        # Find all action elements
        action_elements = []
        for tag in ['action', 'Action', 'ACTION']:
            found = action_list.findall(tag)
            if found:
                action_elements.extend(found)
                
        logger.debug(f"Found {len(action_elements)} action elements")
        
        for action_elem in action_elements:
            try:
                action = await self._parse_single_action(action_elem)
                if action:
                    document.add_action(action)
            except Exception as e:
                error_msg = f"Failed to parse action: {e}"
                logger.warning(error_msg)
                document.parsing_errors.append(error_msg)
                continue
                
    async def _parse_single_action(self, action_elem: ET.Element) -> Optional[SOAPAction]:
        """Parse a single action element."""
        # Get action name
        name_elem = None
        for name_tag in ['name', 'Name', 'NAME']:
            name_elem = action_elem.find(name_tag)
            if name_elem is not None and name_elem.text:
                break
                
        if name_elem is None or not name_elem.text:
            logger.warning("Action element missing name")
            return None
            
        action_name = name_elem.text.strip()
        action = SOAPAction(action_name)
        
        # Parse description if available
        desc_elem = action_elem.find('description')
        if desc_elem is not None and desc_elem.text:
            action.description = desc_elem.text.strip()
            
        # Parse argument list
        arg_list = None
        for list_tag in ['argumentList', 'ArgumentList', 'ARGUMENTLIST']:
            arg_list = action_elem.find(list_tag)
            if arg_list is not None:
                break
                
        if arg_list is not None:
            await self._parse_argument_list(arg_list, action)
            
        logger.debug(f"Parsed action '{action_name}' with {len(action.arguments_in)} in args, {len(action.arguments_out)} out args")
        return action
        
    async def _parse_argument_list(self, arg_list: ET.Element, action: SOAPAction):
        """Parse argument list for an action."""
        # Find arguments
        arguments = []
        for arg_tag in ['argument', 'Argument', 'ARGUMENT']:
            found_args = arg_list.findall(arg_tag)
            if found_args:
                arguments.extend(found_args)
                
        for arg_elem in arguments:
            try:
                argument = self._parse_single_argument(arg_elem)
                if argument:
                    action.add_argument(argument)
            except Exception as e:
                logger.warning(f"Failed to parse argument in action {action.name}: {e}")
                continue
                
    def _parse_single_argument(self, arg_elem: ET.Element) -> Optional[ActionArgument]:
        """Parse a single argument element."""
        # Get argument name
        name_elem = None
        for name_tag in ['name', 'Name', 'NAME']:
            name_elem = arg_elem.find(name_tag)
            if name_elem is not None and name_elem.text:
                break
                
        # Get argument direction
        direction_elem = None
        for dir_tag in ['direction', 'Direction', 'DIRECTION']:
            direction_elem = arg_elem.find(dir_tag)
            if direction_elem is not None and direction_elem.text:
                break
                
        if name_elem is None or direction_elem is None:
            logger.warning("Argument missing name or direction")
            return None
            
        arg_name = name_elem.text.strip()
        arg_direction = direction_elem.text.strip().lower()
        
        # Get related state variable
        state_var_elem = None
        for var_tag in ['relatedStateVariable', 'RelatedStateVariable', 'RELATEDSTATEVARIABLE']:
            state_var_elem = arg_elem.find(var_tag)
            if state_var_elem is not None and state_var_elem.text:
                break
                
        related_var = state_var_elem.text.strip() if state_var_elem is not None and state_var_elem.text else ""
        
        argument = ActionArgument(arg_name, arg_direction, related_var)
        
        logger.debug(f"Parsed argument: {arg_name} ({arg_direction}) -> {related_var}")
        return argument
        
    def _parse_state_table(self, root: ET.Element, document: SCPDDocument):
        """Parse service state table."""
        # Find state table
        state_table = None
        for table_tag in ['serviceStateTable', 'ServiceStateTable', 'SERVICESTATETABLE']:
            state_table = root.find(f'.//{table_tag}')
            if state_table is not None:
                break
                
        if state_table is None:
            logger.debug("No serviceStateTable found in SCPD")
            return
            
        # Find state variables
        state_vars = []
        for var_tag in ['stateVariable', 'StateVariable', 'STATEVARIABLE']:
            found_vars = state_table.findall(var_tag)
            if found_vars:
                state_vars.extend(found_vars)
                
        logger.debug(f"Found {len(state_vars)} state variable elements")
        
        for var_elem in state_vars:
            try:
                state_var = self._parse_state_variable(var_elem)
                if state_var:
                    document.add_state_variable(state_var)
            except Exception as e:
                logger.warning(f"Failed to parse state variable: {e}")
                continue
                
    def _parse_state_variable(self, var_elem: ET.Element) -> Optional[StateVariable]:
        """Parse a single state variable."""
        # Get variable name
        name_elem = None
        for name_tag in ['name', 'Name', 'NAME']:
            name_elem = var_elem.find(name_tag)
            if name_elem is not None and name_elem.text:
                break
                
        # Get data type
        type_elem = None
        for type_tag in ['dataType', 'DataType', 'DATATYPE']:
            type_elem = var_elem.find(type_tag)
            if type_elem is not None and type_elem.text:
                break
                
        if name_elem is None or type_elem is None:
            logger.warning("State variable missing name or dataType")
            return None
            
        var_name = name_elem.text.strip()
        var_type = type_elem.text.strip()
        
        state_var = StateVariable(var_name, var_type)
        
        # Parse sendEvents attribute
        send_events = var_elem.get('sendEvents', 'yes')
        state_var.send_events = send_events.lower() == 'yes'
        
        # Parse allowed value list
        allowed_list = var_elem.find('allowedValueList')
        if allowed_list is not None:
            values = []
            for value_elem in allowed_list.findall('allowedValue'):
                if value_elem.text:
                    values.append(value_elem.text.strip())
            state_var.allowed_values = values
            
        # Parse allowed value range
        range_elem = var_elem.find('allowedValueRange')
        if range_elem is not None:
            min_elem = range_elem.find('minimum')
            max_elem = range_elem.find('maximum')
            step_elem = range_elem.find('step')
            
            if min_elem is not None and min_elem.text:
                try:
                    state_var.minimum = int(min_elem.text)
                except ValueError:
                    state_var.minimum = min_elem.text
                    
            if max_elem is not None and max_elem.text:
                try:
                    state_var.maximum = int(max_elem.text)
                except ValueError:
                    state_var.maximum = max_elem.text
                    
            if step_elem is not None and step_elem.text:
                try:
                    state_var.step = int(step_elem.text)
                except ValueError:
                    state_var.step = step_elem.text
                    
        # Parse default value
        default_elem = var_elem.find('defaultValue')
        if default_elem is not None and default_elem.text:
            state_var.default_value = default_elem.text.strip()
            
        logger.debug(f"Parsed state variable: {var_name} ({var_type})")
        return state_var
        
    def _resolve_state_variable_references(self, document: SCPDDocument):
        """Resolve state variable references in action arguments."""
        for action in document.actions.values():
            for argument in action.arguments_in + action.arguments_out:
                if argument.related_state_variable in document.state_variables:
                    state_var = document.state_variables[argument.related_state_variable]
                    argument.data_type = state_var.data_type
                    argument.allowed_values = state_var.allowed_values.copy()
                    argument.default_value = state_var.default_value
                    argument.minimum = state_var.minimum
                    argument.maximum = state_var.maximum


async def parse_device_scpds(device_info: Dict[str, Any], base_url: str, timeout: int = 10) -> List[SCPDDocument]:
    """
    Parse all SCPD files for a device's services.
    
    Args:
        device_info: Device information containing services
        base_url: Base URL for the device
        timeout: Request timeout
        
    Returns:
        List of parsed SCPD documents
    """
    services = device_info.get('services', [])
    
    # Also check for embedded devices (like Sonos MediaRenderer/MediaServer)
    embedded_devices = device_info.get('devices', [])
    for embedded_device in embedded_devices:
        embedded_services = embedded_device.get('services', [])
        services.extend(embedded_services)
        logger.info(f"Found embedded device: {embedded_device.get('deviceType', 'Unknown')} with {len(embedded_services)} services")
    
    if not services:
        logger.warning("No services found in device info (including embedded devices)")
        return []
        
    scpd_documents = []
    
    async with EnhancedSCPDParser(timeout) as parser:
        for service in services:
            service_type = service.get('serviceType', '')
            scpd_url = service.get('SCPDURL', '')
            
            if not service_type or not scpd_url:
                logger.warning(f"Service missing serviceType or SCPDURL: {service}")
                continue
                
            try:
                document = await parser.fetch_and_parse_scpd(base_url, scpd_url, service_type)
                scpd_documents.append(document)
                
                if document.parsing_success:
                    logger.info(f"Successfully parsed {document.get_action_count()} actions for {service_type}")
                else:
                    logger.warning(f"SCPD parsing failed for {service_type}: {document.parsing_errors}")
                    
            except Exception as e:
                logger.error(f"Exception parsing SCPD for {service_type}: {e}")
                continue
                
    return scpd_documents


async def generate_comprehensive_action_inventory(devices: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generate comprehensive action inventory for multiple devices.
    
    Args:
        devices: List of device information dictionaries
        
    Returns:
        Complete action inventory with statistics
    """
    inventory = {
        "total_devices": len(devices),
        "devices_parsed": 0,
        "total_services": 0,
        "total_actions": 0,
        "unique_actions": set(),
        "device_inventories": [],
        "action_statistics": {},
        "parsing_errors": []
    }
    
    for device in devices:
        try:
            ip = device.get('ip', 'unknown')
            port = device.get('port', 1400)
            base_url = f"http://{ip}:{port}"
            device_name = device.get('friendlyName', f"{ip}:{port}")
            
            logger.info(f"Generating action inventory for {device_name}")
            
            scpd_documents = await parse_device_scpds(device, base_url)
            
            device_inventory = {
                "device_name": device_name,
                "ip": ip,
                "port": port,
                "services_parsed": len(scpd_documents),
                "total_actions": 0,
                "services": []
            }
            
            for document in scpd_documents:
                service_info = {
                    "service_type": document.service_type,
                    "scpd_url": document.scpd_url,
                    "parsing_success": document.parsing_success,
                    "action_count": document.get_action_count(),
                    "actions": list(document.actions.keys()),
                    "parsing_errors": document.parsing_errors
                }
                
                device_inventory["services"].append(service_info)
                device_inventory["total_actions"] += document.get_action_count()
                
                # Update global statistics
                inventory["total_actions"] += document.get_action_count()
                inventory["unique_actions"].update(document.actions.keys())
                
                if document.parsing_errors:
                    inventory["parsing_errors"].extend(document.parsing_errors)
                    
            inventory["device_inventories"].append(device_inventory)
            inventory["devices_parsed"] += 1
            inventory["total_services"] += len(scpd_documents)
            
        except Exception as e:
            error_msg = f"Failed to generate inventory for device {device.get('friendlyName', 'Unknown')}: {e}"
            logger.error(error_msg)
            inventory["parsing_errors"].append(error_msg)
            
    # Convert set to list for JSON serialization
    inventory["unique_actions"] = list(inventory["unique_actions"])
    
    # Generate action statistics
    action_counts = {}
    for device_inv in inventory["device_inventories"]:
        for service in device_inv["services"]:
            for action in service["actions"]:
                action_counts[action] = action_counts.get(action, 0) + 1
                
    inventory["action_statistics"] = dict(sorted(action_counts.items(), key=lambda x: x[1], reverse=True))
    
    logger.info(f"Generated comprehensive inventory: {inventory['total_actions']} total actions, {len(inventory['unique_actions'])} unique actions")
    
    return inventory 