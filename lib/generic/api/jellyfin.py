import logging
from typing import Optional, Dict, List, Any, Tuple
from urllib.parse import urlencode

import requests

_log = logging.getLogger(__name__)


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
        self._authorization = (
            f'MediaBrowser Client="{client_name}", Device="{device_name}", DeviceId="{device_id}", Version="{version}"')
        self._requests_api = requests_api
        self._timeout = timeout
        self._log_raw_resp = log_raw_resp

    def _get_headers(self, user: Optional[User] = None, headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        headers = headers or {}
        headers['x-emby-authorization'] = self._authorization
        if user:
            headers['x-mediabrowser-token'] = user.token
        return headers

    def _get_timeout(self, **kwargs) -> float:
        return kwargs.pop('timeout', self._timeout)

    @property
    def server(self) -> str:
        return self._server

    @property
    def authorization(self) -> str:
        return self._authorization

    def post(self, path: str, *args, user: Optional[User] = None, **kwargs) -> requests.Response:
        headers = self._get_headers(user, kwargs.get('headers'))
        response = self._requests_api.post(f'{self.server}{path}', *args, headers=headers, verify=self._verify_cert,
                                           timeout=self._get_timeout(), **kwargs)
        if self._log_raw_resp:
            _log.debug(repr(response.text))
        return response

    def get(self, path: str, *args, user: Optional[User] = None, **kwargs) -> requests.Response:
        headers = self._get_headers(user, kwargs.get('headers'))
        response = self._requests_api.get(f'{self.server}{path}', *args, headers=headers, verify=self._verify_cert,
                                          timeout=self._get_timeout(), **kwargs)
        if self._log_raw_resp:
            _log.debug(repr(response.text))
        return response

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

    def get_items(self, user: User, *args, **kwargs) -> Tuple[List[Dict[str, Any]], int, int]:
        with self.get(f'/Users/{user.uuid}/Items', *args, user=user, **kwargs) as resp:
            resp.raise_for_status()
            data = resp.json()
            return data['Items'], data['TotalRecordCount'], data['StartIndex']

    def get_item(self, user: User, item_id: str, *args, **kwargs) -> List[Dict[str, Any]]:
        with self.get(f'/Users/{user.uuid}/Items/{item_id}', *args, user=user, **kwargs) as resp:
            resp.raise_for_status()
            return resp.json()

    def get_item_images(self, user: User, item_id: str, *args, **kwargs) -> List[Dict[str, str]]:
        with self.get(f'/Items/{item_id}/Images', *args, user=user, **kwargs) as resp:
            resp.raise_for_status()
            return resp.json()

    def get_seasons(self, user: User, series_id: str, *args, **kwargs) -> List[Dict[str, Any]]:
        params = kwargs.pop('params', None) or {}
        params['userId'] = user.uuid
        with self.get(f'/Shows/{series_id}/Seasons', *args, user=user, params=params, **kwargs) as resp:
            resp.raise_for_status()
            return resp.json()['Items']

    def get_episodes(self, user: User, series_id: str, *args, **kwargs) -> List[Dict[str, Any]]:
        params = kwargs.pop('params', None) or {}
        params['userId'] = user.uuid
        with self.get(f'/Shows/{series_id}/Episodes', *args, user=user, params=params, **kwargs) as resp:
            resp.raise_for_status()
            return resp.json()['Items']

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

    def image_url_exists(self, url: str) -> bool:
        with self._requests_api.head(url, timeout=self._get_timeout()) as resp:
            return resp.status_code == 200

    def image_url(self, item_id: str, image_type='Primary', **kwargs) -> str:
        return create_image_url(self, item_id, image_type, **kwargs)

    def __str__(self) -> str:
        return f'Server[server={self.server}, authorization={self.authorization}]'


def create_image_url(server: Server, item_id: str, image_type='Primary', **kwargs) -> str:
    # /Items/30e61375a2dd864eaf4180717916f0c2/Images/Primary?fillHeight=651&fillWidth=434&quality=96&tag=c419dc7dbb3ed2d4b54d47958efa7811
    url = f'{server.server}/Items/{item_id}/Images/{image_type}'
    params = kwargs.get('params')
    if params:
        url = f'{url}?{urlencode(params)}'
    return url
