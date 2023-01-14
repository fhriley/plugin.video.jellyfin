import logging
import tempfile
import unittest
from unittest.mock import patch, Mock, PropertyMock, call

import xbmcaddon

from lib.source.builder.movies import MoviesBuilder
from lib.source.builder.tvshows import TvShowsBuilder
from lib.source.log import LOG_FORMAT
from lib.source.settings import Settings
from test.common import load_data

logging.basicConfig(format=LOG_FORMAT, level=logging.INFO)

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


class TestBuilder(unittest.TestCase):
    def _create_builder(self, handle, temp_dir, builder_class):
        settings = get_mock_settings(temp_dir)
        addon = get_mock_addon()
        return builder_class(settings, handle, addon)

    def _test_builder(self, mock_xbmcplugin, mock_xbmcgui, handle, builder_func, in_json_file, media_type,
                      content_type, is_folder, url_keys=('id',)):
        items = load_data(in_json_file)
        list_item = mock_xbmcgui.ListItem
        mock_xbmcgui.ListItem.return_value = list_item
        builder_func(items)

        self.assertEqual(len(items), mock_xbmcgui.ListItem.call_count)
        expected = [call(item['name'], offscreen=True) for item in items]
        self.assertEqual(expected, mock_xbmcgui.ListItem.call_args_list)

        mock_xbmcplugin.setContent.assert_called_with(handle=handle, content=content_type)

        expected = []
        for item in items:
            paths = '/'.join([item[key] for key in url_keys])
            expected.append((f'plugin://{_addon_id}/library/{media_type}/{paths}', list_item, is_folder))
        mock_xbmcplugin.addDirectoryItems.assert_called_with(handle=handle, items=expected)
        mock_xbmcplugin.endOfDirectory.assert_called_with(handle=handle, succeeded=True)

    @patch('lib.source.builder.base.xbmcgui')
    @patch('lib.source.builder.base.xbmcplugin')
    def test_movies_builder(self, mock_xbmcplugin, mock_xbmcgui):
        handle = 1
        with tempfile.TemporaryDirectory() as temp_dir:
            builder = self._create_builder(handle, temp_dir, MoviesBuilder)
            self._test_builder(mock_xbmcplugin, mock_xbmcgui, handle, builder.build_directory, 'movies_scraper.json',
                               'movies', 'movies', True)

    @patch('lib.source.builder.base.xbmcgui')
    @patch('lib.source.builder.base.xbmcplugin')
    def test_tvshows_builder(self, mock_xbmcplugin, mock_xbmcgui):
        handle = 1
        with tempfile.TemporaryDirectory() as temp_dir:
            builder = self._create_builder(handle, temp_dir, TvShowsBuilder)
            self._test_builder(mock_xbmcplugin, mock_xbmcgui, handle, builder.build_directory, 'tvshows_scraper.json',
                               'tvshows', 'tvshows', True)

    @patch('lib.source.builder.tvshows.xbmcgui')
    @patch('lib.source.builder.tvshows.xbmcplugin')
    def test_episodes_builder(self, mock_xbmcplugin, mock_xbmcgui):
        handle = 1
        with tempfile.TemporaryDirectory() as temp_dir:
            builder = self._create_builder(handle, temp_dir, TvShowsBuilder)
            self._test_builder(mock_xbmcplugin, mock_xbmcgui, handle, builder.build_episodes, 'episodes_scraper.json',
                               'tvshows', 'episodes', False, ('series_id', 'id'))
