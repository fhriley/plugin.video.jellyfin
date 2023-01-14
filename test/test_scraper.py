import logging
import unittest
from typing import Union

from lib.api.jellyfin import Server
from lib.scraper.movies import MoviesScraper
from lib.scraper.tvshows import TvShowsScraper
from lib.source.log import LOG_FORMAT
from test.common import get_user, load_episodes_jf_by_series, load_data, load_data_scraper, get_mock_server

logging.basicConfig(format=LOG_FORMAT, level=logging.INFO)


class TestScraper(unittest.TestCase):
    def _test_get_items(self, server: Server, scraper_class: Union[type(MoviesScraper), type(TvShowsScraper)],
                        out_file: str):
        scraper = scraper_class(server, debug_level=0)
        user = get_user()
        items = scraper.get_items(user)
        # with open(out_file, 'w') as out:
        #     json.dump(items, out, indent=4, sort_keys=True)
        expected = load_data_scraper(out_file)
        for item in items:
            expected_item = expected.get(item['id'])
            self.assertEqual(expected_item, item)

    def test_movies_get_items(self):
        server = get_mock_server()
        server.get_items.return_value = load_data('movies_jf.json')
        self.maxDiff = None
        self._test_get_items(server, MoviesScraper, 'movies_scraper.json')

    def test_tvshows_get_items(self):
        server = get_mock_server()
        server.get_items.return_value = load_data('tvshows_jf.json')
        server.get_seasons.return_value = load_data('seasons_jf.json')
        self._test_get_items(server, TvShowsScraper, 'tvshows_scraper.json')

    def test_tvshows_get_episodes(self):
        series_id = '7879d2c8a44a666d6846d4eea026ddd3'

        in_items = load_episodes_jf_by_series()[series_id]
        data = {
            'Items': in_items,
            'StartIndex': 0,
            'TotalRecordCount': len(in_items),
        }

        server = get_mock_server()
        server.get_episodes.return_value = data

        scraper = TvShowsScraper(server, debug_level=0)
        user = get_user()
        items = scraper.get_episodes(user, series_id)
        # with open('episodes_scraper.json', 'w') as out:
        #     json.dump(items, out, indent=4, sort_keys=True)

        expected = load_data_scraper('episodes_scraper.json')
        for item in items:
            expected_item = expected.get(item['id'])
            self.assertEqual(expected_item, item)
