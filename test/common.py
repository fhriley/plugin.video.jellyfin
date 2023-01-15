import json
from pathlib import Path
from typing import Dict, Any, Optional
from unittest.mock import MagicMock, PropertyMock

from lib.api.jellyfin import Server, User, create_image_url

SERVER = 'http://server'
USER = 'user'
USER_ID = 'uuid'
USER_TOKEN = 'token'
PASS = 'pass'
CLIENT = 'client'
DEVICE = 'device'
DEVICE_ID = 'device_id'
VERSION = '1.0'
AUTH = f'MediaBrowser Client="{CLIENT}", Device="{DEVICE}", DeviceId="{DEVICE_ID}", Version="{VERSION}"'


def get_server(requests_api=None):
    return Server(requests_api, SERVER, CLIENT, DEVICE, DEVICE_ID, VERSION)


def get_mock_server(url: Optional[str] = 'http://server') -> Server:
    server = MagicMock(Server)
    type(server).server = PropertyMock(return_value=url)
    server.image_url = lambda item_id, image_type='Primary', **kwargs: create_image_url(server, item_id, image_type,
                                                                                        **kwargs)
    return server


def get_user():
    return User(USER, USER_ID, USER_TOKEN)


def get_data_path() -> Path:
    return Path(__file__).parent / 'data'


def load_data(file_name):
    json_file = get_data_path() / file_name
    with open(json_file, 'r') as in_file:
        return json.load(in_file)


def load_seasons_jf_by_series() -> Dict[str, Any]:
    by_series = {}
    for season in load_data('seasons_jf.json').get('Items') or []:
        seasons = by_series.setdefault(season['SeriesId'], [])
        seasons.append(season)
    return by_series


def load_episodes_jf_by_series() -> Dict[str, Any]:
    by_series = {}
    for episode in load_data('episodes_jf.json').get('Items') or []:
        episodes = by_series.setdefault(episode['SeriesId'], [])
        episodes.append(episode)
    return by_series


def load_episodes_scraper_by_series() -> Dict[str, Any]:
    by_series = {}
    for episode in load_data('episodes_scraper.json'):
        episodes = by_series.setdefault(episode['series_id'], [])
        episodes.append(episode)
    return by_series
