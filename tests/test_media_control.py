"""
Tests for media control module.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import aiohttp

from upnp_cli.media_control import (
    MediaController, MediaControlError, get_media_controller,
    play_media, pause_media, stop_media, set_media_uri, set_volume, get_volume
)


class TestMediaController:
    """Test MediaController class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.controller = MediaController()
    
    @pytest.mark.asyncio
    async def test_controller_initialization(self):
        """Test media controller initialization."""
        assert self.controller.soap_client is not None
        assert self.controller.stealth_mode is False
        
        stealth_controller = MediaController(stealth_mode=True)
        assert stealth_controller.stealth_mode is True
    
    @pytest.mark.asyncio
    @patch('upnp_cli.media_control.get_device_control_info')
    @patch('aiohttp.ClientSession')
    async def test_upnp_play_success(self, mock_session, mock_control_info):
        """Test successful UPnP play operation."""
        # Setup mocks
        mock_control_info.return_value = {
            'protocol': 'upnp',
            'avtransport_url': '/MediaRenderer/AVTransport/Control'
        }
        
        mock_response = AsyncMock()
        mock_response.status = 200
        
        with patch.object(self.controller.soap_client, 'send_soap_request_async', return_value=mock_response):
            result = await self.controller.play('192.168.1.100', 1400)
        
        assert result['status'] == 'success'
        assert result['action'] == 'play'
        assert result['protocol'] == 'upnp'
    
    @pytest.mark.asyncio
    @patch('upnp_cli.media_control.get_device_control_info')
    @patch('aiohttp.ClientSession')
    async def test_upnp_play_failure(self, mock_session, mock_control_info):
        """Test failed UPnP play operation."""
        mock_control_info.return_value = {
            'protocol': 'upnp',
            'avtransport_url': '/MediaRenderer/AVTransport/Control'
        }
        
        mock_response = AsyncMock()
        mock_response.status = 500
        
        with patch.object(self.controller.soap_client, 'send_soap_request_async', return_value=mock_response):
            with pytest.raises(MediaControlError, match="UPnP Play failed"):
                await self.controller.play('192.168.1.100', 1400)
    
    @pytest.mark.asyncio
    @patch('upnp_cli.media_control.get_device_control_info')
    @patch('upnp_cli.media_control.MediaController._ecp_play')
    async def test_ecp_play_success(self, mock_ecp_play, mock_control_info):
        """Test successful ECP play operation."""
        mock_control_info.return_value = {'protocol': 'ecp'}
        mock_ecp_play.return_value = {
            'status': 'success',
            'action': 'play',
            'protocol': 'ecp'
        }
        
        result = await self.controller.play('192.168.1.100', 8060)
        
        assert result['status'] == 'success'
        assert result['action'] == 'play'
        assert result['protocol'] == 'ecp'
        mock_ecp_play.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('upnp_cli.media_control.get_device_control_info')
    async def test_samsung_wam_play(self, mock_control_info):
        """Test Samsung WAM play operation."""
        mock_control_info.return_value = {'protocol': 'samsung_wam'}
        
        result = await self.controller.play('192.168.1.100', 55001)
        
        assert result['status'] == 'success'
        assert result['action'] == 'play'
        assert result['protocol'] == 'samsung_wam'
        assert 'note' in result
    
    @pytest.mark.asyncio
    @patch('upnp_cli.media_control.get_device_control_info')
    async def test_cast_play_not_implemented(self, mock_control_info):
        """Test Cast play operation (not implemented)."""
        mock_control_info.return_value = {'protocol': 'cast'}
        
        result = await self.controller.play('192.168.1.100', 8008)
        
        assert result['status'] == 'not_implemented'
        assert result['protocol'] == 'cast'
        assert 'WebSocket' in result['note']
    
    @pytest.mark.asyncio
    @patch('upnp_cli.media_control.get_device_control_info')
    @patch('aiohttp.ClientSession')
    async def test_pause_operation(self, mock_session, mock_control_info):
        """Test pause operation."""
        mock_control_info.return_value = {
            'protocol': 'upnp',
            'avtransport_url': '/MediaRenderer/AVTransport/Control'
        }
        
        mock_response = AsyncMock()
        mock_response.status = 200
        
        with patch.object(self.controller.soap_client, 'send_soap_request_async', return_value=mock_response):
            result = await self.controller.pause('192.168.1.100', 1400)
        
        assert result['status'] == 'success'
        assert result['action'] == 'pause'
        assert result['protocol'] == 'upnp'
    
    @pytest.mark.asyncio
    @patch('upnp_cli.media_control.get_device_control_info')
    @patch('aiohttp.ClientSession')
    async def test_stop_operation(self, mock_session, mock_control_info):
        """Test stop operation."""
        mock_control_info.return_value = {
            'protocol': 'upnp',
            'avtransport_url': '/MediaRenderer/AVTransport/Control'
        }
        
        mock_response = AsyncMock()
        mock_response.status = 200
        
        with patch.object(self.controller.soap_client, 'send_soap_request_async', return_value=mock_response):
            result = await self.controller.stop('192.168.1.100', 1400)
        
        assert result['status'] == 'success'
        assert result['action'] == 'stop'
        assert result['protocol'] == 'upnp'
    
    @pytest.mark.asyncio
    @patch('upnp_cli.media_control.get_device_control_info')
    @patch('aiohttp.ClientSession')
    async def test_set_uri_with_metadata(self, mock_session, mock_control_info):
        """Test set URI operation with custom metadata."""
        mock_control_info.return_value = {
            'protocol': 'upnp',
            'avtransport_url': '/MediaRenderer/AVTransport/Control'
        }
        
        mock_response = AsyncMock()
        mock_response.status = 200
        
        test_uri = 'http://example.com/audio.mp3'
        test_metadata = '<DIDL-Lite>custom metadata</DIDL-Lite>'
        
        with patch.object(self.controller.soap_client, 'send_soap_request_async', return_value=mock_response) as mock_soap:
            result = await self.controller.set_uri('192.168.1.100', 1400, test_uri, test_metadata)
        
        # Verify SOAP call was made with correct parameters
        mock_soap.assert_called_once()
        call_args, call_kwargs = mock_soap.call_args
        # Arguments are passed positionally as the 7th parameter (index 6)
        if len(call_args) > 6:
            arguments = call_args[6]
            assert arguments['CurrentURI'] == test_uri
            assert arguments['CurrentURIMetaData'] == test_metadata
        elif 'arguments' in call_kwargs:
            assert call_kwargs['arguments']['CurrentURI'] == test_uri
            assert call_kwargs['arguments']['CurrentURIMetaData'] == test_metadata
        
        assert result['status'] == 'success'
        assert result['action'] == 'set_uri'
        assert result['uri'] == test_uri
    
    @pytest.mark.asyncio
    @patch('upnp_cli.media_control.get_device_control_info')
    @patch('aiohttp.ClientSession')
    async def test_set_uri_without_metadata(self, mock_session, mock_control_info):
        """Test set URI operation without metadata (should create default)."""
        mock_control_info.return_value = {
            'protocol': 'upnp',
            'avtransport_url': '/MediaRenderer/AVTransport/Control'
        }
        
        mock_response = AsyncMock()
        mock_response.status = 200
        
        test_uri = 'http://example.com/audio.mp3'
        
        with patch.object(self.controller.soap_client, 'send_soap_request_async', return_value=mock_response) as mock_soap:
            result = await self.controller.set_uri('192.168.1.100', 1400, test_uri)
        
        # Verify SOAP call was made with generated metadata
        mock_soap.assert_called_once()
        call_args, call_kwargs = mock_soap.call_args
        # Arguments are passed positionally as the 7th parameter (index 6)
        if len(call_args) > 6:
            arguments = call_args[6]
            assert arguments['CurrentURI'] == test_uri
            assert 'DIDL-Lite' in arguments['CurrentURIMetaData']
        elif 'arguments' in call_kwargs:
            assert call_kwargs['arguments']['CurrentURI'] == test_uri
            assert 'DIDL-Lite' in call_kwargs['arguments']['CurrentURIMetaData']
        
        assert result['status'] == 'success'
    
    @pytest.mark.asyncio
    @patch('upnp_cli.media_control.get_device_control_info')
    @patch('upnp_cli.media_control.MediaController._ecp_set_uri')
    async def test_ecp_set_uri(self, mock_ecp_set_uri, mock_control_info):
        """Test ECP set URI operation."""
        mock_control_info.return_value = {'protocol': 'ecp'}
        
        test_uri = 'http://example.com/audio.mp3'
        mock_ecp_set_uri.return_value = {
            'status': 'success',
            'action': 'set_uri',
            'uri': test_uri,
            'protocol': 'ecp'
        }
        
        result = await self.controller.set_uri('192.168.1.100', 8060, test_uri)
        
        assert result['status'] == 'success'
        assert result['action'] == 'set_uri'
        assert result['uri'] == test_uri
        assert result['protocol'] == 'ecp'
        mock_ecp_set_uri.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('upnp_cli.media_control.get_device_control_info')
    @patch('upnp_cli.media_control.MediaController._samsung_wam_set_uri')
    async def test_samsung_wam_set_uri(self, mock_samsung_wam_set_uri, mock_control_info):
        """Test Samsung WAM set URI operation."""
        mock_control_info.return_value = {'protocol': 'samsung_wam'}
        
        test_uri = 'http://example.com/audio.mp3'
        mock_samsung_wam_set_uri.return_value = {
            'status': 'success',
            'protocol': 'samsung_wam',
            'response': '<response>success</response>'
        }
        
        result = await self.controller.set_uri('192.168.1.100', 55001, test_uri)
        
        assert result['status'] == 'success'
        assert result['protocol'] == 'samsung_wam'
        mock_samsung_wam_set_uri.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('upnp_cli.media_control.get_device_control_info')
    @patch('aiohttp.ClientSession')
    async def test_get_volume_success(self, mock_session, mock_control_info):
        """Test successful get volume operation."""
        mock_control_info.return_value = {
            'protocol': 'upnp',
            'rendering_url': '/MediaRenderer/RenderingControl/Control'
        }
        
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text.return_value = '<CurrentVolume>75</CurrentVolume>'
        
        with patch.object(self.controller.soap_client, 'send_soap_request_async', return_value=mock_response):
            result = await self.controller.get_volume('192.168.1.100', 1400)
        
        assert result['status'] == 'success'
        assert result['volume'] == 75
        assert result['protocol'] == 'upnp'
    
    @pytest.mark.asyncio
    @patch('upnp_cli.media_control.get_device_control_info')
    @patch('aiohttp.ClientSession')
    async def test_set_volume_success(self, mock_session, mock_control_info):
        """Test successful set volume operation."""
        mock_control_info.return_value = {
            'protocol': 'upnp',
            'rendering_url': '/MediaRenderer/RenderingControl/Control'
        }
        
        mock_response = AsyncMock()
        mock_response.status = 200
        
        with patch.object(self.controller.soap_client, 'send_soap_request_async', return_value=mock_response):
            result = await self.controller.set_volume('192.168.1.100', 1400, 80)
        
        assert result['status'] == 'success'
        assert result['action'] == 'set_volume'
        assert result['volume'] == 80
        assert result['protocol'] == 'upnp'
    
    @pytest.mark.asyncio
    async def test_set_volume_invalid_level(self):
        """Test set volume with invalid level."""
        with pytest.raises(MediaControlError, match="Volume level must be 0-100"):
            await self.controller.set_volume('192.168.1.100', 1400, 150)
        
        with pytest.raises(MediaControlError, match="Volume level must be 0-100"):
            await self.controller.set_volume('192.168.1.100', 1400, -10)
    
    @pytest.mark.asyncio
    @patch('upnp_cli.media_control.get_device_control_info')
    @patch('aiohttp.ClientSession')
    async def test_get_mute_success(self, mock_session, mock_control_info):
        """Test successful get mute operation."""
        mock_control_info.return_value = {
            'protocol': 'upnp',
            'rendering_url': '/MediaRenderer/RenderingControl/Control'
        }
        
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text.return_value = '<CurrentMute>1</CurrentMute>'
        
        with patch.object(self.controller.soap_client, 'send_soap_request_async', return_value=mock_response):
            result = await self.controller.get_mute('192.168.1.100', 1400)
        
        assert result['status'] == 'success'
        assert result['muted'] is True
        assert result['protocol'] == 'upnp'
    
    @pytest.mark.asyncio
    @patch('upnp_cli.media_control.get_device_control_info')
    @patch('aiohttp.ClientSession')
    async def test_set_mute_success(self, mock_session, mock_control_info):
        """Test successful set mute operation."""
        mock_control_info.return_value = {
            'protocol': 'upnp',
            'rendering_url': '/MediaRenderer/RenderingControl/Control'
        }
        
        mock_response = AsyncMock()
        mock_response.status = 200
        
        with patch.object(self.controller.soap_client, 'send_soap_request_async', return_value=mock_response):
            result = await self.controller.set_mute('192.168.1.100', 1400, True)
        
        assert result['status'] == 'success'
        assert result['action'] == 'set_mute'
        assert result['muted'] is True
        assert result['protocol'] == 'upnp'
    
    @pytest.mark.asyncio
    @patch('upnp_cli.media_control.get_device_control_info')
    @patch('aiohttp.ClientSession')
    async def test_seek_operation(self, mock_session, mock_control_info):
        """Test seek operation."""
        mock_control_info.return_value = {
            'protocol': 'upnp',
            'avtransport_url': '/MediaRenderer/AVTransport/Control'
        }
        
        mock_response = AsyncMock()
        mock_response.status = 200
        
        with patch.object(self.controller.soap_client, 'send_soap_request_async', return_value=mock_response) as mock_soap:
            # Test with seconds
            result = await self.controller.seek('192.168.1.100', 1400, '120')
        
        # Verify position was converted to HH:MM:SS format
        mock_soap.assert_called_once()
        call_args, call_kwargs = mock_soap.call_args
        # Arguments are passed positionally as the 7th parameter (index 6)
        if len(call_args) > 6:
            arguments = call_args[6]
            assert arguments['Target'] == '00:02:00'
        elif 'arguments' in call_kwargs:
            assert call_kwargs['arguments']['Target'] == '00:02:00'
        
        assert result['status'] == 'success'
        assert result['action'] == 'seek'
        assert result['position'] == '00:02:00'
    
    @pytest.mark.asyncio
    @patch('upnp_cli.media_control.get_device_control_info')
    @patch('aiohttp.ClientSession')
    async def test_seek_with_time_format(self, mock_session, mock_control_info):
        """Test seek operation with HH:MM:SS format."""
        mock_control_info.return_value = {
            'protocol': 'upnp',
            'avtransport_url': '/MediaRenderer/AVTransport/Control'
        }
        
        mock_response = AsyncMock()
        mock_response.status = 200
        
        with patch.object(self.controller.soap_client, 'send_soap_request_async', return_value=mock_response) as mock_soap:
            result = await self.controller.seek('192.168.1.100', 1400, '01:23:45')
        
        # Verify position was passed through unchanged
        mock_soap.assert_called_once()
        call_args, call_kwargs = mock_soap.call_args
        # Arguments are passed positionally as the 7th parameter (index 6)
        if len(call_args) > 6:
            arguments = call_args[6]
            assert arguments['Target'] == '01:23:45'
        elif 'arguments' in call_kwargs:
            assert call_kwargs['arguments']['Target'] == '01:23:45'
        
        assert result['position'] == '01:23:45'
    
    @pytest.mark.asyncio
    @patch('upnp_cli.media_control.get_device_control_info')
    async def test_next_track_not_supported(self, mock_control_info):
        """Test next track on non-UPnP protocol."""
        mock_control_info.return_value = {'protocol': 'ecp'}
        
        result = await self.controller.next_track('192.168.1.100', 8060)
        
        assert result['status'] == 'not_supported'
        assert result['protocol'] == 'ecp'
    
    @pytest.mark.asyncio
    @patch('upnp_cli.media_control.get_device_control_info')
    async def test_volume_not_supported(self, mock_control_info):
        """Test volume operations on non-supporting protocol."""
        mock_control_info.return_value = {'protocol': 'ecp'}
        
        result = await self.controller.get_volume('192.168.1.100', 8060)
        assert result['status'] == 'not_supported'
        
        result = await self.controller.set_volume('192.168.1.100', 8060, 50)
        assert result['status'] == 'not_supported'
    
    def test_create_didl_metadata(self):
        """Test DIDL metadata creation."""
        uri = 'http://example.com/audio.mp3'
        metadata = self.controller._create_didl_metadata(uri)
        
        assert 'DIDL-Lite' in metadata
        assert uri in metadata
        assert 'Audio Stream' in metadata
        assert 'audioItem.musicTrack' in metadata
    
    def test_parse_soap_response_value(self):
        """Test SOAP response value parsing."""
        xml_response = '''
        <s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
            <s:Body>
                <GetVolumeResponse>
                    <CurrentVolume>85</CurrentVolume>
                </GetVolumeResponse>
            </s:Body>
        </s:Envelope>
        '''
        
        volume = self.controller._parse_soap_response_value(xml_response, 'CurrentVolume')
        assert volume == '85'
        
        # Test with non-existent tag
        invalid = self.controller._parse_soap_response_value(xml_response, 'NonExistent')
        assert invalid is None
        
        # Test with invalid XML
        invalid_xml = self.controller._parse_soap_response_value('invalid xml', 'CurrentVolume')
        assert invalid_xml is None


class TestGlobalFunctions:
    """Test global convenience functions."""
    
    @pytest.mark.asyncio
    @patch('upnp_cli.media_control.MediaController')
    async def test_get_media_controller_singleton(self, mock_controller_class):
        """Test global media controller singleton."""
        mock_instance = Mock()
        mock_controller_class.return_value = mock_instance
        
        # Reset global instance
        import upnp_cli.media_control
        upnp_cli.media_control._media_controller = None
        
        controller1 = get_media_controller()
        controller2 = get_media_controller()
        
        assert controller1 is controller2
        mock_controller_class.assert_called_once_with(stealth_mode=False)
    
    @pytest.mark.asyncio
    @patch('upnp_cli.media_control.get_media_controller')
    async def test_convenience_functions(self, mock_get_controller):
        """Test convenience functions."""
        mock_controller = AsyncMock()
        mock_get_controller.return_value = mock_controller
        
        # Test play_media
        mock_controller.play.return_value = {'status': 'success'}
        result = await play_media('192.168.1.100')
        mock_controller.play.assert_called_once_with('192.168.1.100', 1400, None)
        assert result['status'] == 'success'
        
        # Test pause_media
        mock_controller.pause.return_value = {'status': 'success'}
        result = await pause_media('192.168.1.100', port=8060)
        mock_controller.pause.assert_called_once_with('192.168.1.100', 8060, None)
        
        # Test stop_media
        mock_controller.stop.return_value = {'status': 'success'}
        result = await stop_media('192.168.1.100')
        mock_controller.stop.assert_called_once_with('192.168.1.100', 1400, None)
        
        # Test set_media_uri
        test_uri = 'http://example.com/audio.mp3'
        mock_controller.set_uri.return_value = {'status': 'success'}
        result = await set_media_uri('192.168.1.100', test_uri, metadata='custom')
        mock_controller.set_uri.assert_called_once_with('192.168.1.100', 1400, test_uri, 'custom', None)
        
        # Test set_volume
        mock_controller.set_volume.return_value = {'status': 'success'}
        result = await set_volume('192.168.1.100', 75)
        mock_controller.set_volume.assert_called_once_with('192.168.1.100', 1400, 75, None)
        
        # Test get_volume
        mock_controller.get_volume.return_value = {'status': 'success', 'volume': 50}
        result = await get_volume('192.168.1.100')
        mock_controller.get_volume.assert_called_once_with('192.168.1.100', 1400, None)


class TestMediaControlError:
    """Test MediaControlError exception."""
    
    def test_media_control_error_creation(self):
        """Test MediaControlError creation with different parameters."""
        # Basic error
        error = MediaControlError("Test error")
        assert str(error) == "Test error"
        assert error.error_code is None
        assert error.device_info is None
        
        # Error with code
        error = MediaControlError("Test error", error_code=500)
        assert error.error_code == 500
        
        # Error with device info
        device_info = {'host': '192.168.1.100', 'port': 1400}
        error = MediaControlError("Test error", device_info=device_info)
        assert error.device_info == device_info