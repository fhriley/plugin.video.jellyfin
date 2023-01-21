import datetime
import logging
from typing import Optional, Dict, List, Any
from urllib.parse import urlencode, urlsplit, urlunsplit, urljoin

import requests


def seconds_to_ticks(seconds: float) -> int:
    return int(round(max(seconds, 0) * 1e7))


class User:
    def __init__(self, user: str, uuid: Optional[str] = None, token: Optional[str] = None):
        self._user = user
        self._uuid = uuid
        self._token = token

    @property
    def user(self) -> str:
        return self._user

    @property
    def uuid(self) -> str:
        return self._uuid

    @property
    def token(self) -> str:
        return self._token

    def __eq__(self, other) -> bool:
        return (self.user, self.uuid, self.token) == (other.user, other.uuid, other.token)

    def __str__(self) -> str:
        return f'User[user={self._user}, uuid={self._uuid}]'


class Server:
    def __init__(self, requests_api, server: str, client_name: str, device_name: str, device_id: str, version: str,
                 verify_cert: bool = True, timeout: float = 3, log_raw_resp: bool = False):
        self._server = server
        self._verify_cert = verify_cert
        self._device_id = device_id
        self._authorization = (
            f'MediaBrowser Client="{client_name}", Device="{device_name}", DeviceId="{device_id}", Version="{version}"')
        self._requests_api = requests_api
        self._timeout = timeout
        self._log_raw_resp = log_raw_resp
        self._log = logging.getLogger(__name__)
        parsed = urlsplit(self._server)
        scheme = 'ws'
        if parsed.scheme == 'https':
            scheme = 'wss'
        self._ws_server = urlunsplit((scheme, parsed.netloc, parsed.path, parsed.query, parsed.fragment))

    def get_headers(self, user: Optional[User] = None, headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        headers = headers or {}
        headers['x-emby-authorization'] = self._authorization
        if user:
            headers['x-mediabrowser-token'] = user.token
        return headers

    @property
    def server(self) -> str:
        return self._server

    def ws_url(self, user: User) -> str:
        return urljoin(self._ws_server, f'/socket?api_key={user.token}&device_id={self._device_id}')

    @property
    def authorization(self) -> str:
        return self._authorization

    def _method(self, requests_method, path: str, *args, user: Optional[User] = None, **kwargs) -> requests.Response:
        headers = self.get_headers(user, kwargs.get('headers'))
        timeout = kwargs.pop('timeout', self._timeout)
        response = requests_method(f'{self.server}{path}', *args, headers=headers, verify=self._verify_cert,
                                   timeout=timeout, **kwargs)
        if self._log_raw_resp:
            self._log.debug(repr(response.text))
        return response

    def post(self, path: str, *args, user: Optional[User] = None, **kwargs) -> requests.Response:
        return self._method(self._requests_api.post, path, *args, user=user, **kwargs)

    def get(self, path: str, *args, user: Optional[User] = None, **kwargs) -> requests.Response:
        return self._method(self._requests_api.get, path, *args, user=user, **kwargs)

    def head(self, path: str, *args, user: Optional[User] = None, **kwargs) -> requests.Response:
        return self._method(self._requests_api.head, path, *args, user=user, **kwargs)

    def delete(self, path: str, *args, user: Optional[User] = None, **kwargs) -> requests.Response:
        return self._method(self._requests_api.delete, path, *args, user=user, **kwargs)

    def authenticate_by_password(self, user: str, password: str) -> User:
        with self.post('/Users/AuthenticateByName', json={'Username': user, 'Pw': password}) as response:
            response.raise_for_status()
            data = response.json()
        token = data.get('AccessToken')
        if not token:
            raise Exception('Authentication failed')
        return User(data['User']['Name'], data['User']['Id'], token)

    def is_authenticated(self, user: User) -> bool:
        with self.get(f'/System/Info', user=user) as resp:
            return resp.status_code == 200

    def get_views(self, user: User, *args, **kwargs) -> List[Dict[str, Any]]:
        with self.get(f'/Users/{user.uuid}/Views', *args, user=user, **kwargs) as resp:
            resp.raise_for_status()
            return resp.json()['Items']

    def _get_items(self, user: User, *args, **kwargs) -> Dict[str, Any]:
        with self.get(f'/Users/{user.uuid}/Items', *args, user=user, **kwargs) as resp:
            resp.raise_for_status()
            data = resp.json()
            # with open('movies_jf.json', 'w') as out:
            #     import json
            #     json.dump(data, out, indent=4, sort_keys=True)
            return data

    def get_items(self, user: User, chunk_size: Optional[int] = 0, *args, **kwargs) -> Dict[str, Any]:
        if chunk_size <= 0:
            return self._get_items(user, *args, **kwargs)

        params = kwargs.pop('params', None) or {}
        params['Limit'] = chunk_size

        items = []
        start_index = 0
        while True:
            params['startIndex'] = start_index
            data = self._get_items(user, *args, params=params, **kwargs)
            iter_items = data['Items']
            iter_count = len(iter_items)

            items.extend(iter_items)
            total, start_index = data['TotalRecordCount'], data['StartIndex']
            if iter_count == 0 or len(items) >= total:
                break
            start_index += iter_count

        return {'Items': items, 'TotalRecordCount': len(items), 'StartIndex': 0}

    def get_item(self, user: User, item_id: str, *args, **kwargs) -> Dict[str, Any]:
        with self.get(f'/Users/{user.uuid}/Items/{item_id}', *args, user=user, **kwargs) as resp:
            resp.raise_for_status()
            return resp.json()

    def get_item_images(self, user: User, item_id: str, *args, **kwargs) -> List[Dict[str, str]]:
        with self.get(f'/Items/{item_id}/Images', *args, user=user, **kwargs) as resp:
            resp.raise_for_status()
            return resp.json()

    def get_seasons(self, user: User, series_id: Optional[str] = None, chunk_size: Optional[int] = 0, *args,
                    **kwargs) -> Dict[str, Any]:
        params = kwargs.pop('params', None) or {}
        if series_id:
            params['userId'] = user.uuid
            with self.get(f'/Shows/{series_id}/Seasons', *args, user=user, params=params, **kwargs) as resp:
                resp.raise_for_status()
                return resp.json()
        else:
            params['recursive'] = 'true'
            params['includeItemTypes'] = 'Season'
            seasons = self.get_items(user, *args, chunk_size=chunk_size, params=params, **kwargs)
            # with open('seasons_jf.json', 'w') as out:
            #     import json
            #     json.dump(seasons, out, indent=4, sort_keys=True)
            return seasons

    def get_episodes(self, user: User, series_id: Optional[str] = None, chunk_size: Optional[int] = 0, *args,
                     **kwargs) -> Dict[str, Any]:
        params = kwargs.pop('params', None) or {}
        if series_id:
            params['userId'] = user.uuid
            with self.get(f'/Shows/{series_id}/Episodes', *args, user=user, params=params, **kwargs) as resp:
                resp.raise_for_status()
                return resp.json()
        else:
            params['recursive'] = 'true'
            params['includeItemTypes'] = 'Episode'
            return self.get_items(user, *args, chunk_size=chunk_size, params=params, **kwargs)

    def get_episode(self, user: User, series_id: str, episode_id: str, *args, **kwargs) -> Optional[Dict[str, Any]]:
        params = kwargs.pop('params', None) or {}
        params['userId'] = user.uuid
        params['startItemId'] = episode_id
        params['limit'] = 1
        with self.get(f'/Shows/{series_id}/Episodes', *args, user=user, params=params, **kwargs) as resp:
            resp.raise_for_status()
            items = resp.json()['Items']
            if items:
                return items[0]
            return None

    def image_url_exists(self, url: str, **kwargs) -> bool:
        timeout = kwargs.pop('timeout', self._timeout)
        with self._requests_api.head(url, timeout=timeout) as resp:
            return resp.status_code == 200

    def image_url(self, item_id: str, image_type='Primary', **kwargs) -> str:
        return create_image_url(self, item_id, image_type, **kwargs)

    def get_sessions(self, user: User):
        params = {'ControllableByUserId': user.uuid}
        with self.get(f'/Sessions', user=user, params=params) as resp:
            resp.raise_for_status()
            return resp.json()

    def _playstate_data(self, item_id: str, position_s: Optional[float] = None):
        data = {
            'QueueableMediaTypes': 'Video',
            'CanSeek': True,
            'ItemId': item_id,
            'PlayMethod': 'DirectPlay',
        }
        if position_s is not None:
            data['PositionTicks'] = seconds_to_ticks(position_s)
        return data

    def send_playback_started(self, user: User, item_id: str, position_s: Optional[float] = None):
        data = self._playstate_data(item_id, position_s)
        with self.post('/Sessions/Playing', user=user, json=data) as response:
            response.raise_for_status()

    def send_playback_stopped(self, user: User, item_id: str, position_s: Optional[float] = None):
        data = self._playstate_data(item_id, position_s)
        with self.post('/Sessions/Playing/Stopped', user=user, json=data) as response:
            response.raise_for_status()

    def _send_playback_progress(self, user: User, data: dict):
        with self.post('/Sessions/Playing/Progress', user=user, json=data) as response:
            response.raise_for_status()

    def send_playback_time(self, user: User, item_id: str, position_s: float):
        data = self._playstate_data(item_id, position_s)
        self._send_playback_progress(user, data)

    def send_playback_paused(self, user: User, item_id: str, position_s: float):
        data = self._playstate_data(item_id, position_s)
        data['IsPaused'] = True
        self._send_playback_progress(user, data)

    def send_playback_unpaused(self, user: User, item_id: str, position_s: float):
        data = self._playstate_data(item_id, position_s)
        data['IsPaused'] = False
        self._send_playback_progress(user, data)

    def mark_watched(self, user: User, item_id: str):
        with self.post(f'/Users/{user.uuid}/PlayedItems/{item_id}', user=user) as response:
            response.raise_for_status()

    def mark_unwatched(self, user: User, item_id: str):
        with self.delete(f'/Users/{user.uuid}/PlayedItems/{item_id}', user=user) as response:
            response.raise_for_status()

    def get_sync_queue(self, user: User, last_updated: Optional[datetime.datetime] = None, *args, **kwargs) -> Dict[str, Any]:
        params = kwargs.pop('params', None) or {}
        params['filters'] = 'Movies,TvShows'
        if last_updated:
            params['lastUpdateDt'] = last_updated.strftime('%Y-%m-%dT%H:%M:%SZ')
        with self.get(f'/Jellyfin.Plugin.KodiSyncQueue/{user.uuid}/GetItems', *args, user=user, params=params, **kwargs) as resp:
            resp.raise_for_status()
            return resp.json()

    def get_server_time(self) -> datetime.datetime:
        with self.get('/Jellyfin.Plugin.KodiSyncQueue/GetServerDateTime') as resp:
            resp.raise_for_status()
            dt = resp.json()['ServerDateTime']
        return datetime.datetime.strptime(dt, '%Y-%m-%dT%H:%M:%SZ')

    def __str__(self) -> str:
        return f'Server[server={self.server}, authorization={self.authorization}]'


def create_image_url(server: Server, item_id: str, image_type='Primary', **kwargs) -> str:
    # /Items/30e61375a2dd864eaf4180717916f0c2/Images/Primary?fillHeight=651&fillWidth=434&quality=96&tag=c419dc7dbb3ed2d4b54d47958efa7811
    url = f'{server.server}/Items/{item_id}/Images/{image_type}'
    params = kwargs.get('params')
    if params:
        url = f'{url}?{urlencode(params)}'
    return url


def authenticate(server: Server, user_cache: Dict[str, User], username: str, password: str) -> User:
    user = user_cache.get(username)
    if not user or not server.is_authenticated(user):
        user = server.authenticate_by_password(username, password)
        user_cache[user.user] = user
    return user
