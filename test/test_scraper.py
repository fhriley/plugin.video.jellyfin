import logging
import unittest

from lib.scraper.base import get_name
from lib.scraper.movies import MoviesScraper
from lib.scraper.queries import seasons_by_series
from lib.scraper.tvshows import TvShowsScraper
from lib.util.log import LOG_FORMAT
from test.common import load_episodes_jf_by_series, load_data, get_mock_server

logging.basicConfig(format=LOG_FORMAT, level=logging.DEBUG)


class TestScraper(unittest.TestCase):
    def test_find(self):
        server = get_mock_server()
        scraper = MoviesScraper(server, debug_level=0)
        in_data = load_data('movies_jf.json').get('Items') or []
        movies = scraper.scrape_find(in_data)
        expected = [{'id': movie['Id'], 'name': get_name(movie['Name'], movie['ProductionYear'])} for movie in in_data]
        self.assertEqual(expected, movies)

    def test_artwork(self):
        server = get_mock_server()
        scraper = MoviesScraper(server, debug_level=0)
        in_data = load_data('artwork_jf.json')
        artwork = scraper.scrape_artwork(in_data)
        # with open('data/artwork_scraper.json', 'w') as out:
        #     json.dump(artwork, out, indent=4, sort_keys=True)
        expected = load_data('artwork_scraper.json')
        self.assertEqual(expected, artwork)

    def test_movies(self):
        server = get_mock_server()
        scraper = MoviesScraper(server, debug_level=0)
        movies = scraper.scrape_movies(load_data('movies_jf.json').get('Items') or [])
        # with open('data/movies_scraper.json', 'w') as out:
        #     json.dump(movies, out, indent=4, sort_keys=True)
        expected = load_data('movies_scraper.json')
        self.assertEqual(expected, movies)

    def test_tvshows_seasons(self):
        server = get_mock_server()
        scraper = TvShowsScraper(server, debug_level=0)
        jf_seasons = load_data('seasons_jf.json').get('Items') or []
        seasons = scraper.scrape_seasons(jf_seasons)
        # with open('data/seasons_scraper.json', 'w') as out:
        #     json.dump(seasons, out, indent=4, sort_keys=True)
        expected = load_data('seasons_scraper.json')
        self.assertEqual(expected, seasons)

    def test_tvshows(self):
        server = get_mock_server()
        scraper = TvShowsScraper(server, debug_level=0)
        jf_shows = load_data('tvshows_jf.json').get('Items') or []
        jf_shows = [show for show in jf_shows if show['Name'] == 'Archer']
        jf_seasons = load_data('seasons_jf.json').get('Items') or []
        jf_seasons = seasons_by_series(jf_seasons)
        shows = scraper.scrape_shows(jf_shows, jf_seasons)
        # with open('data/tvshows_scraper.json', 'w') as out:
        #     json.dump(shows, out, indent=4, sort_keys=True)
        expected = load_data('tvshows_scraper.json')
        self.assertEqual(expected, shows)

    def test_tvshows_episodes(self):
        series_id = '7879d2c8a44a666d6846d4eea026ddd3'
        in_items = load_episodes_jf_by_series()[series_id]
        server = get_mock_server()
        scraper = TvShowsScraper(server, debug_level=0)
        episodes = scraper.scrape_episodes(in_items)
        # with open('data/episodes_scraper.json', 'w') as out:
        #     json.dump(episodes, out, indent=4, sort_keys=True)
        expected = load_data('episodes_scraper.json')
        self.assertEqual(expected, episodes)
