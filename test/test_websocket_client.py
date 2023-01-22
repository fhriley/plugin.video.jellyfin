import datetime
import logging
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import PurePath
from unittest.mock import Mock, PropertyMock, MagicMock, patch
from urllib.parse import urlparse

import requests
import xbmcaddon

from lib.api.jellyfin import User
from lib.service.playback_monitor import PlaybackMonitor
from lib.service.websocket_client import library_changed
from lib.util.settings import Settings
from test.common import get_server, load_data

_addon_id = 'addon'


def get_addon_info(key):
    if key == 'id':
        return _addon_id
    if key == 'version':
        return '1.0.0'
    raise Exception('unknown key: ' + key)


def get_mock_settings(temp_dir: str) -> Settings:
    settings = Mock(Settings)
    type(settings).profile_dir = PropertyMock(return_value=temp_dir)
    return settings


def get_mock_addon() -> xbmcaddon.Addon:
    addon = Mock(xbmcaddon.Addon)
    addon.getAddonInfo = get_addon_info
    return addon


class TestWebsocketClient(unittest.TestCase):
    def setUp(self):
        self.handle = 1
        self.temp_dir = tempfile.TemporaryDirectory()
        self.mock_requests = MagicMock(requests.Session)
        self.settings = get_mock_settings(self.temp_dir.name)
        self.addon = get_mock_addon()
        self.server = get_server(self.mock_requests)
        self.mock_user = MagicMock(User)
        self.log = MagicMock(logging.Logger)
        self.player = MagicMock(PlaybackMonitor)

    def tearDown(self):
        self.temp_dir.cleanup()

    @patch('lib.service.websocket_client.scan_kodi')
    @patch('lib.service.websocket_client.get_item')
    def test_library_changed_added(self, mock_get_item, mock_scan_kodi):
        episodes = load_data('episodes_jf.json')['Items']
        episodes_by_id = {show['Id']: show for show in episodes}
        episode = episodes_by_id['16a8433c712dceefb0a1538f3609e589']
        data = {'Data': {'ItemsAdded': [episode['Id']],
                         'ItemsRemoved': [],
                         'ItemsUpdated': []},
                'MessageType': 'LibraryChanged'}['Data']
        type(self.player).playing_state = PropertyMock(return_value=None)
        mock_get_item.return_value = episode
        with ThreadPoolExecutor(max_workers=1) as executor:
            library_changed(self.log, executor, self.player, self.settings, self.server, self.mock_user,
                            datetime.datetime.now(), data)
        parsed = urlparse(episode['Path'])
        expected_path = f'{parsed.scheme}://{parsed.netloc}{PurePath(parsed.path).parent}'
        mock_scan_kodi.assert_called_once_with(self.log, expected_path)
