import unittest
from unittest.mock import patch, Mock, PropertyMock

import xbmcaddon

from lib.api.jellyfin import Server, User, authenticate
from lib.source.entrypoint import main
from lib.source.settings import Settings


class TestMain(unittest.TestCase):
    def test_authenticate(self):
        password = 'password'
        expected_user = User('user', 'user_id', 'token')
        user_cache = {}

        server = Mock(Server)
        server.authenticate_by_password.return_value = expected_user
        type(server).server = PropertyMock(return_value='http://server')

        server.is_authenticated.return_value = False
        user = authenticate(server, user_cache, expected_user.user, password)
        server.authenticate_by_password.assert_called_once_with(expected_user.user, password)
        self.assertEqual(expected_user, user)

        server.is_authenticated.return_value = True
        user = authenticate(server, user_cache, expected_user.user, password)
        server.authenticate_by_password.assert_called_once()
        self.assertEqual(expected_user, user)

    def test_authenticate_cached(self):
        password = 'password'
        expected_user = User('user', 'user_id', 'token')
        user_cache = {}

        server = Mock(Server)
        server.authenticate_by_password.return_value = expected_user
        type(server).server = PropertyMock(return_value='http://server')

        server.is_authenticated.return_value = False
        user = authenticate(server, user_cache, expected_user.user, password)
        server.authenticate_by_password.assert_called_once_with(expected_user.user, password)
        self.assertEqual(expected_user, user)

        server.is_authenticated.return_value = True
        user = authenticate(server, user_cache, expected_user.user, password)
        server.authenticate_by_password.assert_called_once()
        self.assertEqual(expected_user, user)

        server.is_authenticated.return_value = False
        user = authenticate(server, user_cache, expected_user.user, password)
        server.authenticate_by_password.assert_called_with(expected_user.user, password)
        self.assertEqual(expected_user, user)

    @patch('lib.source.entrypoint.TvShowsBuilder')
    @patch('lib.source.entrypoint.TvShowsScraper')
    @patch('lib.source.entrypoint.authenticate')
    @patch('lib.source.entrypoint.Settings')
    @patch('lib.source.entrypoint.get_server')
    @patch('lib.source.entrypoint.xbmcaddon')
    def test_tvshows(self, mock_xbmcaddon, mock_get_server, mock_settings, mock_authenticate, mock_scraper,
                     mock_builder):
        addon = Mock(xbmcaddon.Addon)
        settings = Mock(Settings)
        type(settings).debug_level = PropertyMock(return_value=0)
        mock_settings.return_value = settings
        server = Mock(Server)
        user = Mock(User)
        mock_xbmcaddon.Addon.return_value = addon
        mock_get_server.return_value = server
        mock_authenticate.return_value = user
        mock_scraper.return_value = mock_scraper
        mock_builder.return_value = mock_builder

        main('plugin://plugin.video.jellyfin/library/tvshows/', '1')
        mock_scraper.assert_called_with(server, debug_level=0)
        mock_scraper.get_items.assert_called_with(user)
        mock_builder.assert_called_with(settings, 1, addon)
        mock_builder.build_directory.assert_called()

        main('plugin://plugin.video.jellyfin/library/tvshows', '2')
        mock_scraper.assert_called_with(server, debug_level=0)
        mock_scraper.get_items.assert_called_with(user)
        mock_builder.assert_called_with(settings, 2, addon)
        mock_builder.build_directory.assert_called()

    @patch('lib.source.entrypoint.TvShowsBuilder')
    @patch('lib.source.entrypoint.TvShowsScraper')
    @patch('lib.source.entrypoint.authenticate')
    @patch('lib.source.entrypoint.Settings')
    @patch('lib.source.entrypoint.get_server')
    @patch('lib.source.entrypoint.xbmcaddon')
    def test_episodes(self, mock_xbmcaddon, mock_get_server, mock_settings, mock_authenticate, mock_scraper,
                      mock_builder):
        addon = Mock(xbmcaddon.Addon)
        settings = Mock(Settings)
        type(settings).debug_level = PropertyMock(return_value=0)
        mock_settings.return_value = settings
        server = Mock(Server)
        user = Mock(User)
        mock_xbmcaddon.Addon.return_value = addon
        mock_get_server.return_value = server
        mock_authenticate.return_value = user
        mock_scraper.return_value = mock_scraper
        mock_builder.return_value = mock_builder

        main('plugin://plugin.video.jellyfin/library/tvshows/series/', '1')
        mock_scraper.assert_called_with(server, debug_level=0)
        mock_scraper.get_episodes.assert_called_with(user, 'series')
        mock_builder.assert_called_with(settings, 1, addon)
        mock_builder.build_episodes.assert_called()

        main('plugin://plugin.video.jellyfin/library/tvshows/series', '2')
        mock_scraper.assert_called_with(server, debug_level=0)
        mock_scraper.get_episodes.assert_called_with(user, 'series')
        mock_builder.assert_called_with(settings, 2, addon)
        mock_builder.build_episodes.assert_called()
