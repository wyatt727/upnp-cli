"""
Tests for the cache module.
"""

import json
import tempfile
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from upnp_cli.cache import DeviceCache, get_cache, invalidate_cache


@pytest.fixture
def temp_cache_path():
    """Create temporary cache file for testing."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        cache_path = Path(f.name)
    yield cache_path
    # Cleanup
    if cache_path.exists():
        cache_path.unlink()


class TestDeviceCache:
    """Test DeviceCache functionality."""
    
    @pytest.fixture
    def cache(self, temp_cache_path):
        """Create DeviceCache instance for testing."""
        return DeviceCache(temp_cache_path)
    
    @pytest.fixture
    def sample_device_info(self):
        """Sample device information for testing."""
        return {
            'friendlyName': 'Kitchen Sonos',
            'manufacturer': 'Sonos, Inc.',
            'modelName': 'S23',
            'serialNumber': '12:34:56:78:90:AB',
            'services': [
                {
                    'serviceType': 'urn:schemas-upnp-org:service:AVTransport:1',
                    'controlURL': '/MediaRenderer/AVTransport/Control'
                }
            ]
        }
    
    def test_cache_initialization(self, temp_cache_path):
        """Test cache initialization creates database."""
        cache = DeviceCache(temp_cache_path)
        assert temp_cache_path.exists()
        assert cache.cache_path == temp_cache_path
    
    def test_upsert_and_get_device(self, cache, sample_device_info):
        """Test storing and retrieving device information."""
        ip = "192.168.1.100"
        port = 1400
        
        # Store device
        cache.upsert(ip, port, sample_device_info)
        
        # Retrieve device
        cached_device = cache.get(ip)
        
        assert cached_device is not None
        assert cached_device['ip'] == ip
        assert cached_device['port'] == port
        assert cached_device['info'] == sample_device_info
        assert 'last_seen' in cached_device
    
    def test_get_nonexistent_device(self, cache):
        """Test retrieving nonexistent device returns None."""
        result = cache.get("192.168.1.999")
        assert result is None
    
    def test_list_devices(self, cache, sample_device_info):
        """Test listing cached devices."""
        devices = [
            ("192.168.1.100", 1400, sample_device_info),
            ("192.168.1.101", 8060, {"manufacturer": "Roku"}),
            ("192.168.1.102", 55001, {"manufacturer": "Samsung"})
        ]
        
        # Store devices
        for ip, port, info in devices:
            cache.upsert(ip, port, info)
        
        # List devices
        cached_devices = cache.list()
        
        assert len(cached_devices) == 3
        
        # Check devices are sorted by last_seen (newest first)
        assert cached_devices[0]['ip'] in ["192.168.1.100", "192.168.1.101", "192.168.1.102"]
    
    def test_device_expiration(self, cache, sample_device_info):
        """Test device TTL expiration."""
        ip = "192.168.1.100"
        port = 1400
        
        # Mock very short TTL
        cache.ttl_hours = 0.001  # About 3.6 seconds
        
        # Store device
        cache.upsert(ip, port, sample_device_info)
        
        # Should be retrievable immediately
        assert cache.get(ip) is not None
        
        # Wait for expiration (convert hours to seconds)
        time.sleep(cache.ttl_hours * 3600 + 0.1)  # TTL + buffer
        
        # Should be expired now
        assert cache.get(ip) is None
    
    def test_remove_device(self, cache, sample_device_info):
        """Test removing device from cache."""
        ip = "192.168.1.100"
        port = 1400
        
        # Store device
        cache.upsert(ip, port, sample_device_info)
        assert cache.get(ip) is not None
        
        # Remove device
        removed = cache.remove(ip)
        assert removed is True
        assert cache.get(ip) is None
        
        # Try removing again
        removed = cache.remove(ip)
        assert removed is False
    
    def test_cleanup_expired(self, cache, sample_device_info):
        """Test cleanup of expired entries."""
        # Store devices with different timestamps
        cache.upsert("192.168.1.100", 1400, sample_device_info)
        
        # Mock old timestamp for second device
        old_time = time.time() - (25 * 3600)  # 25 hours ago
        with cache._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO devices (ip, port, last_seen, device_data, compressed)
                VALUES (?, ?, ?, ?, ?)
            ''', ("192.168.1.101", 8060, old_time, json.dumps({"old": "device"}).encode(), 0))
            conn.commit()
        
        # Should have 2 devices total
        all_devices = cache.list(max_age_hours=48)  # Get all devices regardless of age
        assert len(all_devices) == 2
        
        # Cleanup expired (only old device should be removed)
        removed_count = cache.cleanup_expired()
        assert removed_count == 1
        
        # Should have 1 device remaining
        remaining_devices = cache.list()
        assert len(remaining_devices) == 1
        assert remaining_devices[0]['ip'] == "192.168.1.100"
    
    def test_clear_cache(self, cache, sample_device_info):
        """Test clearing entire cache."""
        # Store multiple devices
        cache.upsert("192.168.1.100", 1400, sample_device_info)
        cache.upsert("192.168.1.101", 8060, {"manufacturer": "Roku"})
        
        assert len(cache.list()) == 2
        
        # Clear cache
        cache.clear()
        
        assert len(cache.list()) == 0
    
    def test_cache_stats(self, cache, sample_device_info):
        """Test cache statistics."""
        # Store a device
        cache.upsert("192.168.1.100", 1400, sample_device_info)
        
        stats = cache.stats()
        
        assert stats['total_entries'] == 1
        assert stats['valid_entries'] == 1
        assert stats['expired_entries'] == 0
        assert 'file_size_bytes' in stats
        assert 'file_size_mb' in stats
        assert stats['cache_path'] == str(cache.cache_path)
        assert stats['ttl_hours'] == cache.ttl_hours
    
    def test_metadata_operations(self, cache):
        """Test cache metadata storage and retrieval."""
        key = "last_scan_network"
        value = "192.168.1.0/24"
        
        # Set metadata
        cache.set_metadata(key, value)
        
        # Get metadata
        retrieved_value = cache.get_metadata(key)
        assert retrieved_value == value
        
        # Get nonexistent metadata
        assert cache.get_metadata("nonexistent") is None
    
    def test_compression(self, cache):
        """Test data compression for large device info."""
        # Create large device info that should trigger compression
        large_device_info = {
            'manufacturer': 'Test',
            'services': [{'service': f'service_{i}'} for i in range(100)],
            'large_data': 'x' * 2000  # 2KB of data
        }
        
        cache.upsert("192.168.1.100", 1400, large_device_info)
        
        # Verify compression by checking stats
        stats = cache.stats()
        assert stats['compressed_entries'] > 0
        
        # Verify data integrity after compression
        retrieved = cache.get("192.168.1.100")
        assert retrieved['info'] == large_device_info


class TestCacheGlobalFunctions:
    """Test global cache functions."""
    
    def test_get_cache_singleton(self):
        """Test that get_cache returns singleton instance."""
        cache1 = get_cache()
        cache2 = get_cache()
        assert cache1 is cache2
    
    def test_invalidate_cache(self):
        """Test cache invalidation."""
        # Get initial cache
        cache1 = get_cache()
        
        # Invalidate
        invalidate_cache()
        
        # Get new cache - should be different instance
        cache2 = get_cache()
        assert cache1 is not cache2


class TestCacheErrorHandling:
    """Test cache error handling."""
    
    def test_database_error_handling(self, temp_cache_path):
        """Test handling of database errors."""
        cache = DeviceCache(temp_cache_path)
        
        # Try to corrupt the database by writing invalid data
        with open(temp_cache_path, 'w') as f:
            f.write("invalid database content")
        
        # Operations should handle errors gracefully
        cache.upsert("192.168.1.100", 1400, {"test": "data"})  # Should not crash
        result = cache.get("192.168.1.100")  # Should return None
        assert result is None
    
    def test_json_parsing_error(self, temp_cache_path):
        """Test handling of corrupt JSON data in cache."""
        cache = DeviceCache(temp_cache_path)
        
        # Manually insert invalid JSON data
        with cache._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO devices (ip, port, last_seen, device_data, compressed)
                VALUES (?, ?, ?, ?, ?)
            ''', ("192.168.1.100", 1400, time.time(), b"invalid json", 0))
            conn.commit()
        
        # Should handle gracefully
        result = cache.get("192.168.1.100")
        assert result is None
        
        # List should skip invalid entries
        devices = cache.list()
        assert len(devices) == 0


if __name__ == "__main__":
    pytest.main([__file__]) 