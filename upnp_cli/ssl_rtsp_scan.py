"""
SSL/TLS and RTSP Scanner for UPnP CLI.

This module provides SSL certificate analysis, weak cipher detection,
and RTSP stream discovery for security assessment of media devices.
"""

import asyncio
import socket
import ssl
import time
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple, Set
from urllib.parse import urlparse
import re

import aiohttp
import requests

from . import config
from .logging_utils import get_logger
from .utils import validate_ip_address, validate_port, threaded_map

logger = get_logger(__name__)


class SecurityScanError(Exception):
    """Exception raised for security scanning operations."""
    
    def __init__(self, message: str, error_code: Optional[int] = None, target: Optional[str] = None):
        self.message = message
        self.error_code = error_code
        self.target = target
        super().__init__(self.message)


class SSLRTSPScanner:
    """
    SSL/TLS and RTSP security scanner.
    
    Provides SSL certificate analysis, cipher suite enumeration,
    RTSP stream discovery, and vulnerability assessment.
    """
    
    def __init__(self):
        """Initialize SSL/RTSP scanner."""
        logger.debug("SSLRTSPScanner initialized")
    
    # === SSL/TLS ANALYSIS ===
    
    async def scan_ssl_certificate(self, 
                                   host: str, 
                                   port: int = 443,
                                   timeout: int = 10) -> Dict[str, Any]:
        """
        Analyze SSL certificate on target host:port.
        
        Args:
            host: Target host
            port: Target port (default 443)
            timeout: Connection timeout
            
        Returns:
            SSL certificate analysis results
        """
        try:
            logger.debug(f"Scanning SSL certificate on {host}:{port}")
            
            # Create SSL context
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            
            # Connect and get certificate
            with socket.create_connection((host, port), timeout) as sock:
                with context.wrap_socket(sock, server_hostname=host) as ssock:
                    cert = ssock.getpeercert()
                    cert_der = ssock.getpeercert(binary_form=True)
                    cipher = ssock.cipher()
                    version = ssock.version()
            
            # Analyze certificate
            analysis = self._analyze_certificate(cert, cert_der)
            analysis.update({
                'cipher': cipher,
                'ssl_version': version,
                'host': host,
                'port': port,
                'scan_time': datetime.now(timezone.utc).isoformat()
            })
            
            return analysis
            
        except Exception as e:
            logger.error(f"SSL scan failed for {host}:{port}: {e}")
            return {
                'error': str(e),
                'host': host,
                'port': port,
                'scan_time': datetime.now(timezone.utc).isoformat()
            }
    
    def _analyze_certificate(self, cert: Dict, cert_der: bytes) -> Dict[str, Any]:
        """Analyze SSL certificate details."""
        analysis = {
            'subject': dict(x[0] for x in cert.get('subject', [])),
            'issuer': dict(x[0] for x in cert.get('issuer', [])),
            'version': cert.get('version'),
            'serial_number': cert.get('serialNumber'),
            'not_before': cert.get('notBefore'),
            'not_after': cert.get('notAfter'),
            'san': cert.get('subjectAltName', []),
            'signature_algorithm': cert.get('signatureAlgorithm'),
            'public_key_size': None,
            'is_expired': False,
            'is_self_signed': False,
            'vulnerabilities': []
        }
        
        # Check expiration
        if cert.get('notAfter'):
            try:
                expiry = datetime.strptime(cert['notAfter'], '%b %d %H:%M:%S %Y %Z')
                analysis['is_expired'] = expiry < datetime.now()
                analysis['days_until_expiry'] = (expiry - datetime.now()).days
            except ValueError:
                logger.warning("Could not parse certificate expiry date")
        
        # Check if self-signed
        subject = analysis.get('subject', {})
        issuer = analysis.get('issuer', {})
        if subject == issuer:
            analysis['is_self_signed'] = True
            analysis['vulnerabilities'].append('Self-signed certificate')
        
        # Check weak signature algorithms
        sig_alg = analysis.get('signature_algorithm', '').lower()
        if any(weak in sig_alg for weak in ['md5', 'sha1']):
            analysis['vulnerabilities'].append(f'Weak signature algorithm: {sig_alg}')
        
        # Extract public key size
        try:
            x509 = ssl.DER_cert_to_PEM_cert(cert_der)
            # Basic extraction - would need cryptography library for full analysis
            if 'RSA' in str(cert.get('subjectPublicKeyInfo', '')):
                # Estimate based on certificate size (rough approximation)
                if len(cert_der) < 1000:
                    analysis['public_key_size'] = 1024
                    analysis['vulnerabilities'].append('Weak RSA key size (< 2048 bits)')
                elif len(cert_der) < 1500:
                    analysis['public_key_size'] = 2048
                else:
                    analysis['public_key_size'] = 4096
        except Exception:
            logger.debug("Could not determine public key size")
        
        return analysis
    
    async def scan_ssl_ciphers(self, 
                               host: str, 
                               port: int = 443,
                               timeout: int = 10) -> Dict[str, Any]:
        """
        Enumerate supported SSL ciphers and protocols.
        
        Args:
            host: Target host
            port: Target port
            timeout: Connection timeout
            
        Returns:
            Cipher enumeration results
        """
        try:
            logger.debug(f"Scanning SSL ciphers on {host}:{port}")
            
            results = {
                'host': host,
                'port': port,
                'supported_protocols': [],
                'supported_ciphers': [],
                'weak_ciphers': [],
                'vulnerabilities': [],
                'scan_time': datetime.now(timezone.utc).isoformat()
            }
            
            # Test different SSL/TLS versions
            protocols_to_test = [
                ('SSLv2', ssl.PROTOCOL_SSLv23),  # Will fail on modern systems
                ('SSLv3', ssl.PROTOCOL_SSLv23),
                ('TLSv1.0', ssl.PROTOCOL_TLSv1),
                ('TLSv1.1', ssl.PROTOCOL_TLSv1_1),
                ('TLSv1.2', ssl.PROTOCOL_TLSv1_2),
            ]
            
            # Add TLSv1.3 if available
            if hasattr(ssl, 'PROTOCOL_TLSv1_3'):
                protocols_to_test.append(('TLSv1.3', ssl.PROTOCOL_TLSv1_3))
            
            for protocol_name, protocol_version in protocols_to_test:
                try:
                    context = ssl.SSLContext(protocol_version)
                    context.check_hostname = False
                    context.verify_mode = ssl.CERT_NONE
                    
                    with socket.create_connection((host, port), timeout) as sock:
                        with context.wrap_socket(sock) as ssock:
                            results['supported_protocols'].append({
                                'protocol': protocol_name,
                                'version': ssock.version(),
                                'cipher': ssock.cipher()
                            })
                            
                            # Check for weak protocols
                            if protocol_name in ['SSLv2', 'SSLv3', 'TLSv1.0']:
                                results['vulnerabilities'].append(f'Weak protocol supported: {protocol_name}')
                            
                except Exception:
                    logger.debug(f"Protocol {protocol_name} not supported or failed")
            
            # Test cipher suites with default context
            try:
                context = ssl.create_default_context()
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
                
                with socket.create_connection((host, port), timeout) as sock:
                    with context.wrap_socket(sock) as ssock:
                        cipher_info = ssock.cipher()
                        if cipher_info:
                            results['supported_ciphers'].append(cipher_info)
                            
                            # Check for weak ciphers
                            cipher_name = cipher_info[0] if cipher_info else ''
                            if any(weak in cipher_name.upper() for weak in ['RC4', 'DES', 'MD5', 'NULL']):
                                results['weak_ciphers'].append(cipher_info)
                                results['vulnerabilities'].append(f'Weak cipher: {cipher_name}')
                            
            except Exception as e:
                logger.debug(f"Default cipher test failed: {e}")
            
            return results
            
        except Exception as e:
            logger.error(f"SSL cipher scan failed for {host}:{port}: {e}")
            return {
                'error': str(e),
                'host': host,
                'port': port,
                'scan_time': datetime.now(timezone.utc).isoformat()
            }
    
    # === RTSP STREAM DISCOVERY ===
    
    async def scan_rtsp_streams(self, 
                                host: str, 
                                port: int = 554,
                                common_paths: Optional[List[str]] = None,
                                timeout: int = 10) -> Dict[str, Any]:
        """
        Discover RTSP streams on target host.
        
        Args:
            host: Target host
            port: RTSP port (default 554)
            common_paths: List of common RTSP paths to test
            timeout: Connection timeout
            
        Returns:
            RTSP stream discovery results
        """
        try:
            logger.debug(f"Scanning RTSP streams on {host}:{port}")
            
            if common_paths is None:
                common_paths = self._get_common_rtsp_paths()
            
            results = {
                'host': host,
                'port': port,
                'available_streams': [],
                'auth_required': [],
                'errors': [],
                'scan_time': datetime.now(timezone.utc).isoformat()
            }
            
            # Test each common path
            for path in common_paths:
                try:
                    rtsp_url = f"rtsp://{host}:{port}{path}"
                    stream_info = await self._test_rtsp_stream(rtsp_url, timeout)
                    
                    if stream_info['status'] == 'available':
                        results['available_streams'].append(stream_info)
                    elif stream_info['status'] == 'auth_required':
                        results['auth_required'].append(stream_info)
                    else:
                        results['errors'].append(stream_info)
                        
                except Exception as e:
                    results['errors'].append({
                        'path': path,
                        'error': str(e)
                    })
            
            return results
            
        except Exception as e:
            logger.error(f"RTSP scan failed for {host}:{port}: {e}")
            return {
                'error': str(e),
                'host': host,
                'port': port,
                'scan_time': datetime.now(timezone.utc).isoformat()
            }
    
    def _get_common_rtsp_paths(self) -> List[str]:
        """Get list of common RTSP stream paths."""
        return [
            '/',
            '/stream',
            '/live',
            '/cam',
            '/video',
            '/stream1',
            '/stream2',
            '/h264',
            '/mjpeg',
            '/mpeg4',
            '/axis-media/media.amp',
            '/axis-media/media.3gp',
            '/MediaInput/h264',
            '/MediaInput/mpeg4',
            '/live.sdp',
            '/stream.sdp',
            '/cam1',
            '/cam2',
            '/camera',
            '/channel1',
            '/channel2',
            '/onvif1',
            '/onvif2',
            '/profile1',
            '/profile2',
            '/VideoInput/1/h264/1',
            '/VideoInput/1/mpeg4/1',
            '/streaming/channels/1',
            '/streaming/channels/2',
            '/PSIA/streaming/channels/1',
            '/PSIA/streaming/channels/2'
        ]
    
    async def _test_rtsp_stream(self, rtsp_url: str, timeout: int) -> Dict[str, Any]:
        """Test individual RTSP stream."""
        try:
            # Parse RTSP URL
            parsed = urlparse(rtsp_url)
            host = parsed.hostname
            port = parsed.port or 554
            path = parsed.path
            
            # Create RTSP OPTIONS request
            options_request = (
                f"OPTIONS {rtsp_url} RTSP/1.0\r\n"
                f"CSeq: 1\r\n"
                f"User-Agent: UPnP-CLI-Scanner/1.0\r\n"
                f"\r\n"
            )
            
            # Connect and send request
            with socket.create_connection((host, port), timeout) as sock:
                sock.send(options_request.encode())
                response = sock.recv(4096).decode('utf-8', errors='ignore')
            
            # Parse response
            lines = response.split('\r\n')
            status_line = lines[0] if lines else ''
            
            result = {
                'url': rtsp_url,
                'path': path,
                'response': response[:500],  # Truncate for readability
                'status': 'unknown'
            }
            
            if 'RTSP/1.0 200 OK' in status_line:
                result['status'] = 'available'
                # Extract additional info from headers
                for line in lines[1:]:
                    if line.startswith('Public:'):
                        result['methods'] = [m.strip() for m in line.split(':', 1)[1].split(',')]
                    elif line.startswith('Server:'):
                        result['server'] = line.split(':', 1)[1].strip()
            elif 'RTSP/1.0 401' in status_line:
                result['status'] = 'auth_required'
                # Extract auth method
                for line in lines[1:]:
                    if line.startswith('WWW-Authenticate:'):
                        result['auth_method'] = line.split(':', 1)[1].strip()
            elif 'RTSP/1.0 404' in status_line:
                result['status'] = 'not_found'
            else:
                result['status'] = 'error'
                result['error'] = status_line
            
            return result
            
        except Exception as e:
            return {
                'url': rtsp_url,
                'path': urlparse(rtsp_url).path,
                'status': 'error',
                'error': str(e)
            }
    
    # === VULNERABILITY ASSESSMENT ===
    
    async def assess_device_security(self, 
                                     host: str, 
                                     ports: Optional[List[int]] = None,
                                     timeout: int = 10) -> Dict[str, Any]:
        """
        Comprehensive security assessment of a device.
        
        Args:
            host: Target host
            ports: List of ports to scan (default: common media device ports)
            timeout: Connection timeout
            
        Returns:
            Security assessment results
        """
        try:
            logger.info(f"Starting security assessment for {host}")
            
            if ports is None:
                ports = [80, 443, 554, 1400, 7000, 8008, 8060, 8443, 9080, 55001]
            
            assessment = {
                'host': host,
                'scan_time': datetime.now(timezone.utc).isoformat(),
                'ssl_results': {},
                'rtsp_results': {},
                'open_ports': [],
                'vulnerabilities': [],
                'security_score': 0
            }
            
            # Scan for open ports first
            open_ports = await self._scan_ports(host, ports, timeout)
            assessment['open_ports'] = open_ports
            
            # SSL/TLS scanning on HTTPS ports
            https_ports = [p for p in open_ports if p in [443, 8443, 1443]]
            for port in https_ports:
                ssl_result = await self.scan_ssl_certificate(host, port, timeout)
                cipher_result = await self.scan_ssl_ciphers(host, port, timeout)
                
                assessment['ssl_results'][port] = {
                    'certificate': ssl_result,
                    'ciphers': cipher_result
                }
                
                # Collect vulnerabilities
                if 'vulnerabilities' in ssl_result:
                    assessment['vulnerabilities'].extend(ssl_result['vulnerabilities'])
                if 'vulnerabilities' in cipher_result:
                    assessment['vulnerabilities'].extend(cipher_result['vulnerabilities'])
            
            # RTSP scanning
            rtsp_ports = [p for p in open_ports if p in [554, 7000]]
            for port in rtsp_ports:
                rtsp_result = await self.scan_rtsp_streams(host, port, timeout=timeout)
                assessment['rtsp_results'][port] = rtsp_result
            
            # Calculate security score (0-100, higher is better)
            assessment['security_score'] = self._calculate_security_score(assessment)
            
            logger.info(f"Security assessment completed for {host} (score: {assessment['security_score']})")
            return assessment
            
        except Exception as e:
            logger.error(f"Security assessment failed for {host}: {e}")
            return {
                'error': str(e),
                'host': host,
                'scan_time': datetime.now(timezone.utc).isoformat()
            }
    
    async def _scan_ports(self, host: str, ports: List[int], timeout: int) -> List[int]:
        """Scan for open ports on target host."""
        open_ports = []
        
        async def check_port(port):
            try:
                _, writer = await asyncio.wait_for(
                    asyncio.open_connection(host, port), 
                    timeout=timeout
                )
                writer.close()
                await writer.wait_closed()
                return port
            except:
                return None
        
        # Run port checks in parallel
        tasks = [check_port(port) for port in ports]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, int):
                open_ports.append(result)
        
        return sorted(open_ports)
    
    def _calculate_security_score(self, assessment: Dict) -> int:
        """Calculate security score based on assessment results."""
        score = 100  # Start with perfect score
        
        # Deduct points for vulnerabilities
        vuln_count = len(assessment.get('vulnerabilities', []))
        score -= min(vuln_count * 10, 50)  # Max 50 points deduction
        
        # Deduct points for too many open ports
        open_port_count = len(assessment.get('open_ports', []))
        if open_port_count > 5:
            score -= (open_port_count - 5) * 5
        
        # Deduct points for SSL issues
        ssl_results = assessment.get('ssl_results', {})
        for port_result in ssl_results.values():
            cert_info = port_result.get('certificate', {})
            if cert_info.get('is_expired'):
                score -= 20
            if cert_info.get('is_self_signed'):
                score -= 10
            
            cipher_info = port_result.get('ciphers', {})
            weak_cipher_count = len(cipher_info.get('weak_ciphers', []))
            score -= weak_cipher_count * 5
        
        # Deduct points for unprotected RTSP streams
        rtsp_results = assessment.get('rtsp_results', {})
        for port_result in rtsp_results.values():
            available_streams = port_result.get('available_streams', [])
            score -= len(available_streams) * 10  # Unprotected streams
        
        return max(score, 0)  # Don't go below 0


# === GLOBAL FUNCTIONS ===

# Global scanner instance
_ssl_rtsp_scanner = None

def get_ssl_rtsp_scanner() -> SSLRTSPScanner:
    """
    Get global SSL/RTSP scanner instance.
    
    Returns:
        SSLRTSPScanner instance
    """
    global _ssl_rtsp_scanner
    if _ssl_rtsp_scanner is None:
        _ssl_rtsp_scanner = SSLRTSPScanner()
    return _ssl_rtsp_scanner


# === CONVENIENCE FUNCTIONS ===

async def scan_ssl_cert(host: str, port: int = 443, timeout: int = 10) -> Dict[str, Any]:
    """Convenience function to scan SSL certificate."""
    scanner = get_ssl_rtsp_scanner()
    return await scanner.scan_ssl_certificate(host, port, timeout)

async def scan_ssl_ciphers(host: str, port: int = 443, timeout: int = 10) -> Dict[str, Any]:
    """Convenience function to scan SSL ciphers."""
    scanner = get_ssl_rtsp_scanner()
    return await scanner.scan_ssl_ciphers(host, port, timeout)

async def scan_rtsp_streams(host: str, port: int = 554, timeout: int = 10) -> Dict[str, Any]:
    """Convenience function to scan RTSP streams."""
    scanner = get_ssl_rtsp_scanner()
    return await scanner.scan_rtsp_streams(host, port, timeout=timeout)

async def assess_device_security(host: str, ports: Optional[List[int]] = None, timeout: int = 10) -> Dict[str, Any]:
    """Convenience function for comprehensive security assessment."""
    scanner = get_ssl_rtsp_scanner()
    return await scanner.assess_device_security(host, ports, timeout)


# === REPORT GENERATION ===

def generate_security_report(assessment: Dict[str, Any]) -> str:
    """
    Generate human-readable security report.
    
    Args:
        assessment: Security assessment results
        
    Returns:
        Formatted security report
    """
    host = assessment.get('host', 'Unknown')
    score = assessment.get('security_score', 0)
    scan_time = assessment.get('scan_time', 'Unknown')
    
    report = []
    report.append("=" * 60)
    report.append(f"SECURITY ASSESSMENT REPORT")
    report.append("=" * 60)
    report.append(f"Target: {host}")
    report.append(f"Scan Time: {scan_time}")
    report.append(f"Security Score: {score}/100")
    report.append("")
    
    # Security score interpretation
    if score >= 80:
        report.append("🟢 GOOD - Device has strong security posture")
    elif score >= 60:
        report.append("🟡 MODERATE - Some security concerns identified")
    elif score >= 40:
        report.append("🟠 POOR - Multiple security issues found")
    else:
        report.append("🔴 CRITICAL - Severe security vulnerabilities")
    
    report.append("")
    
    # Open ports
    open_ports = assessment.get('open_ports', [])
    if open_ports:
        report.append(f"Open Ports: {', '.join(map(str, open_ports))}")
    else:
        report.append("Open Ports: None detected")
    report.append("")
    
    # SSL/TLS results
    ssl_results = assessment.get('ssl_results', {})
    if ssl_results:
        report.append("SSL/TLS Analysis:")
        for port, result in ssl_results.items():
            cert_info = result.get('certificate', {})
            report.append(f"  Port {port}:")
            if 'error' in cert_info:
                report.append(f"    Error: {cert_info['error']}")
            else:
                subject = cert_info.get('subject', {})
                report.append(f"    Subject: {subject.get('commonName', 'Unknown')}")
                report.append(f"    Issuer: {cert_info.get('issuer', {}).get('commonName', 'Unknown')}")
                report.append(f"    Expires: {cert_info.get('not_after', 'Unknown')}")
                if cert_info.get('is_self_signed'):
                    report.append("    ⚠️  Self-signed certificate")
                if cert_info.get('is_expired'):
                    report.append("    ❌ Certificate expired")
        report.append("")
    
    # RTSP results
    rtsp_results = assessment.get('rtsp_results', {})
    if rtsp_results:
        report.append("RTSP Stream Analysis:")
        for port, result in rtsp_results.items():
            available = result.get('available_streams', [])
            auth_required = result.get('auth_required', [])
            report.append(f"  Port {port}:")
            if available:
                report.append(f"    ❌ {len(available)} unprotected streams found")
                for stream in available[:3]:  # Show first 3
                    report.append(f"      - {stream['path']}")
            if auth_required:
                report.append(f"    🔒 {len(auth_required)} protected streams found")
            if not available and not auth_required:
                report.append("    ✅ No RTSP streams accessible")
        report.append("")
    
    # Vulnerabilities
    vulnerabilities = assessment.get('vulnerabilities', [])
    if vulnerabilities:
        report.append(f"Vulnerabilities Found ({len(vulnerabilities)}):")
        for i, vuln in enumerate(vulnerabilities[:10], 1):  # Show first 10
            report.append(f"  {i}. {vuln}")
        if len(vulnerabilities) > 10:
            report.append(f"  ... and {len(vulnerabilities) - 10} more")
    else:
        report.append("✅ No major vulnerabilities detected")
    
    report.append("")
    report.append("=" * 60)
    
    return "\n".join(report)