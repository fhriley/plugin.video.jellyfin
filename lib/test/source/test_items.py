import unittest
from unittest.mock import patch, Mock, PropertyMock, call

import simplejson as json
import xbmcaddon
import xbmcgui

from lib.generic.api.jellyfin import Server, User
from lib.source.items import get_tvshows, get_seasons, get_episodes
from lib.test.common import get_series_items_resp, get_series_seasons_resp, get_episodes_resp


class TestItems(unittest.TestCase):
    @patch('lib.source.items.xbmcgui')
    @patch('lib.source.items.xbmcplugin')
    def test_get_tvshows(self, mock_xbmcplugin, mock_xbmcgui):
        in_json = json.loads(get_series_items_resp)
        handle = 1
        user = User('user', 'user_id', 'token')

        addon = Mock(xbmcaddon.Addon)
        addon.getAddonInfo.return_value = 'addon'
        server = Mock(Server)
        server.get_items.return_value = in_json['Items'], in_json['TotalRecordCount'], in_json['StartIndex']
        server.authenticate_by_password.return_value = user
        type(server).server = PropertyMock(return_value='http://server')

        list_item = Mock(xbmcgui.ListItem)()
        mock_xbmcgui.ListItem.return_value = list_item

        get_tvshows(handle, addon, server, user, debug_level=0)

        mock_xbmcgui.ListItem.assert_called_once_with('Survivor (2000)')
        mock_xbmcplugin.setContent.assert_called_once_with(handle=1, content='tvshows')
        mock_xbmcplugin.addDirectoryItems.assert_called_once_with(handle=1, items=[
            ('plugin://addon/library/tvshows/d3df2a7b25f148e6c5fa10516addd268', list_item, True)])
        mock_xbmcplugin.endOfDirectory.assert_called_once_with(handle=1, succeeded=True)

    @patch('lib.source.items.xbmcgui')
    @patch('lib.source.items.xbmcplugin')
    def test_get_seasons(self, mock_xbmcplugin, mock_xbmcgui):
        in_json = json.loads(get_series_seasons_resp)
        handle = 1
        user = User('user', 'user_id', 'token')

        addon = Mock(xbmcaddon.Addon)
        addon.getAddonInfo.return_value = 'addon'
        server = Mock(Server)
        server.get_seasons.return_value = in_json['Items']
        server.authenticate_by_password.return_value = user
        type(server).server = PropertyMock(return_value='http://server')

        list_item = Mock(xbmcgui.ListItem)()
        mock_xbmcgui.ListItem.return_value = list_item

        get_seasons(handle, addon, server, user, 'd3df2a7b25f148e6c5fa10516addd268', debug_level=0)

        self.assertEqual([call('Season 41'), call('Season 42'), call('Season 43')],
                         mock_xbmcgui.ListItem.call_args_list)
        mock_xbmcplugin.setContent.assert_not_called()
        self.assertEqual([call(handle=1, items=[
            ('plugin://addon/library/tvshows/d3df2a7b25f148e6c5fa10516addd268/f28c0a87ff9f69be779a6b3a66b82a17',
             list_item, True),
            ('plugin://addon/library/tvshows/d3df2a7b25f148e6c5fa10516addd268/3cfa0f3b16fe1e48e61194f7b96f42b8',
             list_item, True),
            ('plugin://addon/library/tvshows/d3df2a7b25f148e6c5fa10516addd268/59c44cc6b1a73c281aadd3c47fd09986',
             list_item, True)])], mock_xbmcplugin.addDirectoryItems.call_args_list)
        mock_xbmcplugin.endOfDirectory.assert_called_once_with(handle=1, succeeded=True)

    @patch('lib.source.items.xbmcgui')
    @patch('lib.source.items.xbmcplugin')
    def test_get_episodes(self, mock_xbmcplugin, mock_xbmcgui):
        in_json = json.loads(get_episodes_resp)
        handle = 1
        user = User('user', 'user_id', 'token')

        addon = Mock(xbmcaddon.Addon)
        addon.getAddonInfo.return_value = 'addon'
        server = Mock(Server)
        server.get_episodes.return_value = in_json['Items']
        server.authenticate_by_password.return_value = user
        type(server).server = PropertyMock(return_value='http://server')

        list_item = Mock(xbmcgui.ListItem)()
        mock_xbmcgui.ListItem.return_value = list_item

        get_episodes(handle, addon, server, user, 'd3df2a7b25f148e6c5fa10516addd268',
                     '59c44cc6b1a73c281aadd3c47fd09986', debug_level=0)

        self.assertEqual([call("Somebody's Dead"),
                          call('Serious Mothering'),
                          call('Living the Dream'),
                          call('Push Comes to Shove'),
                          call('Once Bitten'),
                          call('Burning Love'),
                          call('You Get What You Need'),
                          call('What Have They Done?'),
                          call('Tell Tale Hearts'),
                          call('The End of the World'),
                          call('She Knows'),
                          call('Kill Me'),
                          call('The Bad Mother'),
                          call('I Want to Know')],
                         mock_xbmcgui.ListItem.call_args_list)
        mock_xbmcplugin.setContent.assert_called_once_with(handle=1, content='episodes')
        self.assertEqual([call(handle=1, items=[
            (
                'plugin://addon/library/tvshows/d3df2a7b25f148e6c5fa10516addd268/59c44cc6b1a73c281aadd3c47fd09986/c29c66263b2a0448725436a72f1a6b7e',
                list_item, False), (
                'plugin://addon/library/tvshows/d3df2a7b25f148e6c5fa10516addd268/59c44cc6b1a73c281aadd3c47fd09986/14e84db0725aa69a065b0684b7251395',
                list_item, False), (
                'plugin://addon/library/tvshows/d3df2a7b25f148e6c5fa10516addd268/59c44cc6b1a73c281aadd3c47fd09986/53ca8bc476929a5f867940d994e3064b',
                list_item, False), (
                'plugin://addon/library/tvshows/d3df2a7b25f148e6c5fa10516addd268/59c44cc6b1a73c281aadd3c47fd09986/7dca59c8ede641b175f50d0e940f096b',
                list_item, False), (
                'plugin://addon/library/tvshows/d3df2a7b25f148e6c5fa10516addd268/59c44cc6b1a73c281aadd3c47fd09986/8ef50e38188d67facecd7b7b62183470',
                list_item, False), (
                'plugin://addon/library/tvshows/d3df2a7b25f148e6c5fa10516addd268/59c44cc6b1a73c281aadd3c47fd09986/55bb918f9450b9ec02ac8cf147403d3d',
                list_item, False), (
                'plugin://addon/library/tvshows/d3df2a7b25f148e6c5fa10516addd268/59c44cc6b1a73c281aadd3c47fd09986/0f6a173e0bb6f54172f74b959760fef1',
                list_item, False), (
                'plugin://addon/library/tvshows/d3df2a7b25f148e6c5fa10516addd268/59c44cc6b1a73c281aadd3c47fd09986/bf172fae9d3de3971a56334cdd9f5638',
                list_item, False), (
                'plugin://addon/library/tvshows/d3df2a7b25f148e6c5fa10516addd268/59c44cc6b1a73c281aadd3c47fd09986/0c73e3fc8be0e2bbea251f0e9962a447',
                list_item, False), (
                'plugin://addon/library/tvshows/d3df2a7b25f148e6c5fa10516addd268/59c44cc6b1a73c281aadd3c47fd09986/57788502d8aae3c8f0139aa97a6f7521',
                list_item, False), (
                'plugin://addon/library/tvshows/d3df2a7b25f148e6c5fa10516addd268/59c44cc6b1a73c281aadd3c47fd09986/ed5bc027ca1bc7e9c4a81e7c295858b2',
                list_item, False), (
                'plugin://addon/library/tvshows/d3df2a7b25f148e6c5fa10516addd268/59c44cc6b1a73c281aadd3c47fd09986/cc4e1fc023ff9403a02619bdca164326',
                list_item, False), (
                'plugin://addon/library/tvshows/d3df2a7b25f148e6c5fa10516addd268/59c44cc6b1a73c281aadd3c47fd09986/d0195f47cd163972f32a770ebcb40b8d',
                list_item, False), (
                'plugin://addon/library/tvshows/d3df2a7b25f148e6c5fa10516addd268/59c44cc6b1a73c281aadd3c47fd09986/f92ecfd6fb9f8ce26d2da65a8a7d5347',
                list_item, False)])],
                         mock_xbmcplugin.addDirectoryItems.call_args_list)
        mock_xbmcplugin.endOfDirectory.assert_called_once_with(handle=1, succeeded=True)
