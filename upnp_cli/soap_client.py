"""
SOAP client for UPnP control operations.

This module provides SOAP envelope construction, request/response handling,
and stealth mode capabilities for UPnP device control.
"""

import asyncio
import random
import time
from typing import Dict, Any, Optional, Union
import xml.etree.ElementTree as ET

import aiohttp
import requests

from . import config
from .logging_utils import get_logger

logger = get_logger(__name__)


class SOAPError(Exception):
    """Exception raised for SOAP-related errors."""
    
    def __init__(self, message: str, response_code: Optional[int] = None, soap_fault: Optional[str] = None):
        super().__init__(message)
        self.response_code = response_code
        self.soap_fault = soap_fault


class SOAPClient:
    """
    SOAP client for UPnP control operations.
    
    Supports both synchronous and asynchronous operations with stealth mode.
    """
    
    def __init__(self, stealth_mode: bool = False):
        """
        Initialize SOAP client.
        
        Args:
            stealth_mode: Enable stealth mode with randomized headers and timing
        """
        self.stealth_mode = stealth_mode
        self.session = None
        
        # User agents for stealth mode
        self.user_agents = config.USER_AGENTS.copy()
        
        logger.debug(f"SOAP client initialized (stealth_mode: {stealth_mode})")
    
    def build_soap_envelope(self, 
                          service_type: str, 
                          action: str, 
                          arguments: Optional[Dict[str, Any]] = None) -> str:
        """
        Build SOAP envelope for UPnP action.
        
        Args:
            service_type: UPnP service type (e.g., "urn:schemas-upnp-org:service:AVTransport:1")
            action: Action name (e.g., "Play", "Pause", "SetVolume")
            arguments: Action arguments
            
        Returns:
            Complete SOAP envelope as XML string
        """
        if arguments is None:
            arguments = {}
        
        # Create SOAP envelope
        envelope = ET.Element("s:Envelope")
        envelope.set("xmlns:s", "http://schemas.xmlsoap.org/soap/envelope/")
        envelope.set("s:encodingStyle", "http://schemas.xmlsoap.org/soap/encoding/")
        
        # Create SOAP body
        body = ET.SubElement(envelope, "s:Body")
        
        # Create action element
        action_element = ET.SubElement(body, f"u:{action}")
        action_element.set("xmlns:u", service_type)
        
        # Add arguments
        for arg_name, arg_value in arguments.items():
            arg_element = ET.SubElement(action_element, arg_name)
            if arg_value is not None:
                arg_element.text = str(arg_value)
        
        # Convert to string
        xml_str = ET.tostring(envelope, encoding='unicode', xml_declaration=True)
        
        logger.debug(f"Built SOAP envelope for {service_type}#{action}")
        return xml_str
    
    def _get_headers(self, service_type: str, action: str, content_length: int) -> Dict[str, str]:
        """Get HTTP headers for SOAP request."""
        headers = {
            'Content-Type': 'text/xml; charset="utf-8"',
            'SOAPAction': f'"{service_type}#{action}"',
            'Content-Length': str(content_length),
            'Connection': 'close'
        }
        
        if self.stealth_mode:
            # Add randomized user agent
            headers['User-Agent'] = random.choice(self.user_agents)
            
            # Add some realistic browser headers
            headers['Accept'] = '*/*'
            headers['Accept-Language'] = 'en-US,en;q=0.9'
            headers['Cache-Control'] = 'no-cache'
        
        return headers
    
    def _apply_stealth_delay(self) -> None:
        """Apply random delay for stealth mode."""
        if self.stealth_mode:
            delay = random.uniform(config.STEALTH_MIN_DELAY, config.STEALTH_MAX_DELAY)
            time.sleep(delay)
    
    def send_soap_request(self, 
                         host: str, 
                         port: int,
                         control_url: str,
                         service_type: str,
                         action: str,
                         arguments: Optional[Dict[str, Any]] = None,
                         use_ssl: bool = False,
                         verify_ssl: bool = True,
                         timeout: int = config.DEFAULT_HTTP_TIMEOUT) -> requests.Response:
        """
        Send synchronous SOAP request.
        
        Args:
            host: Target host
            port: Target port
            control_url: Service control URL path
            service_type: UPnP service type
            action: Action name
            arguments: Action arguments
            use_ssl: Use HTTPS
            verify_ssl: Verify SSL certificates
            timeout: Request timeout
            
        Returns:
            HTTP response object
            
        Raises:
            SOAPError: If SOAP fault or HTTP error occurs
        """
        # Build SOAP envelope
        soap_envelope = self.build_soap_envelope(service_type, action, arguments)
        
        # Build URL
        protocol = 'https' if use_ssl else 'http'
        url = f"{protocol}://{host}:{port}{control_url}"
        
        # Get headers
        headers = self._get_headers(service_type, action, len(soap_envelope))
        
        # Apply stealth delay
        self._apply_stealth_delay()
        
        try:
            logger.debug(f"Sending SOAP request to {url}")
            
            response = requests.post(
                url,
                data=soap_envelope,
                headers=headers,
                timeout=timeout,
                verify=verify_ssl if use_ssl else False
            )
            
            # Check for SOAP faults even in successful HTTP responses
            if response.status_code == 200:
                soap_fault = self._extract_soap_fault(response.text)
                if soap_fault:
                    raise SOAPError(f"SOAP fault: {soap_fault}", response.status_code, soap_fault)
            
            return response
        
        except requests.RequestException as e:
            logger.error(f"SOAP request failed: {e}")
            raise SOAPError(f"Request failed: {e}")
    
    async def send_soap_request_async(self, 
                                    session: aiohttp.ClientSession,
                                    host: str, 
                                    port: int,
                                    control_url: str,
                                    service_type: str,
                                    action: str,
                                    arguments: Optional[Dict[str, Any]] = None,
                                    use_ssl: bool = False,
                                    verify_ssl: bool = True,
                                    timeout: int = config.DEFAULT_HTTP_TIMEOUT) -> aiohttp.ClientResponse:
        """
        Send asynchronous SOAP request.
        
        Args:
            session: aiohttp session
            host: Target host
            port: Target port
            control_url: Service control URL path
            service_type: UPnP service type
            action: Action name
            arguments: Action arguments
            use_ssl: Use HTTPS
            verify_ssl: Verify SSL certificates
            timeout: Request timeout
            
        Returns:
            HTTP response object
            
        Raises:
            SOAPError: If SOAP fault or HTTP error occurs
        """
        # Build SOAP envelope
        soap_envelope = self.build_soap_envelope(service_type, action, arguments)
        
        # Build URL
        protocol = 'https' if use_ssl else 'http'
        url = f"{protocol}://{host}:{port}{control_url}"
        
        # Get headers
        headers = self._get_headers(service_type, action, len(soap_envelope))
        
        # Apply stealth delay
        if self.stealth_mode:
            delay = random.uniform(config.STEALTH_MIN_DELAY, config.STEALTH_MAX_DELAY)
            await asyncio.sleep(delay)
        
        try:
            logger.debug(f"Sending async SOAP request to {url}")
            
            ssl_context = None if verify_ssl else False
            
            async with session.post(
                url,
                data=soap_envelope,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=timeout),
                ssl=ssl_context
            ) as response:
                
                # Read response text within the context manager
                response_text = await response.text()
                
                # Check for SOAP faults
                if response.status == 200:
                    soap_fault = self._extract_soap_fault(response_text)
                    if soap_fault:
                        raise SOAPError(f"SOAP fault: {soap_fault}", response.status, soap_fault)
                
                # Create a response-like object with the data we need
                class AsyncResponseWrapper:
                    def __init__(self, status, headers, text, url):
                        self.status = status
                        self.headers = headers
                        self._text = text
                        self.url = url
                    
                    def text(self):
                        return self._text
                
                return AsyncResponseWrapper(
                    status=response.status,
                    headers=response.headers,
                    text=response_text,
                    url=response.url
                )
        
        except aiohttp.ClientError as e:
            logger.error(f"Async SOAP request failed: {e}")
            raise SOAPError(f"Request failed: {e}")
    
    def _extract_soap_fault(self, response_text: str) -> Optional[str]:
        """Extract SOAP fault from response."""
        try:
            root = ET.fromstring(response_text)
            
            # Look for SOAP fault
            fault = root.find('.//{http://schemas.xmlsoap.org/soap/envelope/}Fault')
            if fault is None:
                # Try without namespace
                fault = root.find('.//Fault')
            
            if fault is not None:
                fault_string = fault.find('.//faultstring')
                fault_code = fault.find('.//faultcode')
                
                if fault_string is not None:
                    return fault_string.text
                elif fault_code is not None:
                    return fault_code.text
                else:
                    return "Unknown SOAP fault"
        
        except Exception:
            # If we can't parse the response, assume no fault
            pass
        
        return None
    
    def parse_soap_response(self, 
                          response: Union[requests.Response, aiohttp.ClientResponse],
                          response_text: Optional[str] = None,
                          verbose: bool = False) -> Dict[str, Any]:
        """
        Parse SOAP response and extract useful information.
        
        Args:
            response: HTTP response object
            response_text: Response text (for aiohttp responses)
            verbose: Include detailed response information
            
        Returns:
            Parsed response data
        """
        result = {
            'status_code': response.status if hasattr(response, 'status') else response.status_code,
            'success': False,
            'data': {},
            'raw_response': ''
        }
        
        # Get response text
        if response_text is None:
            if hasattr(response, 'text'):
                if hasattr(response.text, '__call__'):
                    try:
                        # For requests.Response, this is sync
                        text_result = response.text()
                        if asyncio.iscoroutine(text_result):
                            # This is an aiohttp response in sync context
                            logger.error("Cannot get text from aiohttp response in sync context - response_text parameter required")
                            response_text = f"<Error: async response.text() in sync context>"
                        else:
                            response_text = text_result
                    except Exception as e:
                        logger.error(f"Failed to get response text: {e}")
                        response_text = f"<Error getting response text: {e}>"
                else:
                    response_text = response.text    # already text
            else:
                response_text = ''
        
        result['raw_response'] = response_text
        
        # Check if successful
        result['success'] = result['status_code'] == 200
        
        if result['success']:
            # Parse XML response
            try:
                root = ET.fromstring(response_text)
                
                # Extract response data from SOAP body
                body = root.find('.//{http://schemas.xmlsoap.org/soap/envelope/}Body')
                if body is None:
                    body = root.find('.//Body')
                
                if body is not None:
                    # Find the first child (the response element)
                    for child in body:
                        result['data'] = self._xml_element_to_dict(child)
                        break
            
            except Exception as e:
                logger.warning(f"Failed to parse SOAP response XML: {e}")
                result['data'] = {'parse_error': str(e)}
        
        # Add verbose information
        if verbose:
            if hasattr(response, 'headers'):
                result['headers'] = dict(response.headers)
            result['url'] = getattr(response, 'url', 'unknown')
        
        return result
    
    async def execute_soap_action(self,
                                control_url: str,
                                service_type: str,
                                action_name: str,
                                arguments: Optional[Dict[str, Any]] = None,
                                use_ssl: bool = False,
                                timeout: int = config.DEFAULT_HTTP_TIMEOUT) -> aiohttp.ClientResponse:
        """
        Execute a SOAP action using the provided control URL.
        
        Args:
            control_url: Full control URL (http://host:port/path)
            service_type: UPnP service type
            action_name: Action name
            arguments: Action arguments
            use_ssl: Use HTTPS
            timeout: Request timeout
            
        Returns:
            HTTP response object
        """
        # Parse control URL to extract host and port
        from urllib.parse import urlparse
        parsed = urlparse(control_url)
        
        host = parsed.hostname
        port = parsed.port or (443 if parsed.scheme == 'https' else 80)
        path = parsed.path
        
        if not host:
            raise SOAPError("Invalid control URL: could not extract host")
        
        # Create session if not exists
        if self.session is None:
            self.session = aiohttp.ClientSession()
        
        try:
            return await self.send_soap_request_async(
                session=self.session,
                host=host,
                port=port,
                control_url=path,
                service_type=service_type,
                action=action_name,
                arguments=arguments,
                use_ssl=use_ssl,
                timeout=timeout
            )
        except Exception as e:
            logger.error(f"SOAP action execution failed: {e}")
            raise SOAPError(f"Action execution failed: {e}")
    
    def _xml_element_to_dict(self, element: ET.Element) -> Dict[str, Any]:
        """Convert XML element to dictionary."""
        result = {}
        
        # Add element text
        if element.text and element.text.strip():
            if len(element) == 0:  # Leaf node
                return element.text.strip()
            else:
                result['_text'] = element.text.strip()
        
        # Add attributes
        if element.attrib:
            result['_attributes'] = element.attrib
        
        # Add child elements
        for child in element:
            tag = child.tag.split('}')[-1]  # Remove namespace
            child_data = self._xml_element_to_dict(child)
            
            if tag in result:
                # Multiple elements with same tag - convert to list
                if not isinstance(result[tag], list):
                    result[tag] = [result[tag]]
                result[tag].append(child_data)
            else:
                result[tag] = child_data
        
        return result


# Common UPnP error codes
UPNP_ERROR_CODES = {
    401: "Invalid Action",
    402: "Invalid Args",
    501: "Action Failed",
    600: "Argument Value Invalid",
    601: "Argument Value Out of Range",
    602: "Optional Action Not Implemented",
    603: "Out of Memory",
    604: "Human Intervention Required",
    605: "String Argument Too Long",
    701: "Transition not available",
    702: "No contents",
    703: "Read error",
    704: "Format not supported for recording",
    705: "Transport is locked",
    706: "Write error",
    707: "Media is protected or not writeable",
    708: "Format not supported",
    709: "Transport must be stopped",
    710: "Seek mode not supported",
    711: "Illegal seek target",
    712: "Play mode not supported",
    713: "Record quality not supported",
    714: "Illegal MIME-Type",
    715: "Content BUSY",
    716: "Resource Not found",
    717: "Play speed not supported",
    718: "Invalid InstanceID"
}


def get_error_description(error_code: int) -> str:
    """Get description for UPnP error code."""
    return UPNP_ERROR_CODES.get(error_code, f"Unknown error ({error_code})")


# Global SOAP client instance
_soap_client: Optional[SOAPClient] = None


def get_soap_client(stealth_mode: Optional[bool] = None) -> SOAPClient:
    """Get global SOAP client instance."""
    global _soap_client
    
    if stealth_mode is None:
        stealth_mode = config.is_stealth_mode()
    
    if _soap_client is None or _soap_client.stealth_mode != stealth_mode:
        _soap_client = SOAPClient(stealth_mode)
    
    return _soap_client


# Convenience functions
def send_soap_action(host: str, 
                    port: int,
                    control_url: str,
                    service_type: str,
                    action: str,
                    arguments: Optional[Dict[str, Any]] = None,
                    **kwargs) -> Dict[str, Any]:
    """
    Send SOAP action and return parsed response.
    
    Args:
        host: Target host
        port: Target port  
        control_url: Service control URL
        service_type: UPnP service type
        action: Action name
        arguments: Action arguments
        **kwargs: Additional arguments for send_soap_request
        
    Returns:
        Parsed response dictionary
    """
    client = get_soap_client()
    
    try:
        response = client.send_soap_request(
            host, port, control_url, service_type, action, arguments, **kwargs
        )
        
        return client.parse_soap_response(response)
    
    except SOAPError as e:
        logger.error(f"SOAP action {action} failed: {e}")
        return {
            'status_code': e.response_code or 0,
            'success': False,
            'error': str(e),
            'soap_fault': e.soap_fault,
            'data': {},
            'raw_response': ''
        }


async def send_soap_action_async(session: aiohttp.ClientSession,
                               host: str, 
                               port: int,
                               control_url: str,
                               service_type: str,
                               action: str,
                               arguments: Optional[Dict[str, Any]] = None,
                               **kwargs) -> Dict[str, Any]:
    """
    Send async SOAP action and return parsed response.
    
    Args:
        session: aiohttp session
        host: Target host
        port: Target port
        control_url: Service control URL
        service_type: UPnP service type
        action: Action name
        arguments: Action arguments
        **kwargs: Additional arguments for send_soap_request_async
        
    Returns:
        Parsed response dictionary
    """
    client = get_soap_client()
    
    try:
        response = await client.send_soap_request_async(
            session, host, port, control_url, service_type, action, arguments, **kwargs
        )
        
        response_text = await response.text()
        return client.parse_soap_response(response, response_text)
    
    except SOAPError as e:
        logger.error(f"Async SOAP action {action} failed: {e}")
        return {
            'status_code': e.response_code or 0,
            'success': False,
            'error': str(e),
            'soap_fault': e.soap_fault,
            'data': {},
            'raw_response': ''
        } 