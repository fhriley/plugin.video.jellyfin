import tempfile
import unittest
from unittest.mock import Mock, PropertyMock, MagicMock, patch

import requests
import xbmcaddon

from lib.api.jellyfin import User
from lib.builder.base import Builder
from lib.builder.movies import MoviesBuilder
from lib.builder.tvshows import TvShowsBuilder
from lib.router.movies import MoviesRouter
from lib.router.tvshows import TvShowsRouter
from lib.scraper.base import Scraper
from lib.scraper.movies import MoviesScraper
from lib.scraper.tvshows import TvShowsScraper
from lib.util.settings import Settings
from test.common import (get_server, load_data, load_seasons_jf_by_series, load_episodes_jf_by_series,
                         load_episodes_scraper_by_series)

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


class TestRouter(unittest.TestCase):
    def setUp(self):
        self.handle = 1
        self.temp_dir = tempfile.TemporaryDirectory()
        self.mock_requests = MagicMock(requests.Session)
        self.settings = get_mock_settings(self.temp_dir)
        self.addon = get_mock_addon()
        self.server = get_server(self.mock_requests)
        self.scraper = MagicMock(Scraper)
        self.tvshows_scraper = MagicMock(TvShowsScraper)
        self.movies_scraper = MagicMock(MoviesScraper)
        self.builder = MagicMock(Builder)
        self.tvshows_builder = MagicMock(TvShowsBuilder)
        self.movies_builder = MagicMock(MoviesBuilder)
        self.mock_user = MagicMock(User)

    def tearDown(self):
        self.temp_dir.cleanup()

    @patch('lib.router.base.authenticate')
    def test_execute(self, mock_authenticate):
        mock_authenticate.return_value = self.mock_user
        tests = [
            {'router': MoviesRouter(self.settings, self.handle, self.addon, self.server),
             'funcs': ('find', 'getartwork', 'nfourl', 'getdetails')},
            {'router': TvShowsRouter(self.settings, self.handle, self.addon, self.server),
             'funcs': ('find', 'getartwork', 'nfourl', 'getdetails', 'getepisodelist', 'getepisodedetails')}
        ]
        for test in tests:
            router = test['router']
            for func in test['funcs']:
                params = {'action': func}
                with patch.object(type(router), func, return_value=None) as mock_func:
                    mock_func.__name__ = func
                    router.execute(self.scraper, self.builder, params)
                    mock_func.assert_called_once_with(self.mock_user, self.scraper, self.builder, params)

    @patch('lib.router.base.find_by_title')
    @patch('lib.router.base.authenticate')
    def test_find(self, mock_authenticate, mock_find_by_title):
        in_jf_data = load_data('movies_jf.json')
        in_scraper_data = load_data('movies_scraper.json')
        movie = in_jf_data['Items'][0]
        mock_authenticate.return_value = self.mock_user
        params = {'action': 'find', 'title': movie['Name'], 'year': movie['ProductionYear']}
        find_return = {'Items': [movie], 'TotalRecordCount': 1, 'StartIndex': 0}
        mock_find_by_title.return_value = find_return
        type(self.scraper).jf_item_type = PropertyMock(return_value='Movie')
        self.scraper.scrape_find.return_value = in_scraper_data[0]

        router = MoviesRouter(self.settings, self.handle, self.addon, self.server)
        router.execute(self.scraper, self.builder, params)

        mock_find_by_title.assert_called_once_with(self.server, self.mock_user, 'Movie', movie['Name'],
                                                   movie['ProductionYear'])
        self.scraper.scrape_find.assert_called_once_with(find_return['Items'])
        self.builder.build_find_directory.assert_called_once_with(in_scraper_data[0])

    @patch('lib.router.base.get_artwork')
    @patch('lib.router.base.authenticate')
    def test_getartwork(self, mock_authenticate, mock_get_artwork):
        artwork_jf = load_data('artwork_jf.json')
        artwork_scraper = load_data('artwork_scraper.json')
        mock_authenticate.return_value = self.mock_user
        params = {'action': 'getartwork', 'id': f'{artwork_jf["Id"]}'}
        mock_get_artwork.return_value = artwork_jf
        self.scraper.scrape_artwork.return_value = artwork_scraper

        router = MoviesRouter(self.settings, self.handle, self.addon, self.server)
        router.execute(self.scraper, self.builder, params)

        mock_get_artwork.assert_called_once_with(self.server, self.mock_user, artwork_jf["Id"])
        self.scraper.scrape_artwork.assert_called_once_with(artwork_jf)
        self.builder.build_artwork.assert_called_once_with(artwork_jf["Id"], artwork_scraper)

    @patch('lib.router.movies.get_item')
    @patch('lib.router.base.authenticate')
    def test_movies_getdetails(self, mock_authenticate, mock_get_item):
        in_jf_data = load_data('movies_jf.json')
        in_scraper_data = load_data('movies_scraper.json')
        movie = in_jf_data['Items'][0]
        mock_authenticate.return_value = self.mock_user
        params = {'action': 'getdetails', 'url': f'/foo?id={movie["Id"]}'}
        mock_get_item.return_value = movie
        self.movies_scraper.scrape_movie.return_value = in_scraper_data[0]

        router = MoviesRouter(self.settings, self.handle, self.addon, self.server)
        router.execute(self.movies_scraper, self.movies_builder, params)

        mock_get_item.assert_called_once_with(self.server, self.mock_user, movie["Id"])
        self.movies_scraper.scrape_movie.assert_called_once_with(movie)
        self.movies_builder.build_movie.assert_called_once_with(in_scraper_data[0])

    @patch('lib.router.tvshows.get_seasons')
    @patch('lib.router.tvshows.get_item')
    @patch('lib.router.base.authenticate')
    def test_tvshows_getdetails(self, mock_authenticate, mock_get_item, mock_get_seasons):
        in_jf_data = load_data('tvshows_jf.json')
        in_scraper_data = load_data('tvshows_scraper.json')
        show = in_jf_data['Items'][0]
        seasons = load_seasons_jf_by_series()[show['Id']]
        seasons = {'Items': seasons, 'TotalRecordCount': len(seasons), 'StartIndex': 0}
        mock_authenticate.return_value = self.mock_user
        params = {'action': 'getdetails', 'url': f'/foo?id={show["Id"]}'}
        mock_get_item.return_value = show
        mock_get_seasons.return_value = seasons
        self.tvshows_scraper.scrape_show.return_value = in_scraper_data[0]

        router = TvShowsRouter(self.settings, self.handle, self.addon, self.server)
        router.execute(self.tvshows_scraper, self.tvshows_builder, params)

        mock_get_item.assert_called_once_with(self.server, self.mock_user, show["Id"])
        mock_get_seasons.assert_called_once_with(self.server, self.mock_user, show["Id"])
        self.tvshows_scraper.scrape_show.assert_called_once_with(show, seasons['Items'])
        self.tvshows_builder.build_show.assert_called_once_with(in_scraper_data[0])

    @patch('lib.router.tvshows.get_episodes_min')
    @patch('lib.router.base.authenticate')
    def test_tvshows_getepisodelist(self, mock_authenticate, mock_get_episodes_min):
        in_jf_data = load_data('tvshows_jf.json')
        episodes_jf_in = load_episodes_jf_by_series()
        episodes_scraper_in = load_episodes_scraper_by_series()
        show = None
        episodes_jf = None
        episodes_scraper = None
        for show in in_jf_data['Items']:
            episodes_jf = episodes_jf_in.get(show['Id'])
            episodes_scraper = episodes_scraper_in.get(show['Id'])
            if episodes_jf and episodes_scraper:
                break
        mock_authenticate.return_value = self.mock_user
        params = {'action': 'getepisodelist', 'url': f'/foo?id={show["Id"]}'}
        episode_min_return = {'Items': episodes_jf, 'TotalRecordCount': 1, 'StartIndex': 0}
        mock_get_episodes_min.return_value = episode_min_return
        self.tvshows_scraper.scrape_episodes.return_value = episodes_scraper

        router = TvShowsRouter(self.settings, self.handle, self.addon, self.server)
        router.execute(self.tvshows_scraper, self.tvshows_builder, params)

        mock_get_episodes_min.assert_called_once_with(self.server, self.mock_user, show["Id"])
        self.tvshows_scraper.scrape_episodes.assert_called_once_with(episodes_jf)
        self.tvshows_builder.build_episodes_directory.assert_called_once_with(episodes_scraper)

    @patch('lib.router.tvshows.get_item')
    @patch('lib.router.base.authenticate')
    def test_tvshows_getepisodedetails(self, mock_authenticate, mock_get_item):
        in_jf_data = load_data('episodes_jf.json')
        in_scraper_data = load_data('episodes_scraper.json')
        episode = in_jf_data['Items'][0]
        mock_authenticate.return_value = self.mock_user
        params = {'action': 'getepisodedetails', 'url': f'/foo?id={episode["Id"]}'}
        mock_get_item.return_value = episode
        self.tvshows_scraper.scrape_episode.return_value = in_scraper_data[0]

        router = TvShowsRouter(self.settings, self.handle, self.addon, self.server)
        router.execute(self.tvshows_scraper, self.tvshows_builder, params)

        mock_get_item.assert_called_once_with(self.server, self.mock_user, episode["Id"])
        self.tvshows_scraper.scrape_episode.assert_called_once_with(episode)
        self.tvshows_builder.build_episode.assert_called_once_with(in_scraper_data[0])
