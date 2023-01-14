import unittest
from unittest.mock import Mock, MagicMock

import requests

from lib.generic.api.jellyfin import User
from test.common import get_server, SERVER, USER, USER_ID, USER_TOKEN, PASS, AUTH


class TestServer(unittest.TestCase):
    def test_create_image_url(self):
        mock = MagicMock(requests.Session)
        server = get_server(mock)
        image_id = '123'
        url = server.image_url(image_id)
        self.assertEqual(url, f'{SERVER}/Items/{image_id}/Images/Primary')

    def test_authenticate_by_password(self):
        resp_mock = MagicMock(requests.Response)
        resp_mock.json.return_value = {'User': {'Name': USER, 'Id': USER_ID}, 'AccessToken': USER_TOKEN}
        mock = Mock(requests.Session)
        mock.post.return_value = resp_mock

        server = get_server(mock)
        user = server.authenticate_by_password(USER, PASS)

        mock.post.assert_called_once_with(f'{SERVER}/Users/AuthenticateByName', headers={'x-emby-authorization': AUTH},
                                          verify=True, timeout=3, json={'Username': USER, 'Pw': PASS})
        self.assertEqual(user.user, USER)
        self.assertEqual(user.uuid, 'uuid')
        self.assertEqual(user.token, 'token')

    def test_get_users(self):
        resp_mock = MagicMock(requests.Response)
        resp_mock.json.return_value = [{'Name': USER, 'Id': USER_ID}]
        mock = Mock(requests.Session)
        mock.get.return_value = resp_mock

        server = get_server(mock)
        user = User('user', 'uuid', 'token')
        resp = server.get('/Users', user=user)
        data = resp.json()

        mock.get.assert_called_once_with(f'{SERVER}/Users',
                                         headers={'x-emby-authorization': AUTH, 'x-mediabrowser-token': USER_TOKEN},
                                         timeout=3, verify=True)

        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['Name'], USER)
        self.assertEqual(data[0]['Id'], USER_ID)
