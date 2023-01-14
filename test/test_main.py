import unittest
from unittest.mock import patch, Mock, call

import xbmcaddon

from lib.generic.api.jellyfin import Server, User
from source.entrypoint import main


class TestMain(unittest.TestCase):
    @patch('source.entrypoint.get_tvshows')
    @patch('source.entrypoint.authenticate')
    @patch('source.entrypoint.get_server')
    @patch('source.entrypoint.requests')
    @patch('source.entrypoint.xbmcaddon')
    def test_tvshows(self, mock_xbmcaddon, mock_requests, mock_get_server, mock_authenticate, mock_get_tvshows):
        addon = Mock(xbmcaddon.Addon)
        server = Mock(Server)
        user = Mock(User)
        mock_xbmcaddon.Addon.return_value = addon
        mock_get_server.return_value = server
        mock_authenticate.return_value = user
        main('plugin://plugin.video.jellyfin/library/tvshows/', '1')
        mock_get_tvshows.assert_called_with(1, addon, server, user, debug_level=0)
        main('plugin://plugin.video.jellyfin/library/tvshows', '2')
        mock_get_tvshows.assert_called_with(2, addon, server, user, debug_level=0)

    @patch('source.entrypoint.get_seasons')
    @patch('source.entrypoint.authenticate')
    @patch('source.entrypoint.get_server')
    @patch('source.entrypoint.requests')
    @patch('source.entrypoint.xbmcaddon')
    def test_seasons(self, mock_xbmcaddon, mock_requests, mock_get_server, mock_authenticate, mock_get_seasons):
        addon = Mock(xbmcaddon.Addon)
        server = Mock(Server)
        user = Mock(User)
        mock_xbmcaddon.Addon.return_value = addon
        mock_get_server.return_value = server
        mock_authenticate.return_value = user
        main('plugin://plugin.video.jellyfin/library/tvshows/foo/', '1')
        mock_get_seasons.assert_called_with(1, addon, server, user, 'foo', debug_level=0)
        main('plugin://plugin.video.jellyfin/library/tvshows/bar', '2')
        mock_get_seasons.assert_called_with(2, addon, server, user, 'foo', debug_level=0)

    @patch('source.entrypoint.get_episodes')
    @patch('source.entrypoint.authenticate')
    @patch('source.entrypoint.get_server')
    @patch('source.entrypoint.requests')
    @patch('source.entrypoint.xbmcaddon')
    def test_episodes(self, mock_xbmcaddon, mock_requests, mock_get_server, mock_authenticate, mock_get_episodes):
        addon = Mock(xbmcaddon.Addon)
        server = Mock(Server)
        user = Mock(User)
        mock_xbmcaddon.Addon.return_value = addon
        mock_get_server.return_value = server
        mock_authenticate.return_value = user
        main('plugin://plugin.video.jellyfin/library/tvshows/foo/bar/', '1')
        mock_get_episodes.assert_called_with(1, addon, server, user, 'foo', 'bar', debug_level=0)
        main('plugin://plugin.video.jellyfin/library/tvshows/foo/bar', '2')
        mock_get_episodes.assert_called_with(2, addon, server, user, 'foo', 'bar', debug_level=0)
