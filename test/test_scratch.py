import cProfile
import io
import logging
import pstats
import time
import unittest
from pprint import pprint
from pstats import SortKey
from typing import Union

import requests

from lib.api.jellyfin import Server
from lib.scraper.movies import MoviesScraper
from lib.scraper.queries import get_episodes, get_artwork
from lib.scraper.tvshows import TvShowsScraper
from lib.util.log import LOG_FORMAT

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


@unittest.skip
class TestScratch(unittest.TestCase):
    def test_get_item(self):
        with requests.Session() as session:
            server = get_server(session, debug_level=0)
            user = server.authenticate_by_password(USER, PASS)
            params = {'fields': 'Path', 'enableUserData': 'true'}
            item = server.get_item(user, '6ce12311f8993cf1a212881db0677f2a', params=params)
            pprint(item)

    def _test_get_items(self, scraper_class: Union[type(MoviesScraper), type(TvShowsScraper)], out_file: str):
        with requests.Session() as session:
            server = get_server(session, debug_level=0)
            user = server.authenticate_by_password(USER, PASS)
            scraper = scraper_class(server, debug_level=0)
            start = time.process_time_ns()
            items = scraper.get_items(user)
            end = time.process_time_ns()
            print((end - start) * 1e-9)
            # with open(out_file, 'w') as out:
            #     import json
            #     json.dump(items, out, indent=4, sort_keys=True)

    def test_get_tvshows(self):
        self._test_get_items(TvShowsScraper, 'data/tvshows_scraper.json')

    def test_get_movies(self):
        self._test_get_items(MoviesScraper, 'data/movies_scraper.json')

    def test_get_items_chunked(self):
        with requests.Session() as session:
            server = get_server(session, debug_level=0)
            user = server.authenticate_by_password(USER, PASS)
            start = time.process_time_ns()
            params = {'Recursive': 'true', 'IncludeItemTypes': 'Movie', 'userId': user.user}
            items = server.get_items(user, chunk_size=100, params=params)
            end = time.process_time_ns()
            print((end - start) * 1e-9)
            print(len(items['Items']))

    def test_get_episodes(self):
        with requests.Session() as session:
            server = get_server(session, debug_level=0)
            user = server.authenticate_by_password(USER, PASS)
            episodes = get_episodes(server, user, chunk_size=100)
            pprint(episodes['Items'][:10])
            # with open('data/episodes_jf.json', 'w') as out:
            #     import json
            #     json.dump(episodes, out, indent=4, sort_keys=True)

    def test_get_artwork(self):
        with requests.Session() as session:
            server = get_server(session, debug_level=0)
            user = server.authenticate_by_password(USER, PASS)
            artwork = get_artwork(server, user, '6ce12311f8993cf1a212881db0677f2a')
            # with open('data/artwork_jf.json', 'w') as out:
            #     import json
            #     json.dump(artwork, out, indent=4, sort_keys=True)
