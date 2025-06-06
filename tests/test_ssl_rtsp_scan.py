"""
Tests for SSL/RTSP scanner module.
"""

import pytest
import asyncio
import socket
import ssl
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime, timezone

from upnp_cli.ssl_rtsp_scan import (
    SSLRTSPScanner, SecurityScanError, get_ssl_rtsp_scanner,
    scan_ssl_cert, scan_ssl_ciphers, scan_rtsp_streams, assess_device_security,
    generate_security_report
)


class TestSSLRTSPScanner:
    """Test SSLRTSPScanner class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.scanner = SSLRTSPScanner()
    
    def test_scanner_initialization(self):
        """Test scanner initialization."""
        assert self.scanner is not None
    
    @pytest.mark.asyncio
    @patch('socket.create_connection')
    @patch('ssl.create_default_context')
    async def test_scan_ssl_certificate_success(self, mock_ssl_context, mock_socket):
        """Test successful SSL certificate scan."""
        # Mock certificate data
        mock_cert = {
            'subject': [(('commonName', 'example.com'),)],
            'issuer': [(('commonName', 'CA Authority'),)],
            'version': 3,
            'serialNumber': '123456789',
            'notBefore': 'Jan  1 00:00:00 2023 GMT',
            'notAfter': 'Dec 31 23:59:59 2025 GMT',  # Future date
            'subjectAltName': [('DNS', 'example.com')],
            'signatureAlgorithm': 'sha256WithRSAEncryption'
        }
        
        mock_cert_der = b'mock_cert_data'
        mock_cipher = ('TLS_AES_256_GCM_SHA384', 'TLSv1.3', 256)
        mock_version = 'TLSv1.3'
        
        # Setup mocks
        mock_ssock = Mock()
        mock_ssock.getpeercert.return_value = mock_cert
        mock_ssock.getpeercert.side_effect = [mock_cert, mock_cert_der]
        mock_ssock.cipher.return_value = mock_cipher
        mock_ssock.version.return_value = mock_version
        mock_ssock.__enter__ = Mock(return_value=mock_ssock)
        mock_ssock.__exit__ = Mock(return_value=None)
        
        mock_context_instance = Mock()
        mock_context_instance.wrap_socket.return_value = mock_ssock
        mock_ssl_context.return_value = mock_context_instance
        
        mock_sock = Mock()
        mock_sock.__enter__ = Mock(return_value=mock_sock)
        mock_sock.__exit__ = Mock(return_value=None)
        mock_socket.return_value = mock_sock
        
        result = await self.scanner.scan_ssl_certificate('example.com', 443)
        
        assert result['host'] == 'example.com'
        assert result['port'] == 443
        assert result['subject']['commonName'] == 'example.com'
        assert result['issuer']['commonName'] == 'CA Authority'
        assert result['cipher'] == mock_cipher
        assert result['ssl_version'] == mock_version
        assert 'scan_time' in result
    
    @pytest.mark.asyncio
    @patch('socket.create_connection')
    async def test_scan_ssl_certificate_failure(self, mock_socket):
        """Test SSL certificate scan failure."""
        mock_socket.side_effect = socket.timeout("Connection timeout")
        
        result = await self.scanner.scan_ssl_certificate('invalid.host', 443)
        
        assert 'error' in result
        assert result['host'] == 'invalid.host'
        assert result['port'] == 443
        assert 'Connection timeout' in result['error']
    
    def test_analyze_certificate_basic(self):
        """Test basic certificate analysis."""
        mock_cert = {
            'subject': [(('commonName', 'example.com'),)],
            'issuer': [(('commonName', 'CA Authority'),)],
            'version': 3,
            'serialNumber': '123456789',
            'notBefore': 'Jan  1 00:00:00 2023 GMT',
            'notAfter': 'Dec 31 23:59:59 2025 GMT',  # Future date with correct format
            'signatureAlgorithm': 'sha256WithRSAEncryption'
        }
        
        mock_cert_der = b'mock_cert_data' * 100  # Make it larger
        
        result = self.scanner._analyze_certificate(mock_cert, mock_cert_der)
        
        assert result['subject']['commonName'] == 'example.com'
        assert result['issuer']['commonName'] == 'CA Authority'
        assert result['is_expired'] is False
        assert result['is_self_signed'] is False
        assert len(result['vulnerabilities']) == 0
    
    def test_analyze_certificate_self_signed(self):
        """Test analysis of self-signed certificate."""
        mock_cert = {
            'subject': [(('commonName', 'example.com'),)],
            'issuer': [(('commonName', 'example.com'),)],  # Same as subject
            'signatureAlgorithm': 'sha256WithRSAEncryption'
        }
        
        result = self.scanner._analyze_certificate(mock_cert, b'mock_cert_data')
        
        assert result['is_self_signed'] is True
        assert 'Self-signed certificate' in result['vulnerabilities']
    
    def test_analyze_certificate_weak_signature(self):
        """Test analysis of certificate with weak signature."""
        mock_cert = {
            'subject': [(('commonName', 'example.com'),)],
            'issuer': [(('commonName', 'CA Authority'),)],
            'signatureAlgorithm': 'sha1WithRSAEncryption'  # Weak algorithm
        }
        
        result = self.scanner._analyze_certificate(mock_cert, b'mock_cert_data')
        
        assert any('Weak signature algorithm' in vuln for vuln in result['vulnerabilities'])
    
    @pytest.mark.asyncio
    @patch('socket.create_connection')
    @patch('ssl.SSLContext')
    async def test_scan_ssl_ciphers_success(self, mock_ssl_context_class, mock_socket):
        """Test successful SSL cipher scan."""
        # Mock SSL context and socket
        mock_ssock = Mock()
        mock_ssock.version.return_value = 'TLSv1.2'
        mock_ssock.cipher.return_value = ('TLS_RSA_WITH_AES_256_GCM_SHA384', 'TLSv1.2', 256)
        
        mock_context = Mock()
        mock_context.wrap_socket.return_value = mock_ssock
        mock_ssl_context_class.return_value = mock_context
        
        mock_sock = Mock()
        mock_sock.__enter__ = Mock(return_value=mock_sock)
        mock_sock.__exit__ = Mock(return_value=None)
        mock_socket.return_value = mock_sock
        
        result = await self.scanner.scan_ssl_ciphers('example.com', 443)
        
        assert result['host'] == 'example.com'
        assert result['port'] == 443
        assert isinstance(result['supported_protocols'], list)
        assert isinstance(result['supported_ciphers'], list)
        assert isinstance(result['weak_ciphers'], list)
        assert isinstance(result['vulnerabilities'], list)
    
    @pytest.mark.asyncio
    @patch('socket.create_connection')
    async def test_scan_ssl_ciphers_failure(self, mock_socket):
        """Test SSL cipher scan failure."""
        mock_socket.side_effect = ConnectionRefusedError("Connection refused")
        
        result = await self.scanner.scan_ssl_ciphers('invalid.host', 443)
        
        # The cipher scan might return an empty result or an error field
        assert result['host'] == 'invalid.host'
        assert result['port'] == 443
        # May have 'error' field or just empty lists when connection fails
        assert ('error' in result and 'Connection refused' in result['error']) or len(result['supported_protocols']) == 0
    
    def test_get_common_rtsp_paths(self):
        """Test RTSP path list generation."""
        paths = self.scanner._get_common_rtsp_paths()
        
        assert isinstance(paths, list)
        assert len(paths) > 0
        assert '/' in paths
        assert '/stream' in paths
        assert '/live' in paths
        assert all(path.startswith('/') for path in paths)
    
    @pytest.mark.asyncio
    @patch('socket.create_connection')
    async def test_test_rtsp_stream_available(self, mock_socket):
        """Test RTSP stream testing - available stream."""
        mock_response = (
            "RTSP/1.0 200 OK\r\n"
            "CSeq: 1\r\n"
            "Public: DESCRIBE, SETUP, TEARDOWN, PLAY, PAUSE\r\n"
            "Server: Test RTSP Server/1.0\r\n"
            "\r\n"
        )
        
        mock_sock = Mock()
        mock_sock.recv.return_value = mock_response.encode()
        mock_socket.return_value.__enter__.return_value = mock_sock
        
        result = await self.scanner._test_rtsp_stream('rtsp://example.com:554/stream', 10)
        
        assert result['status'] == 'available'
        assert result['url'] == 'rtsp://example.com:554/stream'
        assert result['path'] == '/stream'
        assert 'methods' in result
        assert 'DESCRIBE' in result['methods']
        assert 'server' in result
    
    @pytest.mark.asyncio
    @patch('socket.create_connection')
    async def test_test_rtsp_stream_auth_required(self, mock_socket):
        """Test RTSP stream testing - authentication required."""
        mock_response = (
            "RTSP/1.0 401 Unauthorized\r\n"
            "CSeq: 1\r\n"
            "WWW-Authenticate: Basic realm=\"RTSP Server\"\r\n"
            "\r\n"
        )
        
        mock_sock = Mock()
        mock_sock.recv.return_value = mock_response.encode()
        mock_socket.return_value.__enter__.return_value = mock_sock
        
        result = await self.scanner._test_rtsp_stream('rtsp://example.com:554/auth', 10)
        
        assert result['status'] == 'auth_required'
        assert 'auth_method' in result
        assert 'Basic' in result['auth_method']
    
    @pytest.mark.asyncio
    @patch('socket.create_connection')
    async def test_test_rtsp_stream_not_found(self, mock_socket):
        """Test RTSP stream testing - not found."""
        mock_response = "RTSP/1.0 404 Not Found\r\nCSeq: 1\r\n\r\n"
        
        mock_sock = Mock()
        mock_sock.recv.return_value = mock_response.encode()
        mock_socket.return_value.__enter__.return_value = mock_sock
        
        result = await self.scanner._test_rtsp_stream('rtsp://example.com:554/missing', 10)
        
        assert result['status'] == 'not_found'
    
    @pytest.mark.asyncio
    @patch('socket.create_connection')
    async def test_test_rtsp_stream_error(self, mock_socket):
        """Test RTSP stream testing - connection error."""
        mock_socket.side_effect = socket.timeout("Connection timeout")
        
        result = await self.scanner._test_rtsp_stream('rtsp://invalid.host:554/stream', 10)
        
        assert result['status'] == 'error'
        assert 'Connection timeout' in result['error']
    
    @pytest.mark.asyncio
    async def test_scan_rtsp_streams_success(self):
        """Test RTSP streams scanning."""
        # Mock the _test_rtsp_stream method
        mock_results = [
            {'status': 'available', 'path': '/stream1', 'url': 'rtsp://example.com:554/stream1'},
            {'status': 'auth_required', 'path': '/stream2', 'url': 'rtsp://example.com:554/stream2'},
            {'status': 'not_found', 'path': '/missing', 'url': 'rtsp://example.com:554/missing'}
        ]
        
        with patch.object(self.scanner, '_test_rtsp_stream', side_effect=mock_results):
            result = await self.scanner.scan_rtsp_streams('example.com', 554, ['/stream1', '/stream2', '/missing'])
        
        assert result['host'] == 'example.com'
        assert result['port'] == 554
        assert len(result['available_streams']) == 1
        assert len(result['auth_required']) == 1
        assert len(result['errors']) == 1
    
    @pytest.mark.asyncio
    @patch.object(SSLRTSPScanner, '_scan_ports')
    @patch.object(SSLRTSPScanner, 'scan_ssl_certificate')
    @patch.object(SSLRTSPScanner, 'scan_ssl_ciphers')
    @patch.object(SSLRTSPScanner, 'scan_rtsp_streams')
    async def test_assess_device_security(self, mock_rtsp, mock_ciphers, mock_cert, mock_ports):
        """Test comprehensive device security assessment."""
        # Setup mocks
        mock_ports.return_value = [80, 443, 554, 1400]
        
        mock_cert.return_value = {
            'host': 'example.com',
            'port': 443,
            'is_expired': False,
            'is_self_signed': False,
            'vulnerabilities': []
        }
        
        mock_ciphers.return_value = {
            'host': 'example.com',
            'port': 443,
            'weak_ciphers': [],
            'vulnerabilities': []
        }
        
        mock_rtsp.return_value = {
            'host': 'example.com',
            'port': 554,
            'available_streams': [],
            'auth_required': []
        }
        
        result = await self.scanner.assess_device_security('example.com')
        
        assert result['host'] == 'example.com'
        assert result['open_ports'] == [80, 443, 554, 1400]
        assert 'ssl_results' in result
        assert 'rtsp_results' in result
        assert 'security_score' in result
        assert isinstance(result['security_score'], int)
        assert 0 <= result['security_score'] <= 100
    
    @pytest.mark.asyncio
    async def test_scan_ports(self):
        """Test port scanning functionality."""
        # Mock successful connection to port 80
        async def mock_open_connection(host, port):
            if port == 80:
                mock_writer = Mock()
                mock_writer.close = Mock()
                mock_writer.wait_closed = AsyncMock()
                return None, mock_writer  # Simulate successful connection
            else:
                raise ConnectionRefusedError()
        
        # Mock wait_for to just return the result of the coroutine
        async def mock_wait_for(coro, timeout):
            return await coro
        
        with patch('asyncio.open_connection', side_effect=mock_open_connection):
            with patch('asyncio.wait_for', side_effect=mock_wait_for):
                open_ports = await self.scanner._scan_ports('example.com', [80, 443, 8080], 5)
        
        assert 80 in open_ports
        assert 443 not in open_ports
        assert 8080 not in open_ports
    
    def test_calculate_security_score_perfect(self):
        """Test security score calculation - perfect score."""
        assessment = {
            'vulnerabilities': [],
            'open_ports': [80, 443],
            'ssl_results': {
                443: {
                    'certificate': {'is_expired': False, 'is_self_signed': False},
                    'ciphers': {'weak_ciphers': []}
                }
            },
            'rtsp_results': {
                554: {'available_streams': []}
            }
        }
        
        score = self.scanner._calculate_security_score(assessment)
        assert score == 100
    
    def test_calculate_security_score_with_issues(self):
        """Test security score calculation with security issues."""
        assessment = {
            'vulnerabilities': ['Weak cipher', 'Self-signed cert'],
            'open_ports': [80, 443, 554, 1400, 8008, 8060, 9080],  # Too many ports
            'ssl_results': {
                443: {
                    'certificate': {'is_expired': True, 'is_self_signed': True},
                    'ciphers': {'weak_ciphers': [('RC4', 'TLSv1.0', 128)]}
                }
            },
            'rtsp_results': {
                554: {'available_streams': [{'path': '/stream1'}, {'path': '/stream2'}]}
            }
        }
        
        score = self.scanner._calculate_security_score(assessment)
        assert score < 100
        assert score >= 0


class TestGlobalFunctions:
    """Test global convenience functions."""
    
    @pytest.mark.asyncio
    @patch('upnp_cli.ssl_rtsp_scan.SSLRTSPScanner')
    async def test_get_ssl_rtsp_scanner_singleton(self, mock_scanner_class):
        """Test global scanner singleton."""
        mock_instance = Mock()
        mock_scanner_class.return_value = mock_instance
        
        # Reset global instance
        import upnp_cli.ssl_rtsp_scan
        upnp_cli.ssl_rtsp_scan._ssl_rtsp_scanner = None
        
        scanner1 = get_ssl_rtsp_scanner()
        scanner2 = get_ssl_rtsp_scanner()
        
        assert scanner1 is scanner2
        mock_scanner_class.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('upnp_cli.ssl_rtsp_scan.get_ssl_rtsp_scanner')
    async def test_convenience_functions(self, mock_get_scanner):
        """Test convenience functions."""
        mock_scanner = AsyncMock()
        mock_get_scanner.return_value = mock_scanner
        
        # Test scan_ssl_cert
        mock_scanner.scan_ssl_certificate.return_value = {'status': 'success'}
        result = await scan_ssl_cert('example.com')
        mock_scanner.scan_ssl_certificate.assert_called_once_with('example.com', 443, 10)
        
        # Test scan_ssl_ciphers
        mock_scanner.scan_ssl_ciphers.return_value = {'status': 'success'}
        result = await scan_ssl_ciphers('example.com', port=8443)
        mock_scanner.scan_ssl_ciphers.assert_called_once_with('example.com', 8443, 10)
        
        # Test scan_rtsp_streams
        mock_scanner.scan_rtsp_streams.return_value = {'status': 'success'}
        result = await scan_rtsp_streams('example.com')
        mock_scanner.scan_rtsp_streams.assert_called_once_with('example.com', 554, timeout=10)
        
        # Test assess_device_security
        mock_scanner.assess_device_security.return_value = {'security_score': 85}
        result = await assess_device_security('example.com')
        mock_scanner.assess_device_security.assert_called_once_with('example.com', None, 10)


class TestReportGeneration:
    """Test security report generation."""
    
    def test_generate_security_report_good_score(self):
        """Test report generation for good security score."""
        assessment = {
            'host': 'example.com',
            'scan_time': '2023-01-01T12:00:00Z',
            'security_score': 85,
            'open_ports': [80, 443],
            'ssl_results': {
                443: {
                    'certificate': {
                        'subject': {'commonName': 'example.com'},
                        'issuer': {'commonName': 'CA Authority'},
                        'not_after': 'Jan 1 00:00:00 2024 GMT',
                        'is_self_signed': False,
                        'is_expired': False
                    }
                }
            },
            'rtsp_results': {},
            'vulnerabilities': []
        }
        
        report = generate_security_report(assessment)
        
        assert 'SECURITY ASSESSMENT REPORT' in report
        assert 'example.com' in report
        assert '85/100' in report
        assert '🟢 GOOD' in report
        assert 'Open Ports: 80, 443' in report
        assert 'SSL/TLS Analysis:' in report
        assert '✅ No major vulnerabilities detected' in report
    
    def test_generate_security_report_poor_score(self):
        """Test report generation for poor security score."""
        assessment = {
            'host': 'vulnerable.com',
            'scan_time': '2023-01-01T12:00:00Z',
            'security_score': 30,
            'open_ports': [80, 443, 554],
            'ssl_results': {
                443: {
                    'certificate': {
                        'subject': {'commonName': 'vulnerable.com'},
                        'issuer': {'commonName': 'vulnerable.com'},  # Self-signed
                        'not_after': 'Jan 1 00:00:00 2022 GMT',  # Expired
                        'is_self_signed': True,
                        'is_expired': True
                    }
                }
            },
            'rtsp_results': {
                554: {
                    'available_streams': [
                        {'path': '/stream1'},
                        {'path': '/stream2'}
                    ],
                    'auth_required': []
                }
            },
            'vulnerabilities': [
                'Self-signed certificate',
                'Weak cipher: RC4',
                'Expired certificate'
            ]
        }
        
        report = generate_security_report(assessment)
        
        assert 'vulnerable.com' in report
        assert '30/100' in report
        assert '🔴 CRITICAL' in report
        assert '⚠️  Self-signed certificate' in report
        assert '❌ Certificate expired' in report
        assert '❌ 2 unprotected streams found' in report
        assert 'Vulnerabilities Found (3):' in report
        assert '1. Self-signed certificate' in report
    
    def test_generate_security_report_no_issues(self):
        """Test report generation with no security issues."""
        assessment = {
            'host': 'secure.com',
            'scan_time': '2023-01-01T12:00:00Z',
            'security_score': 100,
            'open_ports': [443],
            'ssl_results': {},
            'rtsp_results': {},
            'vulnerabilities': []
        }
        
        report = generate_security_report(assessment)
        
        assert '100/100' in report
        assert '🟢 GOOD' in report
        assert '✅ No major vulnerabilities detected' in report


class TestSecurityScanError:
    """Test SecurityScanError exception."""
    
    def test_security_scan_error_creation(self):
        """Test SecurityScanError creation with different parameters."""
        # Basic error
        error = SecurityScanError("Test error")
        assert str(error) == "Test error"
        assert error.error_code is None
        assert error.target is None
        
        # Error with code
        error = SecurityScanError("Test error", error_code=500)
        assert error.error_code == 500
        
        # Error with target
        error = SecurityScanError("Test error", target="example.com:443")
        assert error.target == "example.com:443"