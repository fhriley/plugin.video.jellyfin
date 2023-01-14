import cProfile
import io
import logging
import pstats
import time
import unittest
from pprint import pprint
from pstats import SortKey

import requests

import lib.generic.scraper.movies as movies
import lib.generic.scraper.tvshows as tvshows
from lib.addon.log import LOG_FORMAT
from lib.generic.api.jellyfin import Server
from lib.generic.source import TvShowsSource
from lib.addon.handlers.tvshow import TvShowHandlers

SERVER = 'https://jellyfin.riley-home.net'
USER = 'frank'
PASS = 'ACVs3f!!rDyWJkYdG&oQ9tLy'
CLIENT = 'client'
DEVICE = 'device'
DEVICE_ID = 'device_id'
VERSION = '1.0'

logging.basicConfig(format=LOG_FORMAT, level=logging.DEBUG)
log = logging.getLogger('test')


def get_server(requests_api, debug_level: int):
    return Server(requests_api, SERVER, CLIENT, DEVICE, DEVICE_ID, VERSION, log_raw_resp=debug_level > 2)


def execute(func, num_times=1):
    results = []
    with requests.Session() as session:
        server = get_server(session, debug_level=0)
        user = server.authenticate_by_password(USER, PASS)
        for ii in range(num_times):
            results.append(func(server, user))
    if num_times == 1:
        results = results[0]
    return results


def profile(func, num_times=1):
    results = []
    with cProfile.Profile() as profiler:
        results.append(execute(lambda server, user: func(server, user), num_times))
        profiler.disable()
        sio = io.StringIO()
        sortby = SortKey.CUMULATIVE
        stats = pstats.Stats(profiler, stream=sio)
        ps = stats.sort_stats(sortby)
        ps.print_stats(50)
        if num_times == 1:
            results = results[0]
        return results, sio.getvalue(), stats.total_tt / num_times


class TestScratch(unittest.TestCase):
    def test_get(self):
        with requests.Session() as session:
            server = get_server(session, debug_level=0)
            user = server.authenticate_by_password(USER, PASS)
            # print(user)

            views = server.get_views(user=user)
            for view in views:
                if view['CollectionType'] == 'tvshows':
                    # print(view['Id'])
                    items, _, _ = server.get_items(user=user, params={'ParentId': view['Id']})
                    # pprint(items)

    def test_get_artwork(self):
        with requests.Session() as session:
            server = get_server(session, debug_level=0)
            user = server.authenticate_by_password(USER, PASS)
            scraper = movies.MoviesScraper(server, debug_level=0)

            items = scraper.search_by_title(user, 'planet of the apes', 1968)
            # pprint(items)

            item_id = items[0]['id']
            item = scraper.get_artwork(user, item_id)
            # pprint(item)

    def test_search_movie_by_title(self):
        with requests.Session() as session:
            server = get_server(session, debug_level=0)
            user = server.authenticate_by_password(USER, PASS)
            scraper = movies.MoviesScraper(server, debug_level=0)

            items = scraper.search_by_title(user, 'planet of the apes', 1968)
            # pprint(items)

            item_id = items[0]['id']
            item = scraper.get_by_id(user, item_id)
            # pprint(item)

    def test_search_tvshow_by_title(self):
        with requests.Session() as session:
            server = get_server(session, debug_level=0)
            user = server.authenticate_by_password(USER, PASS)
            scraper = tvshows.TvShowsScraper(server, debug_level=0)

            shows = scraper.get_shows(user)
            pprint(shows)

            # items = scraper.search_by_title(user, 'two and a half men', 2003)
            # # pprint(items)
            #
            # series_id = items[0]['id']
            # item = scraper.get_by_id(user, series_id)
            # # pprint(item)
            #
            # episodes = scraper.get_episodes(user, series_id)
            # # # pprint(episodes)
            # #
            # episode_id = episodes[0]['id']
            # episode = scraper.get_episode_detail(user, series_id, episode_id)
            # pprint(episode)
            #
            # episode_id = episodes[7]['id']
            # episode = scraper.get_episode_detail(user, series_id, episode_id)
            # pprint(episode)

            # images = scraper.get_artwork(user, episode_id)
            # pprint(images)

    def test_get_items(self):
        with requests.Session() as session:
            server = get_server(session, debug_level=0)
            user = server.authenticate_by_password(USER, PASS)
            start_index = 0
            start = time.process_time_ns()
            while True:
                params = {'Limit': 5000, 'Recursive': 'true', 'IncludeItemTypes': 'Movie', 'userId': user.user,
                          'startIndex': start_index}
                items, total, start_index = server.get_items(user, params=params)
                count = len(items)
                if count == 0 or start_index + count == total:
                    break
                start_index += count
            end = time.process_time_ns()
            print((end - start) * 1e-9)

    def test_tvshows_source_get(self):
        with requests.Session() as session:
            server = get_server(session, debug_level=0)
            user = server.authenticate_by_password(USER, PASS)
            source = TvShowsSource(server, debug_level=0)
            shows = source.get(user)
            pprint(shows)

    def test_tvshows_source_get_seasons(self):
        with requests.Session() as session:
            server = get_server(session, debug_level=0)
            user = server.authenticate_by_password(USER, PASS)
            source = TvShowsSource(server, debug_level=0)
            seasons = source.get_seasons(user, 'f37ea375a8efb019acc72ba196e45f39')
            pprint(seasons)

    def test_tvshows_source_get_episodes(self):
        with requests.Session() as session:
            server = get_server(session, debug_level=0)
            user = server.authenticate_by_password(USER, PASS)
            source = TvShowsSource(server, debug_level=0)
            episodes = source.get_episodes(user, 'f37ea375a8efb019acc72ba196e45f39', '5a21f71c36e6358bc59ca05c1b38daa1')
            pprint(episodes)
            episodes = source.get_episodes(user, 'f37ea375a8efb019acc72ba196e45f39', 'df7be5db501e8badbe029d79f33a280d')
            pprint(episodes)

    def test_get_items0(self):
        with requests.Session() as session:
            server = get_server(session, debug_level=0)
            user = server.authenticate_by_password(USER, PASS)
            scraper = tvshows.TvShowsScraper(server, debug_level=0)
            shows = scraper.get_items(user)
            pprint(shows)

    def test_get_seasons(self):
        with requests.Session() as session:
            server = get_server(session, debug_level=0)
            user = server.authenticate_by_password(USER, PASS)
            scraper = tvshows.TvShowsScraper(server, debug_level=0)
            seasons = scraper.get_seasons(user, 'f37ea375a8efb019acc72ba196e45f39')
            pprint(seasons)

    def test_get_episodes0(self):
        with requests.Session() as session:
            server = get_server(session, debug_level=0)
            user = server.authenticate_by_password(USER, PASS)
            scraper = tvshows.TvShowsScraper(server, debug_level=0)
            episodes = scraper.get_episodes(user, 'd78e5ddead5926fba1643090b4d3a1a5')
            pprint(episodes)

    def test_get_episodes(self):
        with requests.Session() as session:
            server = get_server(session, debug_level=0)
            user = server.authenticate_by_password(USER, PASS)
            # print(user)
            # 4369223f7a9bcb0dd0375257f6db85df/8d2bbe76676818c24f3732062bf9fb9d/72428fb38b6aa340f674d85fa2679222
            # 4369223f7a9bcb0dd0375257f6db85df/c3ad55702b189ca71f3005a466e60117/72428fb38b6aa340f674d85fa2679222
            show_id = '4369223f7a9bcb0dd0375257f6db85df'
            params = {'seasonId': '8d2bbe76676818c24f3732062bf9fb9d', 'enableUserData': 'false', 'enableImages': 'false',
                      'sortBy': 'PremiereDate,SortName'}
            jf_episodes = server.get_episodes(user, show_id, params=params)
            pprint(jf_episodes)

            params['seasonId'] = 'c3ad55702b189ca71f3005a466e60117'
            jf_episodes = server.get_episodes(user, show_id, params=params)
            pprint(jf_episodes)
