import logging
import tempfile
import unittest
from unittest.mock import Mock, PropertyMock

import simplejson as json

from lib.addon.log import LOG_FORMAT
from lib.generic.api.jellyfin import create_image_url, Server, User
from lib.generic.scraper.base import get_people, Scraper
from lib.generic.scraper.movies import MoviesScraper
from lib.test.common import get_movie_items_search_resp, get_movie_items_details_resp, get_server_mock, get_user

logging.basicConfig(format=LOG_FORMAT, level=logging.INFO)


class TestScraper(unittest.TestCase):
    def test_authenticate(self):
        server = Mock(Server)
        password = 'password'
        expected_user = User('user', 'user_id', 'token')
        server.authenticate_by_password.return_value = expected_user
        type(server).server = PropertyMock(return_value='http://server')

        scraper = Scraper(server, debug_level=0)
        server.is_authenticated.return_value = False
        user = scraper.authenticate(expected_user.user, password)
        server.authenticate_by_password.assert_called_once_with(expected_user.user, password)
        self.assertEqual(expected_user, user)

        server.is_authenticated.return_value = True
        user = scraper.authenticate(expected_user.user, password)
        server.authenticate_by_password.assert_called_once()
        self.assertEqual(expected_user, user)

    def test_authenticate_cached(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            password = 'password'
            expected_user = User('user', 'user_id', 'token')

            server = Mock(Server)
            server.authenticate_by_password.return_value = expected_user
            type(server).server = PropertyMock(return_value='http://server')

            scraper = Scraper(server, debug_level=0, cache_dir=temp_dir)
            server.is_authenticated.return_value = False
            user = scraper.authenticate(expected_user.user, password)
            server.authenticate_by_password.assert_called_once_with(expected_user.user, password)
            self.assertEqual(expected_user, user)

            scraper = Scraper(server, debug_level=0, cache_dir=temp_dir)
            server.is_authenticated.return_value = True
            user = scraper.authenticate(expected_user.user, password)
            server.authenticate_by_password.assert_called_once()
            self.assertEqual(expected_user, user)

            scraper = Scraper(server, debug_level=0, cache_dir=temp_dir)
            server.is_authenticated.return_value = False
            user = scraper.authenticate(expected_user.user, password)
            server.authenticate_by_password.assert_called_with(expected_user.user, password)
            self.assertEqual(expected_user, user)

    def test_search_by_title(self):
        in_json = json.loads(get_movie_items_search_resp)

        server = get_server_mock()
        server.get_items.return_value = in_json['Items'], in_json['TotalRecordCount'], in_json['StartIndex']
        user = get_user()

        scraper = MoviesScraper(server, debug_level=0)
        movies = scraper.search_by_title(user, 'planet of the apes', 1968)
        self.assertEqual(len(movies), 1)
        movie = movies[0]
        self.assertEqual(movie['id'], 'ab54209a20679cd93ff9762aba1932a6')
        self.assertEqual(movie['name'], 'Planet of the Apes (1968)')

    def test_movies_get_people(self):
        in_json = json.loads(get_movie_items_details_resp)['Items']
        server = Mock(Server)
        type(server).server = PropertyMock(return_value='http://server')
        server.image_url = lambda item_id, image_type='Primary', **kwargs: create_image_url(server, item_id, image_type,
                                                                                            **kwargs)
        server.image_url_exists.return_value = True
        server.get_item_images.return_value = [{'ImageType': 'Banner'}, {'ImageType': 'Art'}, {'ImageType': 'Logo'},
                                               {'ImageType': 'Primary'}, {'ImageType': 'Thumb'},
                                               {'ImageType': 'Backdrop'}]

        cast, directors, writers = get_people(server, in_json[0])
        self.assertEqual(len(cast), 15)
        self.assertEqual(len(directors), 1)
        self.assertEqual(len(writers), 3)
        # TODO: add checks

    def test_movies_get_artwork(self):
        in_json = json.loads(get_movie_items_search_resp)

        server = Mock(Server)
        type(server).server = PropertyMock(return_value='http://server')
        server.image_url = lambda item_id, image_type='Primary', **kwargs: create_image_url(server, item_id, image_type,
                                                                                            **kwargs)
        server.image_url_exists.return_value = True
        server.get_items.return_value = in_json['Items'], in_json['TotalRecordCount'], in_json['StartIndex']

        user = get_user()
        in_json = json.loads(get_movie_items_details_resp)['Items']

        scraper = MoviesScraper(server, debug_level=0)
        artwork = scraper.get_artwork(user, in_json[0]['Id'])

        self.assertEqual(
            {
                'poster': 'http://server/Items/ab54209a20679cd93ff9762aba1932a6/Images/Primary?tag=0c0ba75b4100e2487c1a65dff8f3e593',
                'thumb': 'http://server/Items/ab54209a20679cd93ff9762aba1932a6/Images/Primary?tag=0c0ba75b4100e2487c1a65dff8f3e593',
                'clearlogo': 'http://server/Items/ab54209a20679cd93ff9762aba1932a6/Images/Logo?tag=9c5206e5746ddcc181f9d0cacf41eaa5',
                'landscape': 'http://server/Items/ab54209a20679cd93ff9762aba1932a6/Images/Thumb?tag=0e58c81764d013a2f81554970ba46473'
            },
            artwork)

    def test_movies_get_by_id(self):
        server = Mock(Server)
        type(server).server = PropertyMock(return_value='http://server')
        server.image_url = lambda item_id, image_type='Primary', **kwargs: create_image_url(server, item_id, image_type,
                                                                                            **kwargs)
        server.image_url_exists.return_value = True
        server.get_item_images.return_value = [{'ImageType': 'Banner'}, {'ImageType': 'Art'}, {'ImageType': 'Logo'},
                                               {'ImageType': 'Primary'}, {'ImageType': 'Thumb'},
                                               {'ImageType': 'Backdrop'}]

        user = get_user()
        in_json = json.loads(get_movie_items_details_resp)
        server.get_items.return_value = in_json['Items'], in_json['TotalRecordCount'], in_json['StartIndex']

        scraper = MoviesScraper(server, debug_level=0)
        movie_id = 'ce7474bbfea22f7a710f6a404be7ef63'
        movie = scraper.get_by_id(user, movie_id)

        # from pprint import pprint
        # pprint(in_json[0])
        # pprint(movie)

        expected = {
            'name': 'Planet of the Apes (1968)',
            'id': 'ab54209a20679cd93ff9762aba1932a6',
        }

        expected_info = {
            'dateadded': '2011-08-05 20:14:51', 'duration': 6724,
            'genre': ['Science Fiction', 'Adventure', 'Drama', 'Action'],
            'lastplayed': '2019-05-25 09:39:42',
            'mediatype': 'movie',
            'mpaa': 'G',
            'originaltitle': 'Planet of the Apes',
            'path': 'nfs://nas/zfs/media/movies/Planet of the Apes '
                    '(1968)/Planet.of.the.Apes.1968.1080p.BDRemux.DTSHi-Res.H264.Rus.Eng.mkv',
            'playcount': 2,
            'plot': 'Astronaut Taylor crash lands on a distant planet ruled by '
                    'apes who use a primitive race of humans for experimentation '
                    'and sport. Soon Taylor finds himself among the hunted, his '
                    'life in the hands of a benevolent chimpanzee scientist.',
            'plotoutline': 'Astronaut Taylor crash lands on a distant planet '
                           'ruled by apes who use a primitive race of humans for '
                           'experimentation and sport. Soon Taylor finds himself '
                           'among the hunted, his life in the hands of a '
                           'benevolent chimpanzee scientist.',
            'premiered': '1968-02-07',
            'rating': 7.644,
            'tag': ['human evolution',
                    'gorilla',
                    'based on novel or book',
                    'bondage',
                    'space marine',
                    'chimp',
                    'slavery',
                    'space travel',
                    'time travel',
                    'dystopia',
                    'apocalypse',
                    'astronaut',
                    'ape',
                    'human subjugation'],
            'tagline': 'Somewhere in the Universe, there must be something '
                       'better than man!',
            'title': 'Planet of the Apes',
            'trailer': 'plugin://plugin.video.youtube/play/?video_id=BWh16oVpTBc',
            'year': 1968,
            'unique_ids': {'imdb': 'tt0063442', 'tmdb': '871'},
        }

        for key, val in expected.items():
            self.assertEqual(movie[key], val)

        info = movie['info']
        for key, val in expected_info.items():
            self.assertEqual(info[key], val)
