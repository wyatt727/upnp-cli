"""
UPnP device discovery engine.

This module provides SSDP discovery, device description parsing,
and network scanning capabilities for finding UPnP devices.
"""

import asyncio
import socket
import struct
import time
from typing import List, Dict, Any, Optional, Set, Tuple
from urllib.parse import urlparse
import xml.etree.ElementTree as ET
import json

import aiohttp
import netifaces

from . import config
from .logging_utils import get_logger
from .utils import get_local_ip, validate_ip_address, threaded_map
from .cache import get_cache

logger = get_logger(__name__)

# SSDP multicast settings
SSDP_MULTICAST_ADDR = '239.255.255.250'
SSDP_PORT = 1900
SSDP_MX = 3  # Maximum wait time for responses

# SSDP search targets
SSDP_SEARCH_TARGETS = [
    'upnp:rootdevice',
    'urn:schemas-upnp-org:device:MediaRenderer:1',
    'urn:schemas-upnp-org:device:MediaServer:1',
    'urn:dial-multiscreen-org:service:dial:1',  # Chromecast
    'ssdp:all'
]


class SSDPProtocol(asyncio.DatagramProtocol):
    """Asyncio protocol for handling SSDP responses."""
    
    def __init__(self):
        self.responses: List[Dict[str, Any]] = []
        self.transport: Optional[asyncio.DatagramTransport] = None
    
    def connection_made(self, transport: asyncio.DatagramTransport) -> None:
        """Called when connection is established."""
        self.transport = transport
        logger.debug("SSDP protocol connection established")
    
    def datagram_received(self, data: bytes, addr: Tuple[str, int]) -> None:
        """Handle incoming SSDP response."""
        try:
            response_text = data.decode('utf-8', errors='ignore')
            headers = self._parse_ssdp_headers(response_text)
            
            if 'LOCATION' in headers:
                self.responses.append({
                    'location': headers['LOCATION'],
                    'st': headers.get('ST', ''),
                    'usn': headers.get('USN', ''),
                    'server': headers.get('SERVER', ''),
                    'addr': addr[0],
                    'raw_headers': headers
                })
                logger.debug(f"SSDP response from {addr[0]}: {headers.get('ST', '')}")
        
        except Exception as e:
            logger.warning(f"Failed to parse SSDP response from {addr}: {e}")
    
    def error_received(self, exc: Exception) -> None:
        """Handle protocol errors."""
        logger.warning(f"SSDP protocol error: {exc}")
    
    def connection_lost(self, exc: Optional[Exception]) -> None:
        """Called when connection is lost."""
        if exc:
            logger.warning(f"SSDP connection lost: {exc}")
        else:
            logger.debug("SSDP connection closed")
    
    def _parse_ssdp_headers(self, response: str) -> Dict[str, str]:
        """Parse SSDP response headers."""
        headers = {}
        lines = response.strip().split('\r\n')
        
        for line in lines[1:]:  # Skip the status line
            if ':' in line:
                key, value = line.split(':', 1)
                headers[key.strip().upper()] = value.strip()
        
        return headers


async def discover_ssdp_devices(timeout: int = config.DEFAULT_SSDP_TIMEOUT, 
                              search_targets: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """
    Discover UPnP devices using SSDP multicast.
    
    Args:
        timeout: Discovery timeout in seconds
        search_targets: List of SSDP search targets
        
    Returns:
        List of discovered device information
    """
    if search_targets is None:
        search_targets = SSDP_SEARCH_TARGETS
    
    logger.info(f"Starting SSDP discovery (timeout: {timeout}s)")
    
    # Create SSDP protocol
    loop = asyncio.get_event_loop()
    protocol = SSDPProtocol()
    
    try:
        # Create UDP socket for multicast
        transport, _ = await loop.create_datagram_endpoint(
            lambda: protocol,
            family=socket.AF_INET,
            proto=socket.IPPROTO_UDP,
            allow_broadcast=True
        )
        
        # Send M-SEARCH requests for each target
        for target in search_targets:
            message = _build_ssdp_request(target)
            transport.sendto(message.encode('utf-8'), (SSDP_MULTICAST_ADDR, SSDP_PORT))
            logger.debug(f"Sent SSDP M-SEARCH for {target}")
        
        # Wait for responses
        await asyncio.sleep(timeout)
        
        # Close transport
        transport.close()
        
        logger.info(f"SSDP discovery completed, found {len(protocol.responses)} responses")
        return protocol.responses
    
    except Exception as e:
        logger.error(f"SSDP discovery failed: {e}")
        return []


def _build_ssdp_request(search_target: str) -> str:
    """Build SSDP M-SEARCH request."""
    return '\r\n'.join([
        'M-SEARCH * HTTP/1.1',
        f'HOST: {SSDP_MULTICAST_ADDR}:{SSDP_PORT}',
        'MAN: "ssdp:discover"',
        f'ST: {search_target}',
        f'MX: {SSDP_MX}',
        'USER-AGENT: upnp-cli/1.0',
        '',
        ''
    ])


async def fetch_device_description(session: aiohttp.ClientSession, 
                                 location_url: str, 
                                 timeout: int = config.DEFAULT_HTTP_TIMEOUT) -> Optional[Dict[str, Any]]:
    """
    Fetch and parse UPnP device description XML.
    
    Args:
        session: aiohttp session
        location_url: Device description URL
        timeout: Request timeout
        
    Returns:
        Parsed device information or None if failed
    """
    try:
        async with session.get(location_url, timeout=timeout, ssl=False) as response:
            if response.status == 200:
                xml_content = await response.text()
                device_info = parse_device_description(xml_content)
                
                # Add location metadata
                parsed_url = urlparse(location_url)
                device_info['ip'] = parsed_url.hostname
                device_info['port'] = parsed_url.port or 80
                device_info['location_url'] = location_url
                
                logger.debug(f"Fetched device description for {device_info.get('friendlyName', 'Unknown')}")
                return device_info
            else:
                logger.warning(f"HTTP {response.status} fetching {location_url}")
    
    except Exception as e:
        logger.warning(f"Failed to fetch device description from {location_url}: {e}")
    
    return None


def parse_device_description(xml_content: str) -> Dict[str, Any]:
    """
    Parse UPnP device description XML with robust error handling.
    
    Args:
        xml_content: XML content string
        
    Returns:
        Dictionary with device information
    """
    try:
        # Sanitize and clean the XML content
        xml_content = _sanitize_xml_content(xml_content)
        
        # Remove namespace prefixes for easier parsing
        xml_content = _remove_xml_namespaces(xml_content)
        
        # Parse with multiple fallback strategies
        root = _parse_xml_with_fallbacks(xml_content)
        if root is None:
            logger.warning("Could not parse XML with any strategy")
            return {}
        
        # Find device element with multiple strategies
        device = _find_device_element(root)
        if device is None:
            logger.warning("No device element found in XML")
            return {}
        
        # Extract basic device information
        device_info = {}
        
        # Standard UPnP device fields
        for field in ['deviceType', 'friendlyName', 'manufacturer', 'manufacturerURL',
                     'modelDescription', 'modelName', 'modelNumber', 'modelURL',
                     'serialNumber', 'UDN', 'presentationURL']:
            element = device.find(field)
            if element is not None and element.text:
                device_info[field] = element.text.strip()
        
        # Parse services
        services = []
        service_list = device.find('serviceList')
        if service_list is not None:
            for service in service_list.findall('service'):
                service_info = {}
                for field in ['serviceType', 'serviceId', 'controlURL', 'eventSubURL', 'SCPDURL']:
                    element = service.find(field)
                    if element is not None and element.text:
                        service_info[field] = element.text.strip()
                
                if service_info:
                    services.append(service_info)
        
        device_info['services'] = services
        
        # Parse embedded devices (like Sonos MediaRenderer/MediaServer)
        embedded_devices = []
        device_list = device.find('deviceList')
        if device_list is not None:
            for embedded_device in device_list.findall('device'):
                embedded_info = {}
                
                # Extract basic embedded device info
                for field in ['deviceType', 'friendlyName', 'manufacturer', 'manufacturerURL',
                             'modelDescription', 'modelName', 'modelNumber', 'modelURL',
                             'serialNumber', 'UDN', 'presentationURL']:
                    element = embedded_device.find(field)
                    if element is not None and element.text:
                        embedded_info[field] = element.text.strip()
                
                # Parse embedded device services
                embedded_services = []
                embedded_service_list = embedded_device.find('serviceList')
                if embedded_service_list is not None:
                    for embedded_service in embedded_service_list.findall('service'):
                        embedded_service_info = {}
                        for field in ['serviceType', 'serviceId', 'controlURL', 'eventSubURL', 'SCPDURL']:
                            element = embedded_service.find(field)
                            if element is not None and element.text:
                                embedded_service_info[field] = element.text.strip()
                        
                        if embedded_service_info:
                            embedded_services.append(embedded_service_info)
                
                embedded_info['services'] = embedded_services
                
                if embedded_info:
                    embedded_devices.append(embedded_info)
        
        device_info['devices'] = embedded_devices
        
        # Parse device icons if present
        icons = []
        icon_list = device.find('iconList')
        if icon_list is not None:
            for icon in icon_list.findall('icon'):
                icon_info = {}
                for field in ['mimetype', 'width', 'height', 'depth', 'url']:
                    element = icon.find(field)
                    if element is not None and element.text:
                        icon_info[field] = element.text.strip()
                
                if icon_info:
                    icons.append(icon_info)
        
        device_info['icons'] = icons
        
        return device_info
    
    except Exception as e:
        logger.error(f"Failed to parse device description XML: {e}")
        logger.debug(f"Problematic XML content sample: {xml_content[:200]}...")
        return {}


def _sanitize_xml_content(xml_content: str) -> str:
    """Sanitize XML content to handle common UPnP device issues."""
    import re
    
    # Remove BOM if present
    if xml_content.startswith('\ufeff'):
        xml_content = xml_content[1:]
    
    # Remove null bytes and other control characters (except allowed ones)
    xml_content = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', xml_content)
    
    # Fix common encoding issues
    xml_content = xml_content.replace('\x00', '')
    
    # Ensure proper XML declaration
    if not xml_content.strip().startswith('<?xml'):
        # If no XML declaration, add a simple one
        xml_content = '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_content.strip()
    
    # Fix malformed XML declarations
    xml_content = re.sub(r'<\?xml[^>]*version\s*=\s*["\']?[^"\'>\s]*["\']?[^>]*\?>', 
                        '<?xml version="1.0" encoding="UTF-8"?>', xml_content)
    
    # Remove any content before the first XML element
    match = re.search(r'<[^!?]', xml_content)
    if match:
        start_pos = match.start()
        # Keep the XML declaration if it exists
        xml_decl_match = re.search(r'<\?xml[^>]*\?>', xml_content[:start_pos])
        if xml_decl_match:
            xml_content = xml_content[xml_decl_match.start():start_pos] + xml_content[start_pos:]
        else:
            xml_content = xml_content[start_pos:]
    
    return xml_content


def _remove_xml_namespaces(xml_content: str) -> str:
    """Remove XML namespaces for easier parsing."""
    import re
    
    # Remove namespace declarations
    xml_content = re.sub(r'xmlns[^=]*="[^"]*"', '', xml_content)
    
    # Remove namespace prefixes from tags
    xml_content = re.sub(r'<(/?)(\w+:)', r'<\1', xml_content)
    
    # Clean up any extra spaces in tags
    xml_content = re.sub(r'<([^>]+)\s+>', r'<\1>', xml_content)
    
    return xml_content


def _parse_xml_with_fallbacks(xml_content: str) -> Optional[ET.Element]:
    """Parse XML with multiple fallback strategies."""
    
    # Strategy 1: Direct parsing
    try:
        return ET.fromstring(xml_content)
    except ET.ParseError as e:
        logger.debug(f"Direct XML parsing failed: {e}")
    
    # Strategy 2: Try fixing common issues
    try:
        # Fix unescaped & characters
        import re
        fixed_content = re.sub(r'&(?![a-zA-Z0-9#]+;)', '&amp;', xml_content)
        
        # Fix unclosed tags by removing problematic content
        fixed_content = re.sub(r'<([^/>]+)(?<![/"])>', r'<\1/>', fixed_content)
        
        return ET.fromstring(fixed_content)
    except ET.ParseError as e:
        logger.debug(f"Fixed XML parsing failed: {e}")
    
    # Strategy 3: Try with XMLParser that's more lenient
    try:
        from xml.etree import ElementTree
        parser = ElementTree.XMLParser(encoding='utf-8')
        parser.feed(xml_content)
        return parser.close()
    except Exception as e:
        logger.debug(f"Lenient XML parsing failed: {e}")
    
    # Strategy 4: Try removing problematic content and parsing incrementally
    try:
        import re
        
        # Find the root element and try to parse just that
        root_match = re.search(r'<(\w+)[^>]*>', xml_content)
        if root_match:
            root_tag = root_match.group(1)
            
            # Try to find the matching closing tag
            closing_pattern = f'</{root_tag}>'
            closing_match = re.search(closing_pattern, xml_content)
            
            if closing_match:
                # Extract just the root element content
                start = root_match.start()
                end = closing_match.end()
                root_content = xml_content[start:end]
                
                return ET.fromstring(root_content)
    except Exception as e:
        logger.debug(f"Incremental XML parsing failed: {e}")
    
    # Strategy 5: Last resort - try parsing with BeautifulSoup if available
    try:
        from bs4 import BeautifulSoup, FeatureNotFound
        try:
            # Try with lxml parser
            soup = BeautifulSoup(xml_content, 'xml')
        except FeatureNotFound:
            # Fallback to html.parser
            soup = BeautifulSoup(xml_content, 'html.parser')
        
        # Convert back to ElementTree
        xml_str = str(soup)
        return ET.fromstring(xml_str)
    except ImportError:
        logger.debug("BeautifulSoup not available for XML fallback")
    except Exception as e:
        logger.debug(f"BeautifulSoup XML parsing failed: {e}")
    
    return None


def _find_device_element(root: ET.Element) -> Optional[ET.Element]:
    """Find device element using multiple strategies."""
    
    # Strategy 1: Standard UPnP device element
    device = root.find('.//device')
    if device is not None:
        return device
    
    # Strategy 2: Try different case variations
    for tag in ['Device', 'DEVICE']:
        device = root.find(f'.//{tag}')
        if device is not None:
            return device
    
    # Strategy 3: Check if root is the device element
    if root.tag in ['device', 'Device', 'DEVICE']:
        return root
    
    # Strategy 4: Look for any element with device-like properties
    for elem in root.iter():
        # Check if this element has device-like children
        children = [child.tag.lower() for child in elem]
        device_indicators = ['friendlyname', 'manufacturer', 'modelname', 'devicetype']
        
        if any(indicator in children for indicator in device_indicators):
            return elem
    
    return None


async def scan_network_async(network_range: Optional[str] = None, 
                           ports: Optional[List[int]] = None,
                           use_cache: bool = True) -> List[Dict[str, Any]]:
    """
    Comprehensive network scan combining SSDP discovery and port scanning.
    
    Args:
        network_range: Network to scan (e.g., "192.168.1.0/24")
        ports: Ports to scan (defaults to common UPnP ports)
        use_cache: Whether to use/update device cache
        
    Returns:
        List of discovered devices with combined information
    """
    devices = []
    seen_devices = set()  # Track unique device identifiers to prevent duplicates
    
    if ports is None:
        ports = config.UPNP_SCAN_PORTS
    
    logger.info(f"Starting comprehensive network scan")
    
    # Step 1: SSDP Discovery
    logger.info("Phase 1: SSDP discovery")
    ssdp_devices = await discover_ssdp_devices()
    
    # Deduplicate SSDP responses by location URL
    unique_ssdp_devices = []
    seen_locations = set()
    for ssdp_device in ssdp_devices:
        location = ssdp_device.get('location', '')
        if location and location not in seen_locations:
            seen_locations.add(location)
            unique_ssdp_devices.append(ssdp_device)
    
    logger.info(f"Deduplicated SSDP responses: {len(ssdp_devices)} -> {len(unique_ssdp_devices)}")
    
    # Step 2: Fetch device descriptions
    logger.info(f"Phase 2: Fetching {len(unique_ssdp_devices)} device descriptions")
    async with aiohttp.ClientSession() as session:
        tasks = []
        for ssdp_device in unique_ssdp_devices:
            if 'location' in ssdp_device:
                task = fetch_device_description(session, ssdp_device['location'])
                tasks.append(task)
        
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for i, result in enumerate(results):
                if isinstance(result, dict) and result:
                    # Create unique device identifier
                    device_id = _create_device_identifier(result)
                    
                    if device_id not in seen_devices:
                        seen_devices.add(device_id)
                        
                        # Merge SSDP and device description data
                        device_info = result.copy()
                        device_info.update({
                            'discovery_method': 'ssdp',
                            'ssdp_st': unique_ssdp_devices[i].get('st', ''),
                            'ssdp_usn': unique_ssdp_devices[i].get('usn', ''),
                            'ssdp_server': unique_ssdp_devices[i].get('server', '')
                        })
                        devices.append(device_info)
                        logger.debug(f"Added SSDP device: {device_info.get('friendlyName', 'Unknown')} ({device_id})")
                    else:
                        logger.debug(f"Skipping duplicate SSDP device: {device_id}")
    
    # Step 3: ARP-based discovery (if network_range not specified)
    if network_range is None:
        logger.info("Phase 3: ARP table discovery")
        arp_hosts = discover_arp_hosts()
        logger.info(f"Found {len(arp_hosts)} hosts in ARP table")
    else:
        arp_hosts = []
        logger.info(f"Phase 3: Skipping ARP discovery (network range specified)")
    
    # Step 4: Port scanning on discovered IPs
    discovered_ips = {device['ip'] for device in devices if 'ip' in device}
    arp_ips = {host['ip'] for host in arp_hosts}
    all_ips = discovered_ips.union(arp_ips)
    
    if network_range:
        # Add IPs from specified network range
        network_ips = generate_network_ips(network_range)
        all_ips.update(network_ips)
    
    logger.info(f"Phase 4: Port scanning {len(all_ips)} IPs on {len(ports)} ports")
    
    # Scan ports in parallel
    scan_results = await scan_ports_async(list(all_ips), ports)
    
    # Step 5: Fetch device descriptions from responsive ports
    logger.info(f"Phase 5: Checking {len(scan_results)} responsive endpoints")
    
    # Group scan results by IP:port to avoid multiple attempts on same endpoint
    unique_endpoints = set(scan_results)
    
    async with aiohttp.ClientSession() as session:
        tasks = []
        processed_endpoints = set()
        
        for ip, port in unique_endpoints:
            # Skip if we already have this device from SSDP
            endpoint_id = f"{ip}:{port}"
            if any(d.get('ip') == ip and d.get('port') == port for d in devices):
                logger.debug(f"Skipping endpoint {endpoint_id} - already discovered via SSDP")
                continue
            
            if endpoint_id in processed_endpoints:
                continue
            processed_endpoints.add(endpoint_id)
            
            # Try common UPnP description paths (but only create one task per endpoint)
            for path in ['/xml/device_description.xml', '/description.xml', 
                        '/dmr/description.xml', '/upnp/description.xml']:
                url = f"http://{ip}:{port}{path}"
                task = fetch_device_description(session, url)
                tasks.append((task, ip, port, path))
                break  # Only try first path for now, avoid multiple requests per endpoint
        
        if tasks:
            task_futures = [task for task, _, _, _ in tasks]
            results = await asyncio.gather(*task_futures, return_exceptions=True)
            
            for i, result in enumerate(results):
                if isinstance(result, dict) and result:
                    _, ip, port, path = tasks[i]
                    
                    # Create unique device identifier
                    device_id = _create_device_identifier(result)
                    
                    if device_id not in seen_devices:
                        seen_devices.add(device_id)
                        result['discovery_method'] = 'port_scan'
                        devices.append(result)
                        logger.debug(f"Added port scan device: {result.get('friendlyName', 'Unknown')} ({device_id})")
                    else:
                        logger.debug(f"Skipping duplicate port scan device: {device_id}")
    
    # Step 6: Final deduplication and filtering
    final_devices = _deduplicate_devices(devices)
    logger.info(f"Final deduplication: {len(devices)} -> {len(final_devices)} devices")
    
    # Step 7: Update cache
    if use_cache:
        cache = get_cache()
        for device in final_devices:
            if 'ip' in device and 'port' in device:
                cache.upsert(device['ip'], device['port'], device)
        
        logger.info(f"Updated cache with {len(final_devices)} devices")
    
    logger.info(f"Network scan completed, found {len(final_devices)} total devices")
    return final_devices


def _create_device_identifier(device_info: Dict[str, Any]) -> str:
    """
    Create a unique identifier for a device to prevent duplicates.
    
    Args:
        device_info: Device information dictionary
        
    Returns:
        Unique identifier string
    """
    # Primary identifier: UDN (Unique Device Name)
    udn = device_info.get('UDN', '').strip()
    if udn:
        return f"udn:{udn}"
    
    # Secondary identifier: IP:Port combination
    ip = device_info.get('ip', '')
    port = device_info.get('port', '')
    if ip and port:
        return f"endpoint:{ip}:{port}"
    
    # Fallback identifier: friendlyName + manufacturer + model
    name = device_info.get('friendlyName', '').strip()
    manufacturer = device_info.get('manufacturer', '').strip()
    model = device_info.get('modelName', '').strip()
    
    if name or manufacturer or model:
        return f"device:{name}:{manufacturer}:{model}".lower().replace(' ', '_')
    
    # Last resort: Use location URL if available
    location = device_info.get('location_url', '')
    if location:
        return f"location:{location}"
    
    # Very last resort: Use a combination of available fields
    import hashlib
    content = json.dumps(device_info, sort_keys=True)
    return f"hash:{hashlib.md5(content.encode()).hexdigest()[:8]}"


def _deduplicate_devices(devices: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Final deduplication pass to remove any remaining duplicates.
    
    Args:
        devices: List of device information dictionaries
        
    Returns:
        Deduplicated list of devices
    """
    seen_devices = {}
    deduplicated = []
    
    for device in devices:
        device_id = _create_device_identifier(device)
        
        if device_id not in seen_devices:
            seen_devices[device_id] = device
            deduplicated.append(device)
        else:
            # Merge information from duplicate device if it has additional data
            existing = seen_devices[device_id]
            
            # Prefer SSDP discovery method over port scan
            if (existing.get('discovery_method') == 'port_scan' and 
                device.get('discovery_method') == 'ssdp'):
                # Replace with SSDP version
                seen_devices[device_id] = device
                # Update the device in the deduplicated list
                for i, d in enumerate(deduplicated):
                    if _create_device_identifier(d) == device_id:
                        deduplicated[i] = device
                        break
            
            # Merge SSDP information if missing
            for key in ['ssdp_st', 'ssdp_usn', 'ssdp_server']:
                if key not in existing and key in device:
                    existing[key] = device[key]
    
    return deduplicated


def discover_arp_hosts() -> List[Dict[str, str]]:
    """
    Discover hosts from ARP table.
    
    Returns:
        List of host information from ARP table
    """
    hosts = []
    
    try:
        import subprocess
        
        # Try to get ARP table
        result = subprocess.run(['arp', '-a'], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                # Parse ARP entry: hostname (ip) at mac on interface
                import re
                match = re.search(r'\((\d+\.\d+\.\d+\.\d+)\)', line)
                if match:
                    ip = match.group(1)
                    if validate_ip_address(ip):
                        hosts.append({'ip': ip, 'source': 'arp'})
        
        logger.debug(f"Found {len(hosts)} hosts in ARP table")
    
    except Exception as e:
        logger.warning(f"Failed to discover ARP hosts: {e}")
    
    return hosts


async def scan_ports_async(ips: List[str], ports: List[int]) -> List[Tuple[str, int]]:
    """
    Asynchronously scan ports on multiple IPs.
    
    Args:
        ips: List of IP addresses to scan
        ports: List of ports to scan
        
    Returns:
        List of (ip, port) tuples for responsive endpoints
    """
    responsive_endpoints = []
    
    async def check_port(ip: str, port: int) -> Optional[Tuple[str, int]]:
        """Check if a single port is open."""
        try:
            # Create connection with timeout
            future = asyncio.open_connection(ip, port)
            reader, writer = await asyncio.wait_for(future, timeout=1.0)
            
            # Close connection immediately
            writer.close()
            await writer.wait_closed()
            
            return (ip, port)
        
        except Exception:
            # Port is closed or timeout
            return None
    
    # Create tasks for all IP/port combinations
    tasks = []
    for ip in ips:
        for port in ports:
            task = check_port(ip, port)
            tasks.append(task)
    
    # Run all checks in parallel
    if tasks:
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, tuple):
                responsive_endpoints.append(result)
    
    logger.debug(f"Found {len(responsive_endpoints)} responsive endpoints")
    return responsive_endpoints


def generate_network_ips(network_range: str) -> Set[str]:
    """
    Generate IP addresses from network range.
    
    Args:
        network_range: Network in CIDR notation (e.g., "192.168.1.0/24")
        
    Returns:
        Set of IP addresses in the network
    """
    try:
        import ipaddress
        
        network = ipaddress.IPv4Network(network_range, strict=False)
        return {str(ip) for ip in network.hosts()}
    
    except Exception as e:
        logger.error(f"Invalid network range {network_range}: {e}")
        return set()


def filter_media_devices(devices: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Filter devices to only include media-capable devices.
    
    Args:
        devices: List of discovered devices
        
    Returns:
        Filtered list of media devices
    """
    media_devices = []
    
    media_keywords = [
        'mediarenderer', 'mediaserver', 'sonos', 'roku', 'chromecast',
        'samsung', 'lg', 'sony', 'philips', 'panasonic', 'soundbar',
        'speaker', 'tv', 'audio', 'video', 'dlna'
    ]
    
    for device in devices:
        is_media_device = False
        
        # Check device type
        device_type = device.get('deviceType', '').lower()
        if 'mediarenderer' in device_type or 'mediaserver' in device_type:
            is_media_device = True
        
        # Check manufacturer
        manufacturer = device.get('manufacturer', '').lower()
        if any(keyword in manufacturer for keyword in media_keywords):
            is_media_device = True
        
        # Check model name
        model_name = device.get('modelName', '').lower()
        if any(keyword in model_name for keyword in media_keywords):
            is_media_device = True
        
        # Check friendly name
        friendly_name = device.get('friendlyName', '').lower()
        if any(keyword in friendly_name for keyword in media_keywords):
            is_media_device = True
        
        # Check services
        services = device.get('services', [])
        for service in services:
            service_type = service.get('serviceType', '').lower()
            if any(svc in service_type for svc in ['avtransport', 'renderingcontrol', 'connectionmanager']):
                is_media_device = True
                break
        
        if is_media_device:
            media_devices.append(device)
    
    logger.info(f"Filtered to {len(media_devices)} media devices from {len(devices)} total")
    return media_devices


# Synchronous wrapper functions for backward compatibility
def discover_upnp_devices(timeout: int = config.DEFAULT_SSDP_TIMEOUT) -> List[Dict[str, Any]]:
    """Synchronous wrapper for SSDP discovery."""
    return asyncio.run(discover_ssdp_devices(timeout))


def scan_network(network_range: Optional[str] = None, 
                ports: Optional[List[int]] = None,
                use_cache: bool = True) -> List[Dict[str, Any]]:
    """Synchronous wrapper for network scanning."""
    return asyncio.run(scan_network_async(network_range, ports, use_cache)) 