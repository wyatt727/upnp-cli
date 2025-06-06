"""
Cache management for UPnP CLI.

This module provides persistent device caching using SQLite to avoid
repeated network scanning and improve performance.
"""

import sqlite3
import json
import time
import gzip
from pathlib import Path
from typing import Optional, Dict, Any, List
from contextlib import contextmanager

from . import config
from .logging_utils import get_logger

logger = get_logger(__name__)


class DeviceCache:
    """
    SQLite-based cache for discovered UPnP devices.
    
    Stores device information, last seen timestamps, and control URLs
    with automatic TTL-based invalidation.
    """
    
    def __init__(self, cache_path: Optional[Path] = None):
        """
        Initialize device cache.
        
        Args:
            cache_path: Custom cache file path (optional)
        """
        self.cache_path = cache_path or config.get_cache_path()
        self.ttl_hours = config.CACHE_TTL_HOURS
        self.max_entries = config.CACHE_MAX_ENTRIES
        
        # Ensure cache directory exists
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self._init_database()
        
        logger.debug(f"Initialized device cache at {self.cache_path}")
    
    def _init_database(self) -> None:
        """Initialize the SQLite database with required tables."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Create devices table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS devices (
                    ip TEXT PRIMARY KEY,
                    port INTEGER NOT NULL,
                    last_seen REAL NOT NULL,
                    device_data TEXT NOT NULL,
                    compressed INTEGER DEFAULT 0
                )
            ''')
            
            # Create cache metadata table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS cache_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated REAL NOT NULL
                )
            ''')
            
            # Create indexes for performance
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_last_seen 
                ON devices(last_seen)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_port 
                ON devices(port)
            ''')
            
            conn.commit()
            logger.debug("Database tables initialized")
    
    @contextmanager
    def _get_connection(self):
        """Get a database connection with proper error handling."""
        conn = None
        try:
            conn = sqlite3.connect(self.cache_path, timeout=30.0)
            conn.row_factory = sqlite3.Row  # Enable column access by name
            yield conn
        except sqlite3.Error as e:
            logger.error(f"Database error: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()
    
    def _compress_data(self, data: str) -> bytes:
        """Compress device data if it's large."""
        data_bytes = data.encode('utf-8')
        if len(data_bytes) > 1024:  # Compress if larger than 1KB
            return gzip.compress(data_bytes)
        return data_bytes
    
    def _decompress_data(self, data: bytes, compressed: bool) -> str:
        """Decompress device data if it was compressed."""
        if compressed:
            return gzip.decompress(data).decode('utf-8')
        return data.decode('utf-8')
    
    def upsert(self, ip: str, port: int, device_info: Dict[str, Any]) -> None:
        """
        Insert or update device information in cache.
        
        Args:
            ip: Device IP address
            port: Device port
            device_info: Device information dictionary
        """
        try:
            # Serialize device data
            data_json = json.dumps(device_info, sort_keys=True)
            data_bytes = self._compress_data(data_json)
            compressed = len(data_bytes) < len(data_json.encode('utf-8'))
            
            timestamp = time.time()
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO devices 
                    (ip, port, last_seen, device_data, compressed)
                    VALUES (?, ?, ?, ?, ?)
                ''', (ip, port, timestamp, data_bytes, int(compressed)))
                
                conn.commit()
                
            logger.debug(f"Cached device {ip}:{port} ({len(data_json)} bytes, compressed: {compressed})")
            
        except Exception as e:
            logger.error(f"Failed to cache device {ip}:{port}: {e}")
    
    def get(self, ip: str) -> Optional[Dict[str, Any]]:
        """
        Get cached device information by IP address.
        
        Args:
            ip: Device IP address
            
        Returns:
            Device information dictionary or None if not found/expired
        """
        try:
            cutoff_time = time.time() - (self.ttl_hours * 3600)
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT port, last_seen, device_data, compressed
                    FROM devices 
                    WHERE ip = ? AND last_seen >= ?
                ''', (ip, cutoff_time))
                
                row = cursor.fetchone()
                
            if not row:
                return None
            
            # Decompress and parse device data
            device_data = self._decompress_data(row['device_data'], bool(row['compressed']))
            device_info = json.loads(device_data)
            
            return {
                'ip': ip,
                'port': row['port'],
                'last_seen': row['last_seen'],
                'info': device_info
            }
            
        except Exception as e:
            logger.error(f"Failed to get cached device {ip}: {e}")
            return None
    
    def list(self, max_age_hours: Optional[float] = None) -> List[Dict[str, Any]]:
        """
        List all cached devices within the specified age.
        
        Args:
            max_age_hours: Maximum age in hours (defaults to TTL)
            
        Returns:
            List of device information dictionaries
        """
        try:
            max_age = max_age_hours or self.ttl_hours
            cutoff_time = time.time() - (max_age * 3600)
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT ip, port, last_seen, device_data, compressed
                    FROM devices 
                    WHERE last_seen >= ?
                    ORDER BY last_seen DESC
                ''', (cutoff_time,))
                
                rows = cursor.fetchall()
            
            devices = []
            for row in rows:
                try:
                    device_data = self._decompress_data(row['device_data'], bool(row['compressed']))
                    device_info = json.loads(device_data)
                    
                    devices.append({
                        'ip': row['ip'],
                        'port': row['port'],
                        'last_seen': row['last_seen'],
                        'info': device_info
                    })
                except Exception as e:
                    logger.warning(f"Failed to parse cached device {row['ip']}: {e}")
                    continue
            
            logger.debug(f"Retrieved {len(devices)} cached devices")
            return devices
            
        except Exception as e:
            logger.error(f"Failed to list cached devices: {e}")
            return []
    
    def remove(self, ip: str) -> bool:
        """
        Remove device from cache by IP address.
        
        Args:
            ip: Device IP address
            
        Returns:
            True if device was removed, False if not found
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM devices WHERE ip = ?', (ip,))
                removed = cursor.rowcount > 0
                conn.commit()
                
            if removed:
                logger.debug(f"Removed device {ip} from cache")
            
            return removed
            
        except Exception as e:
            logger.error(f"Failed to remove device {ip} from cache: {e}")
            return False
    
    def cleanup_expired(self) -> int:
        """
        Remove expired entries from cache.
        
        Returns:
            Number of entries removed
        """
        try:
            cutoff_time = time.time() - (self.ttl_hours * 3600)
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM devices WHERE last_seen < ?', (cutoff_time,))
                removed_count = cursor.rowcount
                conn.commit()
                
            if removed_count > 0:
                logger.info(f"Cleaned up {removed_count} expired cache entries")
            
            return removed_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired entries: {e}")
            return 0
    
    def clear(self) -> None:
        """Clear all cached devices."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM devices')
                cursor.execute('DELETE FROM cache_metadata')
                conn.commit()
                
            logger.info("Cleared all cached devices")
            
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
    
    def stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        try:
            current_time = time.time()
            cutoff_time = current_time - (self.ttl_hours * 3600)
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Total entries
                cursor.execute('SELECT COUNT(*) FROM devices')
                total_entries = cursor.fetchone()[0]
                
                # Valid entries (not expired)
                cursor.execute('SELECT COUNT(*) FROM devices WHERE last_seen >= ?', (cutoff_time,))
                valid_entries = cursor.fetchone()[0]
                
                # Expired entries
                expired_entries = total_entries - valid_entries
                
                # Database file size
                file_size = self.cache_path.stat().st_size if self.cache_path.exists() else 0
                
                # Compressed entries
                cursor.execute('SELECT COUNT(*) FROM devices WHERE compressed = 1')
                compressed_entries = cursor.fetchone()[0]
                
            return {
                'total_entries': total_entries,
                'valid_entries': valid_entries,
                'expired_entries': expired_entries,
                'file_size_bytes': file_size,
                'file_size_mb': round(file_size / 1024 / 1024, 2),
                'compressed_entries': compressed_entries,
                'cache_path': str(self.cache_path),
                'ttl_hours': self.ttl_hours,
                'max_entries': self.max_entries
            }
            
        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {}
    
    def set_metadata(self, key: str, value: str) -> None:
        """Set cache metadata key-value pair."""
        try:
            timestamp = time.time()
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO cache_metadata (key, value, updated)
                    VALUES (?, ?, ?)
                ''', (key, value, timestamp))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to set metadata {key}: {e}")
    
    def get_metadata(self, key: str) -> Optional[str]:
        """Get cache metadata value by key."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT value FROM cache_metadata WHERE key = ?', (key,))
                row = cursor.fetchone()
                return row[0] if row else None
        except Exception as e:
            logger.error(f"Failed to get metadata {key}: {e}")
            return None


# Global cache instance
_cache_instance: Optional[DeviceCache] = None


def get_cache() -> DeviceCache:
    """Get the global cache instance (singleton pattern)."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = DeviceCache()
    return _cache_instance


def invalidate_cache() -> None:
    """Invalidate the global cache instance."""
    global _cache_instance
    if _cache_instance is not None:
        _cache_instance.clear()
        _cache_instance = None 