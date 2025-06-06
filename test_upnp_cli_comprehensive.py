#!/usr/bin/env python3
"""
Comprehensive UPnP CLI Test Suite
Tests all functionality and reports success/failure with detailed logging.
"""

import subprocess
import json
import time
import sys
import os
from datetime import datetime
from typing import Dict, List, Tuple, Any
import tempfile
import signal

class UPnPCLITester:
    def __init__(self):
        self.results = {
            'discovery': {},
            'device_control': {},
            'media_control': {},
            'security_scanning': {},
            'server_management': {},
            'cache_management': {},
            'routines': {},
            'mass_operations': {},
            'edge_cases': {}
        }
        self.discovered_devices = []
        self.test_host = None
        self.test_port = None
        self.media_host = None  # Separate host for media control tests
        self.media_port = None
        self.start_time = datetime.now()
        
    def log(self, message: str, level: str = "INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        symbols = {
            "SUCCESS": "✅",
            "FAILURE": "❌", 
            "WARNING": "⚠️",
            "INFO": "ℹ️",
            "TESTING": "🧪"
        }
        symbol = symbols.get(level, "ℹ️")
        print(f"{timestamp} [{level}] {symbol} {message}")
        
    def run_command(self, cmd: str, timeout: int = 30, capture_json: bool = False) -> Tuple[bool, str, str]:
        """Run a upnp-cli command and return (success, stdout, stderr)"""
        try:
            full_cmd = f"upnp-cli {cmd}"
            if capture_json and "--json" not in cmd:
                full_cmd += " --json"
                
            self.log(f"Running: {full_cmd}", "TESTING")
            
            result = subprocess.run(
                full_cmd.split(),
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=os.getcwd()
            )
            
            success = result.returncode == 0
            return success, result.stdout, result.stderr
            
        except subprocess.TimeoutExpired:
            return False, "", f"Command timed out after {timeout}s"
        except Exception as e:
            return False, "", f"Exception: {str(e)}"
    
    def test_discovery_commands(self):
        """Test all discovery-related commands"""
        self.log("Testing Discovery Commands", "INFO")
        
        # Test basic discovery
        success, stdout, stderr = self.run_command("discover", timeout=60)
        self.results['discovery']['basic_discover'] = {
            'success': success,
            'output_length': len(stdout),
            'error': stderr if not success else None
        }
        
        if success:
            self.log("Discovery command succeeded", "SUCCESS")
            # Try to parse devices from output
            try:
                lines = stdout.split('\n')
                device_count = 0
                for line in lines:
                    if 'IP Address' in line and 'Port' in line:
                        continue
                    if line.strip() and not line.startswith('🔍') and not line.startswith('✅'):
                        parts = line.split()
                        if len(parts) >= 2 and parts[0].count('.') == 3:  # IP address
                            device_count += 1
                            try:
                                ip = parts[0]
                                port = int(parts[1])
                                device_name = ' '.join(parts[2:]) if len(parts) > 2 else ''
                                
                                # Store first valid device for general testing
                                if not self.test_host:
                                    self.test_host = ip
                                    self.test_port = port
                                    self.log(f"Using test device: {self.test_host}:{self.test_port}", "INFO")
                                
                                # Look for media renderer devices (prioritize Sonos)
                                if not self.media_host:
                                    # Prioritize Sonos devices
                                    if 'sonos' in device_name.lower() or port == 1400:
                                        self.media_host = ip
                                        self.media_port = port
                                        self.log(f"Using media device: {self.media_host}:{self.media_port} ({device_name})", "INFO")
                                    # Fall back to other media renderers
                                    elif ('mediarenderer' in device_name.lower() or
                                          'speaker' in device_name.lower() or
                                          'renderer' in device_name.lower()):
                                        # Skip obvious non-media devices and problematic ports
                                        if (not any(x in device_name.lower() for x in ['router', 'gateway', 'bridge', 'switch', 'tv']) and
                                            port not in [38400]):  # Skip problematic TV port
                                            self.media_host = ip
                                            self.media_port = port
                                            self.log(f"Using media device: {self.media_host}:{self.media_port} ({device_name})", "INFO")
                                        
                            except ValueError:
                                pass
                
                self.results['discovery']['device_count'] = device_count
                self.log(f"Discovered {device_count} devices", "SUCCESS")
                
            except Exception as e:
                self.log(f"Failed to parse discovery output: {e}", "WARNING")
        else:
            self.log(f"Discovery failed: {stderr}", "FAILURE")
            
        # Test discovery with verbose
        success, stdout, stderr = self.run_command("--verbose discover", timeout=60)
        self.results['discovery']['verbose_discover'] = {
            'success': success,
            'output_length': len(stdout),
            'has_debug_info': '[DEBUG]' in stdout or '[INFO]' in stdout
        }
        
        # Test discovery with JSON output
        success, stdout, stderr = self.run_command("--json discover", timeout=60)
        self.results['discovery']['json_discover'] = {
            'success': success,
            'valid_json': False
        }
        
        if success:
            try:
                json.loads(stdout)
                self.results['discovery']['json_discover']['valid_json'] = True
                self.log("JSON discovery output is valid", "SUCCESS")
            except json.JSONDecodeError:
                self.log("JSON discovery output is invalid", "FAILURE")
    
    def test_device_info_commands(self):
        """Test device information commands"""
        self.log("Testing Device Information Commands", "INFO")
        
        if not self.test_host or not self.test_port:
            self.log("No test device available, skipping device info tests", "WARNING")
            return
            
        # Test info command
        success, stdout, stderr = self.run_command(f"--host {self.test_host} --port {self.test_port} info")
        self.results['device_control']['info'] = {
            'success': success,
            'has_device_info': 'Device Information' in stdout or 'IP Address' in stdout,
            'error': stderr if not success else None
        }
        
        if success:
            self.log("Device info command succeeded", "SUCCESS")
        else:
            self.log(f"Device info failed: {stderr}", "FAILURE")
            
        # Test services command
        success, stdout, stderr = self.run_command(f"--host {self.test_host} --port {self.test_port} services")
        self.results['device_control']['services'] = {
            'success': success,
            'has_services': 'Available Services' in stdout or 'service' in stdout.lower(),
            'error': stderr if not success else None
        }
        
        if success:
            self.log("Services command succeeded", "SUCCESS")
        else:
            self.log(f"Services command failed: {stderr}", "FAILURE")
    
    def test_media_control_commands(self):
        """Test all media control commands"""
        self.log("Testing Media Control Commands", "INFO")
        
        # Use media device if available, otherwise fall back to test device
        if self.media_host and self.media_port:
            test_host, test_port = self.media_host, self.media_port
            self.log(f"Using dedicated media device for media tests: {test_host}:{test_port}", "INFO")
        elif self.test_host and self.test_port:
            # Try known Sonos device first if available
            sonos_test_host, sonos_test_port = "192.168.4.152", 1400
            sonos_available = False
            try:
                success, _, _ = self.run_command(f"--host {sonos_test_host} --port {sonos_test_port} info", timeout=5)
                if success:
                    test_host, test_port = sonos_test_host, sonos_test_port
                    sonos_available = True
                    self.log(f"Using known Sonos device for media tests: {test_host}:{test_port}", "INFO")
            except:
                pass
            
            if not sonos_available:
                test_host, test_port = self.test_host, self.test_port
                self.log(f"Using general test device for media tests: {test_host}:{test_port} (may fail)", "WARNING")
        else:
            self.log("No test device available, skipping media control tests", "WARNING")
            return
            
        media_commands = [
            'get-volume',
            'get-mute', 
            'play',
            'pause',
            'stop',
            'next',
            'previous'
        ]
        
        for cmd in media_commands:
            success, stdout, stderr = self.run_command(f"--host {test_host} --port {test_port} {cmd}")
            self.results['media_control'][cmd] = {
                'success': success,
                'output': stdout[:200] if stdout else "",
                'error': stderr if not success else None
            }
            
            if success:
                self.log(f"Media command '{cmd}' succeeded", "SUCCESS")
            else:
                self.log(f"Media command '{cmd}' failed: {stderr[:200]}", "FAILURE")
                
        # Test volume setting with parameter
        success, stdout, stderr = self.run_command(f"--host {test_host} --port {test_port} set-volume 50")
        self.results['media_control']['set-volume'] = {
            'success': success,
            'output': stdout[:200] if stdout else "",
            'error': stderr if not success else None
        }
        
        # Test mute setting
        success, stdout, stderr = self.run_command(f"--host {test_host} --port {test_port} set-mute 1")
        self.results['media_control']['set-mute'] = {
            'success': success,
            'output': stdout[:200] if stdout else "",
            'error': stderr if not success else None
        }
    
    def test_security_scanning(self):
        """Test SSL and RTSP scanning commands"""
        self.log("Testing Security Scanning Commands", "INFO")
        
        if not self.test_host:
            self.log("No test device available, skipping security tests", "WARNING")
            return
            
        # Test SSL scan
        success, stdout, stderr = self.run_command(f"--host {self.test_host} --ssl-port 1443 ssl-scan")
        self.results['security_scanning']['ssl-scan'] = {
            'success': success,
            'has_ssl_info': 'ssl' in stdout.lower() or 'certificate' in stdout.lower() or 'cipher' in stdout.lower(),
            'error': stderr if not success else None
        }
        
        # Test RTSP scan
        success, stdout, stderr = self.run_command(f"--host {self.test_host} --rtsp-port 7000 rtsp-scan")
        self.results['security_scanning']['rtsp-scan'] = {
            'success': success,
            'has_rtsp_info': 'rtsp' in stdout.lower() or 'stream' in stdout.lower(),
            'error': stderr if not success else None
        }
    
    def test_server_management(self):
        """Test HTTP server start/stop commands"""
        self.log("Testing Server Management Commands", "INFO")
        
        # Test start server
        success, stdout, stderr = self.run_command("start-server --server-port 8081")
        self.results['server_management']['start-server'] = {
            'success': success,
            'output': stdout,
            'error': stderr if not success else None
        }
        
        if success:
            self.log("Server start succeeded", "SUCCESS")
            time.sleep(1)  # Brief wait
            
            # Test stop server
            success, stdout, stderr = self.run_command("stop-server")
            self.results['server_management']['stop-server'] = {
                'success': success,
                'output': stdout,
                'error': stderr if not success else None
            }
            
            if success:
                self.log("Server stop succeeded", "SUCCESS")
            else:
                self.log(f"Server stop failed: {stderr}", "FAILURE")
        else:
            self.log(f"Server start failed: {stderr}", "FAILURE")
    
    def test_cache_management(self):
        """Test cache-related commands"""
        self.log("Testing Cache Management Commands", "INFO")
        
        # Create a temporary cache file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            cache_file = f.name
            
        try:
            # Test discovery with cache
            success, stdout, stderr = self.run_command(f"--cache {cache_file} discover", timeout=30)
            self.results['cache_management']['cache_discover'] = {
                'success': success,
                'cache_file_created': os.path.exists(cache_file),
                'error': stderr[:200] if not success and stderr else None
            }
            
            if not success:
                self.log(f"Cache discover failed: {stderr[:200]}", "FAILURE")
            
            # Test clear cache
            success, stdout, stderr = self.run_command("clear-cache")
            self.results['cache_management']['clear-cache'] = {
                'success': success,
                'output': stdout,
                'error': stderr if not success else None
            }
            
        finally:
            # Clean up
            if os.path.exists(cache_file):
                os.unlink(cache_file)
    
    def test_routines(self):
        """Test routine commands"""
        self.log("Testing Routine Commands", "INFO")
        
        # Test list routines
        success, stdout, stderr = self.run_command("list-routines")
        self.results['routines']['list-routines'] = {
            'success': success,
            'has_routines': 'routine' in stdout.lower() or 'fart' in stdout.lower(),
            'output': stdout,
            'error': stderr if not success else None
        }
        
        if success:
            self.log("List routines succeeded", "SUCCESS")
        else:
            self.log(f"List routines failed: {stderr}", "FAILURE")
            
        # Note: We won't test actual routine execution to avoid disrupting devices
        self.results['routines']['routine_execution'] = {
            'success': None,
            'note': 'Skipped to avoid disrupting devices'
        }
    
    def test_mass_operations(self):
        """Test mass operation commands"""
        self.log("Testing Mass Operations Commands", "INFO")
        
        # Test mass discovery (but interrupt it quickly)
        success, stdout, stderr = self.run_command("mass", timeout=30)
        self.results['mass_operations']['mass'] = {
            'success': success,
            'started_properly': 'Mass UPnP Discovery' in stdout or 'Discovering' in stdout or 'Found' in stdout,
            'error': stderr[:200] if not success and stderr else None
        }
        
        if success or 'Mass UPnP Discovery' in stdout or 'Found' in stdout:
            self.log("Mass operation started correctly", "SUCCESS")
        else:
            self.log(f"Mass operation may have issues: {stderr[:200] if stderr else 'Unknown error'}", "WARNING")
    
    def test_edge_cases(self):
        """Test edge cases and error handling"""
        self.log("Testing Edge Cases and Error Handling", "INFO")
        
        # Test invalid host
        success, stdout, stderr = self.run_command("--host 999.999.999.999 --port 1400 info")
        self.results['edge_cases']['invalid_host'] = {
            'success': success,
            'proper_error': not success and ('timeout' in stderr.lower() or 'connection' in stderr.lower() or 'failed' in stderr.lower()),
            'error': stderr
        }
        
        # Test invalid port
        success, stdout, stderr = self.run_command("--host 127.0.0.1 --port 99999 info")
        self.results['edge_cases']['invalid_port'] = {
            'success': success,
            'error': stderr
        }
        
        # Test invalid command
        success, stdout, stderr = self.run_command("nonexistent-command")
        self.results['edge_cases']['invalid_command'] = {
            'success': success,
            'proper_error': not success and 'invalid choice' in stderr.lower(),
            'error': stderr[:200] if stderr else None
        }
        
        if not success and 'invalid choice' in stderr.lower():
            self.log("Invalid command properly rejected", "SUCCESS")
        
        # Test missing required parameters
        success, stdout, stderr = self.run_command("set-volume")
        self.results['edge_cases']['missing_params'] = {
            'success': success,
            'proper_error': not success and 'required' in stderr.lower(),
            'error': stderr[:200] if stderr else None
        }
        
        if not success and 'required' in stderr.lower():
            self.log("Missing parameters properly detected", "SUCCESS")
    
    def test_help_and_version(self):
        """Test help and version commands"""
        self.log("Testing Help and Version Commands", "INFO")
        
        # Test main help
        success, stdout, stderr = self.run_command("--help")
        self.results['edge_cases']['help'] = {
            'success': success,
            'has_usage': 'usage:' in stdout.lower(),
            'has_commands': 'discover' in stdout and 'info' in stdout
        }
        
        # Test version
        success, stdout, stderr = self.run_command("--version")
        self.results['edge_cases']['version'] = {
            'success': success,
            'output': stdout
        }
    
    def generate_report(self):
        """Generate a comprehensive test report"""
        self.log("Generating Test Report", "INFO")
        
        total_tests = 0
        passed_tests = 0
        failed_tests = 0
        warnings = 0
        
        print("\n" + "="*80)
        print(" "*25 + "UPNP-CLI COMPREHENSIVE TEST REPORT")
        print("="*80)
        print(f"Test Duration: {datetime.now() - self.start_time}")
        print(f"Test Device: {self.test_host}:{self.test_port}" if self.test_host else "No test device found")
        print("="*80)
        
        for category, tests in self.results.items():
            print(f"\n📋 {category.upper().replace('_', ' ')}")
            print("-" * 40)
            
            for test_name, result in tests.items():
                total_tests += 1
                
                if isinstance(result, dict) and 'success' in result:
                    # For edge cases, check if failure is expected and proper
                    if category == 'edge_cases' and result['success'] is False:
                        if result.get('proper_error', False):
                            print(f"  ✅ {test_name}")
                            passed_tests += 1
                        else:
                            print(f"  ❌ {test_name}")
                            if result.get('error'):
                                print(f"      Error: {result['error'][:100]}...")
                            failed_tests += 1
                    elif result['success'] is True:
                        print(f"  ✅ {test_name}")
                        passed_tests += 1
                    elif result['success'] is False:
                        print(f"  ❌ {test_name}")
                        if result.get('error'):
                            print(f"      Error: {result['error'][:100]}...")
                        failed_tests += 1
                    else:  # None or skipped
                        print(f"  ⚠️  {test_name} (skipped)")
                        warnings += 1
                else:
                    print(f"  ℹ️  {test_name}: {result}")
        
        print("\n" + "="*80)
        print(" "*30 + "SUMMARY")
        print("="*80)
        print(f"Total Tests:    {total_tests}")
        print(f"✅ Passed:      {passed_tests}")
        print(f"❌ Failed:      {failed_tests}")
        print(f"⚠️ Warnings:    {warnings}")
        print(f"Success Rate:   {(passed_tests/total_tests*100):.1f}%" if total_tests > 0 else "N/A")
        
        # Critical Issues
        critical_issues = []
        
        # Check for critical failures
        if not self.results['discovery']['basic_discover']['success']:
            critical_issues.append("❗ Basic discovery is failing - core functionality broken")
            
        if self.test_host and not self.results['device_control']['info']['success']:
            critical_issues.append("❗ Device info retrieval is failing")
            
        media_failures = sum(1 for cmd, result in self.results['media_control'].items() 
                           if isinstance(result, dict) and result.get('success') is False)
        if media_failures > len(self.results['media_control']) / 2:
            critical_issues.append(f"❗ Most media control commands failing ({media_failures} failures)")
            
        if critical_issues:
            print(f"\n🚨 CRITICAL ISSUES:")
            for issue in critical_issues:
                print(f"   {issue}")
        
        # Recommendations
        print(f"\n💡 RECOMMENDATIONS:")
        
        if failed_tests > 0:
            print("   • Focus on fixing failed tests first")
            
        if not self.test_host:
            print("   • Ensure at least one UPnP device is available for testing")
            
        if any('timeout' in str(result.get('error', '')) for tests in self.results.values() 
               for result in tests.values() if isinstance(result, dict)):
            print("   • Some commands are timing out - check network connectivity")
            
        if any("'dict' object has no attribute 'status_code'" in str(result.get('error', '')) 
               for tests in self.results.values() for result in tests.values() if isinstance(result, dict)):
            print("   • SOAP response handling bug detected - fix media control response parsing")
            
        print("\n" + "="*80)
    
    def run_all_tests(self):
        """Run the complete test suite"""
        self.log("Starting Comprehensive UPnP CLI Test Suite", "INFO")
        
        try:
            self.test_help_and_version()
            self.test_discovery_commands()
            self.test_device_info_commands()
            self.test_media_control_commands()
            self.test_security_scanning()
            self.test_server_management()
            self.test_cache_management()
            self.test_routines()
            self.test_mass_operations()
            self.test_edge_cases()
            
            self.generate_report()
            
        except KeyboardInterrupt:
            self.log("Test suite interrupted by user", "WARNING")
            self.generate_report()
        except Exception as e:
            self.log(f"Test suite failed with exception: {e}", "FAILURE")
            self.generate_report()

def main():
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help']:
        print("UPnP CLI Comprehensive Test Suite")
        print("Usage: python3 test_upnp_cli_comprehensive.py")
        print("This script tests all upnp-cli functionality and reports detailed results.")
        return
        
    tester = UPnPCLITester()
    tester.run_all_tests()

if __name__ == "__main__":
    main() 