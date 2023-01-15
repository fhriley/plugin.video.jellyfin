import logging
import tempfile
import unittest
from typing import Dict, Any
from unittest.mock import patch, Mock, PropertyMock, call, MagicMock
from urllib.parse import quote_plus

import xbmc
import xbmcaddon

from lib.builder.base import get_url
from lib.builder.movies import MoviesBuilder
from lib.builder.tvshows import TvShowsBuilder
from lib.util.log import LOG_FORMAT
from lib.util.settings import Settings
from test.common import load_data, load_episodes_scraper_by_series

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


def check_artwork(tag: MagicMock, obj: Dict[str, Any]):
    if tag.addAvailableArtwork.called:
        info = obj['info']
        expected_calls = [call(url, typ) for typ, url in info['artwork'].items()]
        for season in info.get('seasons') or []:
            artwork = season.get('artwork')
            if artwork:
                expected_calls.append(call(artwork['url'], artwork['type'], season=season['number']))
        if expected_calls:
            tag.addAvailableArtwork.assert_has_calls(expected_calls, any_order=True)


def do_checks(checks: list, info: dict):
    for key, func in checks:
        val = info.get(key)
        if val is not None:
            func.assert_called_once_with(val)


def check_tag(test: unittest.TestCase, tag: MagicMock, obj: Dict[str, Any]):
    checks = [
        ('year', tag.setYear),
        ('rating', tag.setRating),
        ('playcount', tag.setPlaycount),
        ('mpaa', tag.setMpaa),
        ('plot', tag.setPlot),
        ('plotoutline', tag.setPlotOutline),
        ('title', tag.setTitle),
        ('originaltitle', tag.setOriginalTitle),
        ('sorttitle', tag.setSortTitle),
        ('tagline', tag.setTagLine),
        ('genre', tag.setGenres),
        ('country', tag.setCountries),
        ('director', tag.setDirectors),
        ('studio', tag.setStudios),
        ('duration', tag.setDuration),
        ('writer', tag.setWriters),
        ('premiered', tag.setPremiered),
        ('tag', tag.setTags),
        # _('', tag.setProductionCode),
        ('lastplayed', tag.setLastPlayed),
        # _('', tag.setVotes),
        ('trailer', tag.setTrailer),
        # ('path', tag.setPath),
        ('dateadded', tag.setDateAdded),
        ('mediatype', tag.setMediaType),
    ]

    info = obj['info']
    do_checks(checks, info)

    resume_point = info.get('resume_point')
    if resume_point:
        test.assertAlmostEqual(resume_point[0], tag.setResumePoint.call_args.args[0])
        test.assertAlmostEqual(resume_point[1], tag.setResumePoint.call_args.args[1])

    unique_id = tag.setUniqueIDs.call_args[0][0]['jellyfin']
    test.assertEqual(unique_id, obj['id'])
    test.assertEqual(tag.setUniqueIDs.call_args[1], {'defaultuniqueid': 'jellyfin'})

    check_artwork(tag, obj)

    # TODO: setUserRating, addSubtitleStream, setCast, addVideoStream, addAudioStream


def check_show_tag(tag: MagicMock, obj: Dict[str, Any]):
    checks = [
        ('tvshowtitle', tag.setTvShowTitle),
        ('status', tag.setTvShowStatus),
        ('aired', tag.setFirstAired),
    ]
    info = obj['info']
    do_checks(checks, info)


def check_episode_tag(tag: MagicMock, obj: Dict[str, Any]):
    checks = [
        ('season', tag.setSeason),
        ('episode', tag.setEpisode),
        ('sortseason', tag.setSortSeason),
        ('sortepisode', tag.setSortEpisode),
        ('aired', tag.setFirstAired),
    ]
    info = obj['info']
    do_checks(checks, info)


def _create_builder(handle, temp_dir, builder_class, addon=None):
    settings = get_mock_settings(temp_dir)
    if addon is None:
        addon = get_mock_addon()
    return builder_class(settings, handle, addon)


class TestBuilder(unittest.TestCase):
    def _test_build_directory(self, mock_xbmcplugin, mock_xbmcgui, handle, builder_func, in_json_file, media_type,
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

    @patch('lib.builder.base.xbmcgui')
    @patch('lib.builder.base.xbmcplugin')
    def test_movies_build_directory(self, mock_xbmcplugin, mock_xbmcgui):
        handle = 1
        with tempfile.TemporaryDirectory() as temp_dir:
            builder = _create_builder(handle, temp_dir, MoviesBuilder)
            self._test_build_directory(mock_xbmcplugin, mock_xbmcgui, handle, builder.build_directory,
                                       'movies_scraper.json',
                                       'movies', 'movies', True)

    @patch('lib.builder.base.xbmcgui')
    @patch('lib.builder.base.xbmcplugin')
    def test_tvshows_build_directory(self, mock_xbmcplugin, mock_xbmcgui):
        handle = 1
        with tempfile.TemporaryDirectory() as temp_dir:
            builder = _create_builder(handle, temp_dir, TvShowsBuilder)
            self._test_build_directory(mock_xbmcplugin, mock_xbmcgui, handle, builder.build_directory,
                                       'tvshows_scraper.json',
                                       'tvshows', 'tvshows', True)

    # @patch('lib.builder.tvshows.xbmcgui')
    # @patch('lib.builder.tvshows.xbmcplugin')
    # def test_episodes_build_directory(self, mock_xbmcplugin, mock_xbmcgui):
    #     handle = 1
    #     with tempfile.TemporaryDirectory() as temp_dir:
    #         builder = _create_builder(handle, temp_dir, TvShowsBuilder)
    #         self._test_build_directory(mock_xbmcplugin, mock_xbmcgui, handle, builder.build_episodes_directory,
    #                                    'episodes_scraper.json',
    #                                    'tvshows', 'episodes', False, ('series_id', 'id'))

    @patch('lib.builder.base.xbmcgui')
    @patch('lib.builder.base.xbmcplugin')
    def test_build_find_directory(self, mock_xbmcplugin, mock_xbmcgui):
        handle = 1
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_list_item = mock_xbmcgui.ListItem
            mock_xbmcgui.ListItem.return_value = mock_list_item
            addon = get_mock_addon()
            builder = _create_builder(handle, temp_dir, TvShowsBuilder, addon)

            input = [{'id': '43df71c52fff642be7e32c048322de8c', 'name': 'Breaking Bad (2008)'}]
            builder.build_find_directory(input)
            mock_xbmcgui.ListItem.assert_called_once_with(input[0]['name'])
            expected_items = [(f'plugin://addon/find?id={input[0]["id"]}&name={quote_plus(input[0]["name"])}', mock_list_item, True)]
            mock_xbmcplugin.addDirectoryItems.assert_called_once_with(handle=handle, items=expected_items)
            mock_xbmcplugin.endOfDirectory.assert_called_once_with(handle=handle, succeeded=True)

    @patch('lib.builder.base.xbmcgui')
    @patch('lib.builder.base.xbmcplugin')
    def test_build_artwork(self, mock_xbmcplugin, mock_xbmcgui):
        handle = 1
        with tempfile.TemporaryDirectory() as temp_dir:
            jf_artwork = load_data('artwork_jf.json')
            artwork = load_data('artwork_scraper.json')
            mock_list_item = mock_xbmcgui.ListItem
            mock_xbmcgui.ListItem.return_value = mock_list_item
            mock_info_tag_video = MagicMock(xbmc.InfoTagVideo)
            mock_xbmcgui.ListItem.getVideoInfoTag.return_value = mock_info_tag_video

            builder = _create_builder(handle, temp_dir, TvShowsBuilder)
            builder.build_artwork(jf_artwork['Id'], artwork)

            mock_xbmcgui.ListItem.assert_called_once_with(jf_artwork['Id'], offscreen=True)
            mock_xbmcgui.ListItem.getVideoInfoTag.assert_called_once()
            expected_calls = [call(url, typ) for typ, url in artwork.items()]
            mock_info_tag_video.addAvailableArtwork.assert_has_calls(expected_calls)
            mock_xbmcplugin.setResolvedUrl.assert_called_with(handle=handle, succeeded=True, listitem=mock_list_item)

    @patch('lib.builder.movies.xbmcgui')
    @patch('lib.builder.movies.xbmcplugin')
    def test_build_movie(self, mock_xbmcplugin, mock_xbmcgui):
        handle = 1
        with tempfile.TemporaryDirectory() as temp_dir:
            movies = load_data('movies_scraper.json')
            mock_list_item = mock_xbmcgui.ListItem
            mock_xbmcgui.ListItem.return_value = mock_list_item
            mock_info_tag_video = MagicMock(xbmc.InfoTagVideo)
            mock_xbmcgui.ListItem.getVideoInfoTag.return_value = mock_info_tag_video
            builder = _create_builder(handle, temp_dir, MoviesBuilder)

            for movie in movies:
                builder.build_movie(movie)
                mock_xbmcgui.ListItem.assert_called_once_with(movie['name'], offscreen=True)
                mock_xbmcgui.ListItem.getVideoInfoTag.assert_called_once_with()
                check_tag(self, mock_info_tag_video, movie)
                mock_xbmcplugin.setResolvedUrl.assert_called_once_with(handle=handle, succeeded=True,
                                                                       listitem=mock_list_item)

                mock_xbmcgui.ListItem.reset_mock()
                mock_xbmcplugin.setResolvedUrl.reset_mock()
                mock_info_tag_video.reset_mock()

    @patch('lib.builder.tvshows.xbmcgui')
    @patch('lib.builder.tvshows.xbmcplugin')
    def test_build_show(self, mock_xbmcplugin, mock_xbmcgui):
        handle = 1
        with tempfile.TemporaryDirectory() as temp_dir:
            shows = load_data('tvshows_scraper.json')
            mock_list_item = mock_xbmcgui.ListItem
            mock_xbmcgui.ListItem.return_value = mock_list_item
            mock_info_tag_video = MagicMock(xbmc.InfoTagVideo)
            mock_xbmcgui.ListItem.getVideoInfoTag.return_value = mock_info_tag_video
            builder = _create_builder(handle, temp_dir, TvShowsBuilder)

            for show in shows:
                builder.build_show(show)
                mock_xbmcgui.ListItem.assert_called_once_with(show['name'], offscreen=True)
                mock_xbmcgui.ListItem.getVideoInfoTag.assert_called_once_with()
                check_tag(self, mock_info_tag_video, show)
                check_show_tag(mock_info_tag_video, show)
                mock_info_tag_video.setEpisodeGuide.assert_called_with(f'plugin://addon/tvshows?id={show["id"]}')
                mock_xbmcplugin.setResolvedUrl.assert_called_once_with(handle=handle, succeeded=True,
                                                                       listitem=mock_list_item)

                mock_xbmcgui.ListItem.reset_mock()
                mock_xbmcplugin.setResolvedUrl.reset_mock()
                mock_info_tag_video.reset_mock()

    @patch('lib.builder.tvshows.xbmcgui')
    @patch('lib.builder.tvshows.xbmcplugin')
    def test_build_episodes_directory(self, mock_xbmcplugin, mock_xbmcgui):
        handle = 1
        with tempfile.TemporaryDirectory() as temp_dir:
            all_episodes = load_episodes_scraper_by_series()
            mock_list_item = mock_xbmcgui.ListItem
            mock_xbmcgui.ListItem.return_value = mock_list_item
            mock_info_tag_video = MagicMock(xbmc.InfoTagVideo)
            mock_xbmcgui.ListItem.getVideoInfoTag.return_value = mock_info_tag_video
            addon = get_mock_addon()
            builder = _create_builder(handle, temp_dir, TvShowsBuilder, addon)

            for _, episodes in all_episodes.items():
                builder.build_episodes_directory(episodes)
                expected_calls = [call(episode['name'], offscreen=True) for episode in episodes]
                mock_xbmcgui.ListItem.has_calls(expected_calls)
                expected_calls = [call()] * len(episodes)
                mock_xbmcgui.ListItem.has_calls(expected_calls)
                # TODO: add tag checks
                mock_xbmcplugin.setContent.assert_called_once_with(handle=handle, content='episodes')
                expected_items = [(get_url(addon, 'tvshows', id=episode['id']), mock_list_item, False) for episode in
                                  episodes]
                mock_xbmcplugin.addDirectoryItems.assert_called_once_with(handle=handle, items=expected_items)
                mock_xbmcplugin.endOfDirectory.assert_called_once_with(handle=handle, succeeded=True)

                mock_xbmcgui.ListItem.reset_mock()
                mock_xbmcplugin.setContent.reset_mock()
                mock_xbmcplugin.addDirectoryItems.reset_mock()
                mock_xbmcplugin.endOfDirectory.reset_mock()

    @patch('lib.builder.tvshows.xbmcgui')
    @patch('lib.builder.tvshows.xbmcplugin')
    def test_build_episode(self, mock_xbmcplugin, mock_xbmcgui):
        handle = 1
        with tempfile.TemporaryDirectory() as temp_dir:
            episodes = load_data('episodes_scraper.json')
            mock_list_item = mock_xbmcgui.ListItem
            mock_xbmcgui.ListItem.return_value = mock_list_item
            mock_info_tag_video = MagicMock(xbmc.InfoTagVideo)
            mock_xbmcgui.ListItem.getVideoInfoTag.return_value = mock_info_tag_video
            builder = _create_builder(handle, temp_dir, TvShowsBuilder)

            for episode in episodes:
                builder.build_episode(episode)
                mock_xbmcgui.ListItem.assert_called_once_with(episode['name'], offscreen=True)
                mock_xbmcgui.ListItem.getVideoInfoTag.assert_called_once_with()
                check_tag(self, mock_info_tag_video, episode)
                check_episode_tag(mock_info_tag_video, episode)
                mock_xbmcplugin.setResolvedUrl.assert_called_once_with(handle=handle, succeeded=True,
                                                                       listitem=mock_list_item)

                mock_xbmcgui.ListItem.reset_mock()
                mock_xbmcplugin.setResolvedUrl.reset_mock()
                mock_info_tag_video.reset_mock()
