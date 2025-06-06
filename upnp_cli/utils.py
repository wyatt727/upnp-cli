"""
Utility functions for UPnP CLI.

This module provides helper functions for network operations, XML parsing,
and other common tasks.
"""

import socket
import subprocess
import ipaddress
import xml.etree.ElementTree as ET
from typing import Tuple, Optional, List, Dict, Any, Callable, TypeVar
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import random

from .logging_utils import get_logger

logger = get_logger(__name__)

T = TypeVar('T')


def get_local_ip() -> str:
    """
    Get the local IP address of this machine.
    
    Returns:
        Local IP address as string, defaults to '127.0.0.1' if detection fails
    """
    try:
        # Try netifaces first (if available)
        try:
            import netifaces
            if 'en0' in netifaces.interfaces():
                addrs = netifaces.ifaddresses('en0')
                if netifaces.AF_INET in addrs:
                    return addrs[netifaces.AF_INET][0]['addr']
        except ImportError:
            pass
        
        # Fallback: UDP connect trick
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
            
    except Exception as e:
        logger.warning(f"Could not determine local IP: {e}")
        
    try:
        # Last resort: hostname resolution
        return socket.gethostbyname(socket.gethostname())
    except Exception:
        return '127.0.0.1'


def get_en0_network() -> Tuple[str, str]:
    """
    Get the IP address and network CIDR for the en0 interface (macOS/Linux).
    
    Returns:
        Tuple of (ip_address, network_cidr)
    """
    try:
        import netifaces
        if 'en0' in netifaces.interfaces():
            addrs = netifaces.ifaddresses('en0')
            if netifaces.AF_INET in addrs:
                info = addrs[netifaces.AF_INET][0]
                ip = info['addr']
                netmask = info['netmask']
                network = ipaddress.IPv4Network(f"{ip}/{netmask}", strict=False)
                return ip, str(network)
    except ImportError:
        logger.debug("netifaces not available, using fallback method")
    except Exception as e:
        logger.debug(f"Could not get en0 network info: {e}")
    
    # Fallback to route command on Unix-like systems
    try:
        result = subprocess.run(['route', 'get', 'default'], 
                              capture_output=True, text=True, timeout=5)
        # Parse route output for gateway and interface info
        # This is a simplified approach; real implementation would be more robust
        pass
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
        pass
    
    # Final fallback: use local IP with /24 network
    local_ip = get_local_ip()
    try:
        network = ipaddress.IPv4Network(f"{local_ip}/24", strict=False)
        return local_ip, str(network)
    except Exception:
        return local_ip, "192.168.1.0/24"


def parse_device_description_xml(xml_text: str) -> Dict[str, Any]:
    """
    Parse UPnP device description XML and extract key information.
    
    Args:
        xml_text: XML content as string
        
    Returns:
        Dictionary containing device information and services
        
    Raises:
        ValueError: If XML is invalid or missing required elements
    """
    try:
        root = ET.fromstring(xml_text)
        
        # Strip namespaces to simplify parsing
        for elem in root.iter():
            if '}' in elem.tag:
                elem.tag = elem.tag.split('}', 1)[1]
        
        # Find the device element
        device = root.find('.//device')
        if device is None:
            raise ValueError("No device element found in XML")
        
        # Extract basic device information
        info = {}
        basic_fields = [
            'deviceType', 'friendlyName', 'manufacturer', 'manufacturerURL',
            'modelDescription', 'modelName', 'modelNumber', 'modelURL',
            'serialNumber', 'UDN', 'softwareVersion'
        ]
        
        for field in basic_fields:
            elem = device.find(field)
            if elem is not None and elem.text:
                info[field] = elem.text.strip()
        
        # Extract services
        services = []
        service_list = device.find('serviceList')
        if service_list is not None:
            for service in service_list.findall('service'):
                service_info = {}
                service_fields = [
                    'serviceType', 'serviceId', 'controlURL', 
                    'eventSubURL', 'SCPDURL'
                ]
                
                for field in service_fields:
                    elem = service.find(field)
                    if elem is not None and elem.text:
                        service_info[field] = elem.text.strip()
                
                if service_info:
                    services.append(service_info)
        
        info['services'] = services
        
        # Extract device icons if present
        icons = []
        icon_list = device.find('iconList')
        if icon_list is not None:
            for icon in icon_list.findall('icon'):
                icon_info = {}
                icon_fields = ['mimetype', 'width', 'height', 'depth', 'url']
                
                for field in icon_fields:
                    elem = icon.find(field)
                    if elem is not None and elem.text:
                        icon_info[field] = elem.text.strip()
                
                if icon_info:
                    icons.append(icon_info)
        
        info['icons'] = icons
        
        return info
        
    except ET.ParseError as e:
        raise ValueError(f"Invalid XML: {e}")
    except Exception as e:
        raise ValueError(f"Error parsing device description: {e}")


def threaded_map(func: Callable[[T], Any], iterable: List[T], 
                max_workers: Optional[int] = None) -> List[Any]:
    """
    Execute function across iterable using thread pool for parallel execution.
    
    Args:
        func: Function to execute
        iterable: Items to process
        max_workers: Maximum number of worker threads
        
    Returns:
        List of results in same order as input
    """
    if max_workers is None:
        max_workers = min(32, len(iterable))
    
    results = [None] * len(iterable)
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks with their original indices
        future_to_index = {
            executor.submit(func, item): i 
            for i, item in enumerate(iterable)
        }
        
        # Collect results in original order
        for future in as_completed(future_to_index):
            index = future_to_index[future]
            try:
                results[index] = future.result()
            except Exception as e:
                logger.debug(f"Task {index} failed: {e}")
                results[index] = None
    
    return results


def is_port_open(host: str, port: int, timeout: float = 1.0) -> bool:
    """
    Check if a TCP port is open on the given host.
    
    Args:
        host: Target hostname or IP address
        port: Port number to check
        timeout: Connection timeout in seconds
        
    Returns:
        True if port is open, False otherwise
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            return result == 0
    except Exception:
        return False


def scan_ports(host: str, ports: List[int], timeout: float = 1.0, 
               max_workers: int = 10) -> List[int]:
    """
    Scan multiple ports on a host in parallel.
    
    Args:
        host: Target hostname or IP address
        ports: List of ports to scan
        timeout: Connection timeout per port
        max_workers: Maximum concurrent connections
        
    Returns:
        List of open ports
    """
    def check_port(port: int) -> Optional[int]:
        if is_port_open(host, port, timeout):
            return port
        return None
    
    results = threaded_map(check_port, ports, max_workers)
    return [port for port in results if port is not None]


def get_arp_table() -> Dict[str, str]:
    """
    Get the ARP table from the system.
    
    Returns:
        Dictionary mapping IP addresses to MAC addresses
    """
    arp_table = {}
    
    try:
        # Try different ARP commands based on platform
        commands = [
            ['arp', '-a'],           # macOS/Linux
            ['arp', '-A'],           # Some Linux distributions
            ['ip', 'neigh', 'show'], # Modern Linux with iproute2
        ]
        
        for cmd in commands:
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    # Parse ARP output
                    for line in result.stdout.splitlines():
                        parts = line.split()
                        if len(parts) >= 3:
                            # Different formats: "IP (IP) at MAC" or "IP dev eth0 lladdr MAC"
                            ip = None
                            mac = None
                            
                            for part in parts:
                                # Look for IP address
                                if not ip:
                                    try:
                                        ipaddress.ip_address(part.strip('()'))
                                        ip = part.strip('()')
                                    except ValueError:
                                        pass
                                
                                # Look for MAC address (colon-separated hex)
                                if ':' in part and len(part) == 17:
                                    mac = part.lower()
                            
                            if ip and mac:
                                arp_table[ip] = mac
                    break
                    
            except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
                continue
                
    except Exception as e:
        logger.debug(f"Could not get ARP table: {e}")
    
    return arp_table


def random_delay(min_seconds: float = 0.1, max_seconds: float = 0.5) -> None:
    """
    Sleep for a random amount of time (useful for stealth mode).
    
    Args:
        min_seconds: Minimum delay
        max_seconds: Maximum delay
    """
    delay = random.uniform(min_seconds, max_seconds)
    time.sleep(delay)


def is_private_ip(ip: str) -> bool:
    """
    Check if an IP address is in a private network range.
    
    Args:
        ip: IP address as string
        
    Returns:
        True if IP is private, False otherwise
    """
    try:
        ip_obj = ipaddress.ip_address(ip)
        return ip_obj.is_private
    except ValueError:
        return False


def expand_network_range(network: str) -> List[str]:
    """
    Expand a network CIDR range into individual IP addresses.
    
    Args:
        network: Network in CIDR notation (e.g., "192.168.1.0/24")
        
    Returns:
        List of IP addresses in the network
    """
    try:
        net = ipaddress.IPv4Network(network, strict=False)
        # Skip network and broadcast addresses for /24 and larger networks
        if net.prefixlen >= 24:
            return [str(ip) for ip in net.hosts()]
        else:
            # For smaller networks, return all addresses
            return [str(ip) for ip in net]
    except Exception as e:
        logger.error(f"Could not expand network range {network}: {e}")
        return []


def validate_ip_address(ip: str) -> bool:
    """
    Validate that a string is a valid IP address.
    
    Args:
        ip: IP address string to validate
        
    Returns:
        True if valid IP address, False otherwise
    """
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False


def validate_port(port: int) -> bool:
    """
    Validate that a port number is in the valid range.
    
    Args:
        port: Port number to validate
        
    Returns:
        True if valid port, False otherwise
    """
    return 1 <= port <= 65535 