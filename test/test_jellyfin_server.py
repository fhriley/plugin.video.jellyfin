import unittest
from unittest.mock import MagicMock, patch

import requests

from lib.api.jellyfin import User
from test.common import get_server, SERVER, USER, USER_ID, USER_TOKEN, PASS, AUTH


class TestServer(unittest.TestCase):
    @patch('lib.api.jellyfin.requests')
    def test_create_image_url(self, mock_requests):
        server = get_server(mock_requests)
        image_id = '123'
        url = server.image_url(image_id)
        self.assertEqual(url, f'{SERVER}/Items/{image_id}/Images/Primary')

    @patch('lib.api.jellyfin.requests')
    def test_authenticate_by_password(self, mock_requests):
        mock_requests.Response = MagicMock(requests.Response)
        mock_requests.Response.__enter__.return_value = mock_requests.Response
        mock_requests.Response.json.return_value = {'User': {'Name': USER, 'Id': USER_ID}, 'AccessToken': USER_TOKEN}
        mock_requests.post.return_value = mock_requests.Response

        server = get_server(mock_requests)
        user = server.authenticate_by_password(USER, PASS)

        mock_requests.post.assert_called_once_with(f'{SERVER}/Users/AuthenticateByName',
                                                   headers={'x-emby-authorization': AUTH},
                                                   verify=True, timeout=3, json={'Username': USER, 'Pw': PASS})
        self.assertEqual(user.user, USER)
        self.assertEqual(user.uuid, 'uuid')
        self.assertEqual(user.token, 'token')

    @patch('lib.api.jellyfin.requests')
    def test_get_call(self, mock_requests):
        mock_requests.Response = MagicMock(requests.Response)
        mock_requests.Response.__enter__.return_value = mock_requests.Response
        mock_requests.Response.json.return_value = [{'Name': USER, 'Id': USER_ID}]
        mock_requests.get.return_value = mock_requests.Response

        server = get_server(mock_requests)
        user = User('user', 'uuid', 'token')
        resp = server.get('/Users', user=user)
        data = resp.json()

        mock_requests.get.assert_called_once_with(f'{SERVER}/Users',
                                                  headers={'x-emby-authorization': AUTH,
                                                           'x-mediabrowser-token': USER_TOKEN},
                                                  timeout=3, verify=True)

        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['Name'], USER)
        self.assertEqual(data[0]['Id'], USER_ID)
