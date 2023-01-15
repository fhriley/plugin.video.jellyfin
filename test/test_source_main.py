import unittest
from unittest.mock import patch, Mock, PropertyMock

import xbmcaddon

from lib.api.jellyfin import Server, User
from lib.source.entrypoint import main
from lib.util.settings import Settings


@unittest.skip
class TestMain(unittest.TestCase):
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
