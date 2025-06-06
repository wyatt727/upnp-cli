"""
HTTP server for serving media files.

This module provides a simple HTTP server to serve media files (like fart.mp3)
that can be accessed by UPnP devices for playback.
"""

import http.server
import os
import socketserver
import subprocess
import threading
import time
import signal
import sys
from pathlib import Path
from typing import Dict, Any, Optional

from .logging_utils import get_logger
from .utils import get_local_ip

logger = get_logger(__name__)


def _get_server_pid_file(port: int) -> Path:
    """Get path to PID file for server on given port."""
    return Path.home() / '.upnp_cli' / f'server_{port}.pid'


def _is_server_running(port: int) -> bool:
    """Check if a server is running on the given port."""
    pid_file = _get_server_pid_file(port)
    
    if not pid_file.exists():
        return False
    
    try:
        with open(pid_file, 'r') as f:
            pid = int(f.read().strip())
        
        # Check if process is still running
        os.kill(pid, 0)  # Sends no signal, just checks if process exists
        return True
    except (OSError, ValueError, FileNotFoundError):
        # Process doesn't exist or PID file is invalid, clean it up
        try:
            pid_file.unlink()
        except FileNotFoundError:
            pass
        return False


def _start_server_process(port: int, directory: str) -> subprocess.Popen:
    """Start HTTP server in a separate background process."""
    # Create the command to run a standalone HTTP server
    python_code = f'''
import http.server
import socketserver
import os
import sys
from pathlib import Path

class MediaHTTPHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, directory=None, **kwargs):
        self.directory = directory or os.getcwd()
        super().__init__(*args, directory=self.directory, **kwargs)
    
    def log_message(self, format, *args):
        pass  # Suppress HTTP logs
    
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, HEAD, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        super().end_headers()
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

os.chdir("{directory}")
handler = lambda *args, **kwargs: MediaHTTPHandler(*args, directory="{directory}", **kwargs)
with socketserver.TCPServer(("", {port}), handler) as httpd:
    httpd.allow_reuse_address = True
    print(f"Server started on port {port}")
    httpd.serve_forever()
'''
    
    # Start the server process
    process = subprocess.Popen(
        [sys.executable, '-c', python_code],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True  # Detach from parent process
    )
    
    return process


def start_media_server(port: int = 8080, directory: Optional[str] = None) -> Dict[str, Any]:
    """
    Start a persistent media server that survives CLI exit.
    
    Args:
        port: Port to bind server to
        directory: Directory to serve files from
        
    Returns:
        Server status dictionary
    """
    # Check if server is already running
    if _is_server_running(port):
        return {
            'status': 'already_running',
            'port': port,
            'local_ip': get_local_ip(),
            'message': f'Server already running on port {port}'
        }
    
    # Set up directory
    if directory is None:
        directory = str(Path.cwd())
    else:
        directory = str(Path(directory).resolve())
    
    try:
        # Start server process
        process = _start_server_process(port, directory)
        
        # Wait a moment for the server to start
        time.sleep(1)
        
        # Check if the process is still running
        if process.poll() is None:
            # Save PID
            pid_file = _get_server_pid_file(port)
            pid_file.parent.mkdir(parents=True, exist_ok=True)
            with open(pid_file, 'w') as f:
                f.write(str(process.pid))
            
            # Check for common media files
            media_files = []
            media_extensions = {'.mp3', '.wav', '.m4a', '.flac', '.ogg', '.mp4', '.m4v', '.avi'}
            try:
                for file_path in Path(directory).iterdir():
                    if file_path.is_file() and file_path.suffix.lower() in media_extensions:
                        media_files.append(file_path.name)
            except Exception:
                pass
            
            local_ip = get_local_ip()
            result = {
                'status': 'running',
                'port': port,
                'local_ip': local_ip,
                'directory': directory,
                'base_url': f"http://{local_ip}:{port}",
                'media_files': sorted(media_files),
                'pid': process.pid
            }
            
            # Add specific URLs for common files
            if 'fart.mp3' in media_files:
                result['fart_url'] = f"http://{local_ip}:{port}/fart.mp3"
            
            logger.info(f"HTTP server started on {local_ip}:{port} (PID: {process.pid})")
            return result
        else:
            return {
                'status': 'error',
                'error': 'Server process failed to start',
                'port': port
            }
    
    except Exception as e:
        logger.error(f"Failed to start HTTP server: {e}")
        return {
            'status': 'error',
            'error': str(e),
            'port': port
        }


def stop_media_server(port: int = 8080) -> Dict[str, Any]:
    """
    Stop the persistent media server.
    
    Args:
        port: Port of the server to stop
        
    Returns:
        Stop status dictionary
    """
    pid_file = _get_server_pid_file(port)
    
    if not pid_file.exists():
        return {'status': 'not_running', 'port': port}
    
    try:
        with open(pid_file, 'r') as f:
            pid = int(f.read().strip())
        
        # Try to kill the process
        try:
            os.kill(pid, signal.SIGTERM)
            time.sleep(0.5)  # Give it time to shut down gracefully
            
            # Check if it's still running
            try:
                os.kill(pid, 0)
                # Still running, force kill
                os.kill(pid, signal.SIGKILL)
            except OSError:
                # Process is gone, good
                pass
                
        except OSError:
            # Process doesn't exist
            pass
        
        # Clean up PID file
        try:
            pid_file.unlink()
        except FileNotFoundError:
            pass
        
        logger.info(f"HTTP server stopped (port {port}, PID: {pid})")
        return {'status': 'stopped', 'port': port, 'pid': pid}
        
    except (ValueError, FileNotFoundError) as e:
        logger.error(f"Error stopping server: {e}")
        return {
            'status': 'error',
            'error': str(e),
            'port': port
        }


def get_media_server_status(port: int = 8080) -> Dict[str, Any]:
    """
    Get status of the media server.
    
    Args:
        port: Port to check
        
    Returns:
        Server status dictionary
    """
    if _is_server_running(port):
        pid_file = _get_server_pid_file(port)
        try:
            with open(pid_file, 'r') as f:
                pid = int(f.read().strip())
        except (ValueError, FileNotFoundError):
            pid = None
        
        return {
            'status': 'running',
            'port': port,
            'local_ip': get_local_ip(),
            'pid': pid
        }
    else:
        return {
            'status': 'stopped',
            'port': port
        }


def get_fart_url(port: int = 8080) -> Optional[str]:
    """
    Get URL for fart.mp3 file.
    
    Args:
        port: Port of the server
        
    Returns:
        URL for fart.mp3 or None if server not running or file doesn't exist
    """
    if not _is_server_running(port):
        return None
    
    fart_path = Path.cwd() / "fart.mp3"
    if not fart_path.exists():
        return None
    
    local_ip = get_local_ip()
    return f"http://{local_ip}:{port}/fart.mp3"


# Legacy compatibility - these functions maintain backward compatibility
# but now use the default port argument structure

class MediaHTTPServer:
    """Legacy compatibility class."""
    
    def __init__(self, port: int = 8080, directory: Optional[str] = None):
        self.port = port
        self.directory = directory
    
    def start(self) -> Dict[str, Any]:
        return start_media_server(self.port, self.directory)
    
    def stop(self) -> Dict[str, Any]:
        return stop_media_server(self.port)
    
    def get_status(self) -> Dict[str, Any]:
        return get_media_server_status(self.port)


# Global server instance for backward compatibility
_media_server: Optional[MediaHTTPServer] = None

def get_media_server(port: int = 8080, directory: Optional[str] = None) -> MediaHTTPServer:
    """Get media server instance."""
    global _media_server
    if _media_server is None or _media_server.port != port:
        _media_server = MediaHTTPServer(port, directory)
    return _media_server 