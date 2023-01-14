import logging
import tempfile
import unittest
from unittest.mock import patch, Mock, PropertyMock, MagicMock, call
from urllib.parse import quote

import simplejson as json
import xbmc
import xbmcaddon
import xbmcgui

from lib.addon.handlers.movie import MovieHandlers
from lib.addon.handlers.tvshow import TvShowHandlers
from lib.addon.log import LOG_FORMAT
from lib.addon.settings import Settings
from lib.addon.util import get_plugin_url
from lib.generic.api.jellyfin import Server, User, create_image_url
from lib.generic.scraper.tvshows import TvShowsScraper
from lib.test.common import (get_series_items_resp, get_series_seasons_resp, get_episodes_resp,
                             get_episode_resp, get_movie_items_search_resp, get_movie_items_details_resp)

logging.basicConfig(format=LOG_FORMAT, level=logging.INFO)


def get_addon_info(key):
    if key == 'id':
        return 'metadata.jellyfin.python'
    if key == 'version':
        return '1.0.0'
    raise Exception('unknown key: ' + key)


class TestEntrypoint(unittest.TestCase):
    @patch('lib.addon.handlers.base.xbmcgui')
    @patch('lib.addon.handlers.base.xbmcplugin')
    def test_movie_find(self, mock_xbmcplugin, mock_xbmcgui):
        with tempfile.TemporaryDirectory() as temp_dir:
            in_json = json.loads(get_movie_items_search_resp)
            settings = Mock(Settings)
            type(settings).profile_dir = PropertyMock(return_value=temp_dir)
            handle = 1
            params = {'action': 'find', 'title': 'planet of the apes', 'year': 1968}
            addon = Mock(xbmcaddon.Addon)
            addon.getAddonInfo = get_addon_info

            server = Mock(Server)
            server.get_items.return_value = in_json['Items'], in_json['TotalRecordCount'], in_json['StartIndex']
            server.authenticate_by_password.return_value = User('user', 'user_id', 'token')
            type(server).server = PropertyMock(return_value='http://server')
            server.image_url = lambda item_id, image_type='Primary', **kwargs: create_image_url(server, item_id,
                                                                                                image_type,
                                                                                                **kwargs)
            server.image_url_exists.return_value = True

            list_item = Mock(xbmcgui.ListItem)()
            mock_xbmcgui.ListItem.return_value = list_item

            handlers = MovieHandlers(settings, handle, params, addon, server)
            handlers.execute()

            mock_xbmcgui.ListItem.assert_called_once_with('Planet of the Apes (1968)')
            mock_xbmcplugin.addDirectoryItems.assert_called_once_with(handle=handle, items=[
                (
                    'plugin://metadata.jellyfin.python?id=ab54209a20679cd93ff9762aba1932a6&name=Planet+of+the+Apes+%281968%29',
                    list_item,
                    True
                )])
            mock_xbmcplugin.setResolvedUrl.assert_not_called()

    @patch('lib.addon.handlers.base.xbmc')
    @patch('lib.addon.handlers.base.xbmcgui')
    @patch('lib.addon.handlers.base.xbmcplugin')
    def test_movie_getdetails(self, mock_xbmcplugin, mock_xbmcgui, mock_xbmc):
        with tempfile.TemporaryDirectory() as temp_dir:
            in_json = json.loads(get_movie_items_details_resp)
            settings = Mock(Settings)
            type(settings).profile_dir = PropertyMock(return_value=temp_dir)
            handle = 1
            name = quote('Planet of the Apes (1968)')
            addon = Mock(xbmcaddon.Addon)
            addon.getAddonInfo = get_addon_info

            server = Mock(Server)
            server.get_items.return_value = in_json['Items'], in_json['TotalRecordCount'], in_json['StartIndex']
            server.authenticate_by_password.return_value = User('user', 'user_id', 'token')
            type(server).server = PropertyMock(return_value='http://server')
            server.image_url = lambda item_id, image_type='Primary', **kwargs: create_image_url(server, item_id,
                                                                                                image_type,
                                                                                                **kwargs)
            server.image_url_exists.return_value = True
            server.get_item_images.return_value = [{'ImageType': 'Banner'}, {'ImageType': 'Art'}, {'ImageType': 'Logo'},
                                                   {'ImageType': 'Primary'}, {'ImageType': 'Thumb'},
                                                   {'ImageType': 'Backdrop'}]

            params = {'action': 'getdetails', 'url': get_plugin_url(addon, id=in_json['Items'][0]["Id"], name=name)}

            list_item = Mock(xbmcgui.ListItem)()
            mock_xbmcgui.ListItem.return_value = list_item
            tags = MagicMock(xbmc.InfoTagVideo)()
            list_item.getVideoInfoTag.return_value = tags

            handlers = MovieHandlers(settings, handle, params, addon, server)
            handlers.execute()

            mock_xbmcgui.ListItem.assert_called_once_with('Planet%20of%20the%20Apes%20%281968%29', offscreen=True)
            tags.setUniqueIDs.assert_called_once_with({'tmdb': '871', 'imdb': 'tt0063442',
                                                       'jellyfin': 'plugin://metadata.jellyfin.python?id=ab54209a20679cd93ff9762aba1932a6'},
                                                      defaultuniqueid='jellyfin')
            tags.setYear.assert_called_once_with(1968)
            tags.setRating.assert_called_once_with(7.644)
            tags.setPlaycount.assert_called_once_with(2)
            tags.setMpaa.assert_called_once_with('G')
            tags.setPlot.assert_called_once_with(
                'Astronaut Taylor crash lands on a distant planet ruled by apes who use a primitive race of humans for experimentation and sport. Soon Taylor finds himself among the hunted, his life in the hands of a benevolent chimpanzee scientist.')
            tags.setPlotOutline.assert_called_once_with(
                'Astronaut Taylor crash lands on a distant planet ruled by apes who use a primitive race of humans for experimentation and sport. Soon Taylor finds himself among the hunted, his life in the hands of a benevolent chimpanzee scientist.')
            tags.setTitle.assert_called_once_with('Planet of the Apes')
            tags.setOriginalTitle.assert_called_once_with('Planet of the Apes')
            tags.setSortTitle.assert_not_called()
            tags.setTagLine.assert_called_once_with(
                'Somewhere in the Universe, there must be something better than man!')
            tags.setGenres.assert_called_once_with(['Science Fiction', 'Adventure', 'Drama', 'Action'])
            tags.setCountries.assert_not_called()
            tags.setDirectors.assert_called_once_with(['Franklin J. Schaffner'])
            tags.setStudios.assert_called_once_with(['20th Century Fox', 'APJAC Productions'])
            tags.setWriters.assert_called_once_with(['Pierre Boulle', 'Michael Wilson', 'Rod Serling'])
            tags.setDuration.assert_called_once_with(6724)
            tags.setPremiered.assert_called_once_with('1968-02-07')
            tags.setTags.assert_called_once_with(
                ['human evolution', 'gorilla', 'based on novel or book', 'bondage', 'space marine', 'chimp', 'slavery',
                 'space travel', 'time travel', 'dystopia', 'apocalypse', 'astronaut', 'ape', 'human subjugation'])
            tags.setLastPlayed.assert_called_once_with('2019-05-25 09:39:42')
            tags.setTrailer.assert_called_once_with('plugin://plugin.video.youtube/play/?video_id=BWh16oVpTBc')
            tags.setPath.assert_not_called()
            # tags.setPath.assert_called_once_with(
            #     'nfs://nas/zfs/media/movies/Planet of the Apes (1968)/Planet.of.the.Apes.1968.1080p.BDRemux.DTSHi-Res.H264.Rus.Eng.mkv')
            tags.setDateAdded.assert_called_once_with('2011-08-05 20:14:51')
            tags.setMediaType.assert_called_once_with('movie')
            tags.setCast.assert_called_once()
            actors = [call('Charlton Heston', 'George Taylor', -1,
                           'http://server/Items/30e61375a2dd864eaf4180717916f0c2/Images/Primary?tag=a40452bafb40f84f6ee10c4cc9c9d208'),
                      call('Roddy McDowall', 'Cornelius', 1,
                           'http://server/Items/7f7d8c971a1c0ee981429a750e2d4ca4/Images/Primary?tag=39bd5022cacf8cde3529d16365d6e6cf'),
                      call('Kim Hunter', 'Zira', 2, ''),
                      call('Maurice Evans', 'Dr. Zaius', 3,
                           'http://server/Items/1be71455211225e1bf6efaca3dd260b5/Images/Primary?tag=82481e706555666995b89612eb698e40'),
                      call('James Whitmore', 'President of the Assembly', 4, ''),
                      call('James Daly', 'Dr. Honorious', 5, ''),
                      call('Linda Harrison', 'Nova', 6, ''),
                      call('Robert Gunner', 'Landon', 7,
                           'http://server/Items/706c8ff18466148ab8e8088d6d09c4d8/Images/Primary?tag=377d4b47a3fb14401cb46bb5a505772f'),
                      call('Lou Wagner', 'Lucius', 8,
                           'http://server/Items/30ea764977ee47978e2c1d2d9ba0d1c0/Images/Primary?tag=3fe1fc7cb2d50780f88836c8e5d9db69'),
                      call('Woodrow Parfrey', 'Dr. Maximus', 9, ''),
                      call('Jeff Burton', 'Dodge', 10, ''),
                      call('Buck Kartalian', 'Julius', 11, ''),
                      call('Norman Burton', 'Hunt Leader', 12, ''),
                      call('Wright King', 'Dr. Galen', 13,
                           'http://server/Items/e8468f45e9ae81ffaeb0f13f36cd0f9e/Images/Primary?tag=a53d27853703c215a0f87cac5a23fc09'),
                      call('Paul Lambert', 'Minister', 14,
                           'http://server/Items/99b0e982952371e69474708e634fd788/Images/Primary?tag=2059734f9324a2f5b8219e2959bded28')]
            self.assertEqual(actors, mock_xbmc.Actor.call_args_list)
            artwork = [call(
                'http://server/Items/ab54209a20679cd93ff9762aba1932a6/Images/Primary?tag=0c0ba75b4100e2487c1a65dff8f3e593',
                'poster'),
                call(
                    'http://server/Items/ab54209a20679cd93ff9762aba1932a6/Images/Primary?tag=0c0ba75b4100e2487c1a65dff8f3e593',
                    'thumb'),
                call(
                    'http://server/Items/ab54209a20679cd93ff9762aba1932a6/Images/Logo?tag=9c5206e5746ddcc181f9d0cacf41eaa5',
                    'clearlogo'),
                call(
                    'http://server/Items/ab54209a20679cd93ff9762aba1932a6/Images/Thumb?tag=0e58c81764d013a2f81554970ba46473',
                    'landscape')]
            self.assertEqual(artwork, tags.addAvailableArtwork.call_args_list)
            video = [call(1920, 1080, 1.7777777777777777, 6724, 'h264', language='eng')]  # , hdrType='')]
            self.assertEqual(video, mock_xbmc.VideoStreamDetail.call_args_list)
            audio = [call(6, 'dts', 'rus'), call(6, 'ac3', 'rus'), call(2, 'ac3', 'rus'), call(6, 'dts', 'eng')]
            self.assertEqual(audio, mock_xbmc.AudioStreamDetail.call_args_list)
            mock_xbmcplugin.addDirectoryItems.assert_not_called()
            mock_xbmcplugin.setResolvedUrl.assert_called_once_with(handle=handle, succeeded=True, listitem=list_item)

    @patch('lib.addon.handlers.base.xbmc')
    @patch('lib.addon.handlers.base.xbmcgui')
    @patch('lib.addon.handlers.base.xbmcplugin')
    def test_tvshow_getdetails(self, mock_xbmcplugin, mock_xbmcgui, mock_xbmc):
        with tempfile.TemporaryDirectory() as temp_dir:
            in_json = json.loads(get_series_items_resp)
            seasons_json = json.loads(get_series_seasons_resp)['Items']
            settings = Mock(Settings)
            type(settings).profile_dir = PropertyMock(return_value=temp_dir)
            handle = 1
            name = quote('Survivor')
            addon = Mock(xbmcaddon.Addon)
            addon.getAddonInfo = get_addon_info

            server = Mock(Server)
            server.get_items.return_value = in_json['Items'], in_json['TotalRecordCount'], in_json['StartIndex']
            server.get_seasons.return_value = seasons_json
            server.authenticate_by_password.return_value = User('user', 'user_id', 'token')
            type(server).server = PropertyMock(return_value='http://server')
            server.image_url = lambda item_id, image_type='Primary', **kwargs: create_image_url(server, item_id,
                                                                                                image_type, **kwargs)
            server.image_url_exists.return_value = True
            server.get_item_images.return_value = [{'ImageType': 'Banner'}, {'ImageType': 'Art'}, {'ImageType': 'Logo'},
                                                   {'ImageType': 'Primary'}, {'ImageType': 'Thumb'},
                                                   {'ImageType': 'Backdrop'}]

            params = {'action': 'getdetails', 'url': get_plugin_url(addon, id=in_json['Items'][0]["Id"], name=name)}

            list_item = Mock(xbmcgui.ListItem)()
            mock_xbmcgui.ListItem.return_value = list_item
            tags = MagicMock(xbmc.InfoTagVideo)()
            list_item.getVideoInfoTag.return_value = tags

            handlers = TvShowHandlers(settings, handle, params, addon, server)
            handlers.execute()

            mock_xbmcgui.ListItem.assert_called_once_with('Survivor', offscreen=True)
            tags.setUniqueIDs.assert_called_once_with(
                {'tmdb': '14658', 'imdb': 'tt0239195',
                 'jellyfin': 'plugin://metadata.jellyfin.python?id=d3df2a7b25f148e6c5fa10516addd268'},
                defaultuniqueid='jellyfin')
            tags.setYear.assert_called_once_with(2000)
            tags.setRating.assert_called_once_with(7.4)
            tags.setPlaycount.assert_called_once_with(0)
            tags.setMpaa.assert_called_once_with('TV-PG')
            tags.setPlot.assert_called_once_with(
                'A reality show contest where sixteen or more castaways split between two or more “Tribes” are taken to a remote isolated location and are forced to live off the land with meager supplies for roughly 39 days. Frequent physical challenges are used to pit the tribes against each other for rewards, such as food or luxuries, or for “Immunity”, forcing the other tribe to attend “Tribal Council”, where they must vote off one of their players.')
            tags.setPlotOutline.assert_called_once_with(
                'A reality show contest where sixteen or more castaways split between two or more “Tribes” are taken to a remote isolated location and are forced to live off the land with meager supplies for roughly 39 days. Frequent physical challenges are used to pit the tribes against each other for rewards, such as food or luxuries, or for “Immunity”, forcing the other tribe to attend “Tribal Council”, where they must vote off one of their players.')
            tags.setTitle.assert_called_once_with('Survivor')
            tags.setOriginalTitle.assert_called_once_with('Survivor')
            tags.setSortTitle.assert_not_called()
            tags.setTagLine.assert_not_called()
            tags.setGenres.assert_called_once_with(['Reality'])
            tags.setCountries.assert_not_called()
            tags.setDirectors.assert_not_called()
            tags.setStudios.assert_not_called()
            tags.setWriters.assert_not_called()
            tags.setDuration.assert_called_once_with(2521)
            tags.setPremiered.assert_called_once_with('2000-05-31')
            tags.setTags.assert_called_once_with(
                ['competition', 'tribe', 'voting', 'survival competition', 'reality competition'])
            tags.setLastPlayed.assert_not_called()
            tags.setTrailer.assert_called_once_with('plugin://plugin.video.youtube/play/?video_id=BhKQBTJME5o')
            tags.setPath.assert_not_called()
            # tags.setPath.assert_called_once_with('nfs://nas/zfs/media/tv/Survivor (2000)')
            tags.setDateAdded.assert_called_once_with('2021-09-23 04:27:51')
            tags.setMediaType.assert_called_once_with('tvshow')
            tags.setCast.assert_called_once()
            actors = [call('Jeff Probst', 'Himself - Host', -1,
                           'http://server/Items/5e6dcba5298126498a80a1111483f132/Images/Primary?tag=32ecadca32225b1bf1c90861acefeb65')]
            self.assertEqual(actors, mock_xbmc.Actor.call_args_list)
            artwork = [call(
                'http://server/Items/d3df2a7b25f148e6c5fa10516addd268/Images/Primary?tag=d4ef84d7ac3694ea2d1fc0121b854b86',
                'poster'),
                call(
                    'http://server/Items/d3df2a7b25f148e6c5fa10516addd268/Images/Primary?tag=d4ef84d7ac3694ea2d1fc0121b854b86',
                    'thumb'),
                call(
                    'http://server/Items/d3df2a7b25f148e6c5fa10516addd268/Images/Logo?tag=62a9e385df4f157f265cf2bbd586bc17',
                    'clearlogo')]
            self.assertEqual(artwork, tags.addAvailableArtwork.call_args_list)
            mock_xbmcplugin.addDirectoryItems.assert_not_called()
            mock_xbmcplugin.setResolvedUrl.assert_called_once_with(handle=handle, succeeded=True, listitem=list_item)

    @patch('lib.addon.handlers.base.xbmcgui')
    @patch('lib.addon.handlers.base.xbmcplugin')
    def test_getartwork(self, mock_xbmcplugin, mock_xbmcgui):
        with tempfile.TemporaryDirectory() as temp_dir:
            in_json = json.loads(get_series_items_resp)

            settings = Mock(Settings)
            type(settings).profile_dir = PropertyMock(return_value=temp_dir)
            handle = 1
            params = {'action': 'getartwork', 'url': 'plugin://foo?id=ab54209a20679cd93ff9762aba1932a6'}
            addon = Mock(xbmcaddon.Addon)
            addon.getAddonInfo = get_addon_info

            server = Mock(Server)
            type(server).server = PropertyMock(return_value='http://server')
            server.image_url = lambda item_id, image_type='Primary', **kwargs: create_image_url(server, item_id,
                                                                                                image_type,
                                                                                                **kwargs)
            server.image_url_exists.return_value = True
            server.get_items.return_value = in_json['Items'], in_json['TotalRecordCount'], in_json['StartIndex']
            server.authenticate_by_password.return_value = User('user', 'user_id', 'token')

            list_item = Mock(xbmcgui.ListItem)()
            mock_xbmcgui.ListItem.return_value = list_item
            tags = MagicMock(xbmc.InfoTagVideo)()
            list_item.getVideoInfoTag.return_value = tags

            handlers = MovieHandlers(settings, handle, params, addon, server)
            handlers.execute()

            mock_xbmcgui.ListItem.assert_called_once_with('ab54209a20679cd93ff9762aba1932a6', offscreen=True)
            artwork = [call(
                'http://server/Items/d3df2a7b25f148e6c5fa10516addd268/Images/Primary?tag=d4ef84d7ac3694ea2d1fc0121b854b86',
                'poster'),
                call(
                    'http://server/Items/d3df2a7b25f148e6c5fa10516addd268/Images/Primary?tag=d4ef84d7ac3694ea2d1fc0121b854b86',
                    'thumb'),
                call(
                    'http://server/Items/d3df2a7b25f148e6c5fa10516addd268/Images/Logo?tag=62a9e385df4f157f265cf2bbd586bc17',
                    'clearlogo')]
            self.assertEqual(artwork, tags.addAvailableArtwork.call_args_list)
            mock_xbmcplugin.addDirectoryItems.assert_not_called()
            mock_xbmcplugin.setResolvedUrl.assert_called_once_with(handle=handle, succeeded=True, listitem=list_item)

    @patch('lib.addon.handlers.tvshow.xbmcgui')
    @patch('lib.addon.handlers.tvshow.xbmcplugin')
    @patch('lib.addon.handlers.base.xbmcplugin')
    def test_tvshow_getepisodelist(self, mock_base_xbmcplugin, mock_xbmcplugin, mock_xbmcgui):
        with tempfile.TemporaryDirectory() as temp_dir:
            series_input = json.loads(get_series_items_resp)['Items'][0]
            settings = Mock(Settings)
            type(settings).profile_dir = PropertyMock(return_value=temp_dir)
            handle = 1
            addon = Mock(xbmcaddon.Addon)
            addon.getAddonInfo = get_addon_info

            server = Mock(Server)
            server.get_episodes.return_value = json.loads(get_episodes_resp)['Items']
            server.authenticate_by_password.return_value = User('user', 'user_id', 'token')
            type(server).server = PropertyMock(return_value='http://server')
            server.image_url = lambda item_id, image_type='Primary', **kwargs: create_image_url(server, item_id,
                                                                                                image_type,
                                                                                                **kwargs)
            server.image_url_exists.return_value = True

            params = {'action': 'getepisodelist',
                      'url': get_plugin_url(addon, id=series_input["Id"], name=series_input['Name'])}

            list_item = Mock(xbmcgui.ListItem)()
            mock_xbmcgui.ListItem.return_value = list_item
            tags = MagicMock(xbmc.InfoTagVideo)()
            list_item.getVideoInfoTag.return_value = tags

            handlers = TvShowHandlers(settings, handle, params, addon, server)
            handlers.execute()

            self.assertEqual(14, list_item.getVideoInfoTag.call_count)

            episodes = [call(1), call(2), call(3), call(4), call(5), call(6), call(7), call(1), call(2), call(3),
                        call(4), call(5), call(6), call(7)]
            self.assertEqual(episodes, tags.setEpisode.call_args_list)

            first_aired = [call('2017-02-19'), call('2017-02-26'), call('2017-03-05'), call('2017-03-12'),
                           call('2017-03-19'), call('2017-03-26'), call('2017-04-02'), call('2019-06-09'),
                           call('2019-06-16'), call('2019-06-23'), call('2019-06-30'), call('2019-07-07'),
                           call('2019-07-14'), call('2019-07-21')]
            self.assertEqual(first_aired, tags.setFirstAired.call_args_list)

            seasons = [call(1), call(1), call(1), call(1), call(1), call(1), call(1), call(2), call(2), call(2),
                       call(2), call(2), call(2), call(2)]
            self.assertEqual(seasons, tags.setSeason.call_args_list)

            titles = [call("Somebody's Dead"), call('Serious Mothering'), call('Living the Dream'),
                      call('Push Comes to Shove'), call('Once Bitten'), call('Burning Love'),
                      call('You Get What You Need'), call('What Have They Done?'), call('Tell Tale Hearts'),
                      call('The End of the World'), call('She Knows'), call('Kill Me'), call('The Bad Mother'),
                      call('I Want to Know')]
            self.assertEqual(titles, tags.setTitle.call_args_list)

            years = [call(2017), call(2017), call(2017), call(2017), call(2017), call(2017), call(2017), call(2019),
                     call(2019), call(2019), call(2019), call(2019), call(2019), call(2019)]
            self.assertEqual(years, tags.setYear.call_args_list)

            mock_xbmcplugin.addDirectoryItems.assert_called_once_with(handle=handle, items=[
                (
                    'plugin://metadata.jellyfin.python?series_id=d3df2a7b25f148e6c5fa10516addd268&id=c29c66263b2a0448725436a72f1a6b7e',
                    list_item, False),
                (
                    'plugin://metadata.jellyfin.python?series_id=d3df2a7b25f148e6c5fa10516addd268&id=14e84db0725aa69a065b0684b7251395',
                    list_item, False),
                (
                    'plugin://metadata.jellyfin.python?series_id=d3df2a7b25f148e6c5fa10516addd268&id=53ca8bc476929a5f867940d994e3064b',
                    list_item, False),
                (
                    'plugin://metadata.jellyfin.python?series_id=d3df2a7b25f148e6c5fa10516addd268&id=7dca59c8ede641b175f50d0e940f096b',
                    list_item, False),
                (
                    'plugin://metadata.jellyfin.python?series_id=d3df2a7b25f148e6c5fa10516addd268&id=8ef50e38188d67facecd7b7b62183470',
                    list_item, False),
                (
                    'plugin://metadata.jellyfin.python?series_id=d3df2a7b25f148e6c5fa10516addd268&id=55bb918f9450b9ec02ac8cf147403d3d',
                    list_item, False),
                (
                    'plugin://metadata.jellyfin.python?series_id=d3df2a7b25f148e6c5fa10516addd268&id=0f6a173e0bb6f54172f74b959760fef1',
                    list_item, False),
                (
                    'plugin://metadata.jellyfin.python?series_id=d3df2a7b25f148e6c5fa10516addd268&id=bf172fae9d3de3971a56334cdd9f5638',
                    list_item, False),
                (
                    'plugin://metadata.jellyfin.python?series_id=d3df2a7b25f148e6c5fa10516addd268&id=0c73e3fc8be0e2bbea251f0e9962a447',
                    list_item, False),
                (
                    'plugin://metadata.jellyfin.python?series_id=d3df2a7b25f148e6c5fa10516addd268&id=57788502d8aae3c8f0139aa97a6f7521',
                    list_item, False),
                (
                    'plugin://metadata.jellyfin.python?series_id=d3df2a7b25f148e6c5fa10516addd268&id=ed5bc027ca1bc7e9c4a81e7c295858b2',
                    list_item, False),
                (
                    'plugin://metadata.jellyfin.python?series_id=d3df2a7b25f148e6c5fa10516addd268&id=cc4e1fc023ff9403a02619bdca164326',
                    list_item, False),
                (
                    'plugin://metadata.jellyfin.python?series_id=d3df2a7b25f148e6c5fa10516addd268&id=d0195f47cd163972f32a770ebcb40b8d',
                    list_item, False),
                (
                    'plugin://metadata.jellyfin.python?series_id=d3df2a7b25f148e6c5fa10516addd268&id=f92ecfd6fb9f8ce26d2da65a8a7d5347',
                    list_item, False
                )])
            mock_base_xbmcplugin.setResolvedUrl.assert_not_called()

    @patch('lib.addon.handlers.tvshow.xbmcgui')
    @patch('lib.addon.handlers.tvshow.xbmcplugin')
    @patch('lib.addon.handlers.base.xbmcplugin')
    @patch('lib.addon.handlers.base.xbmc')
    def test_tvshow_getepisodedetails(self, mock_base_xbmc, mock_base_xbmcplugin, mock_xbmcplugin, mock_xbmcgui):
        with tempfile.TemporaryDirectory() as temp_dir:
            series_input = json.loads(get_series_items_resp)['Items'][0]
            in_json = json.loads(get_episode_resp)['Items'][0]
            # pprint(in_json)
            settings = Mock(Settings)
            type(settings).profile_dir = PropertyMock(return_value=temp_dir)
            handle = 1
            addon = Mock(xbmcaddon.Addon)
            addon.getAddonInfo = get_addon_info

            server = Mock(Server)
            server.get_episode.return_value = in_json
            server.authenticate_by_password.return_value = User('user', 'user_id', 'token')
            type(server).server = PropertyMock(return_value='http://server')
            server.image_url = lambda item_id, image_type='Primary', **kwargs: create_image_url(server, item_id,
                                                                                                image_type,
                                                                                                **kwargs)
            server.image_url_exists.return_value = True
            server.get_item_images.return_value = [{'ImageType': 'Banner'}, {'ImageType': 'Art'}, {'ImageType': 'Logo'},
                                                   {'ImageType': 'Primary'}, {'ImageType': 'Thumb'},
                                                   {'ImageType': 'Backdrop'}]

            params = {'action': 'getepisodedetails',
                      'url': get_plugin_url(addon, series_id=series_input["Id"], id=in_json["Id"])}

            list_item = Mock(xbmcgui.ListItem)()
            mock_xbmcgui.ListItem.return_value = list_item
            tags = MagicMock(xbmc.InfoTagVideo)()
            list_item.getVideoInfoTag.return_value = tags

            handlers = TvShowHandlers(settings, handle, params, addon, server, debug_level=2)
            handlers.execute()

            mock_xbmcgui.ListItem.assert_called_once_with("Somebody's Dead", offscreen=True)
            tags.setUniqueIDs.assert_called_once_with(
                {'imdb': 'tt4766572',
                 'jellyfin': 'plugin://metadata.jellyfin.python?series_id=d3df2a7b25f148e6c5fa10516addd268&id=c29c66263b2a0448725436a72f1a6b7e'},
                defaultuniqueid='jellyfin')
            tags.setYear.assert_called_once_with(2017)
            tags.setRating.assert_called_once_with(7.6)
            tags.setPlaycount.assert_called_once_with(3)
            tags.setMpaa.assert_called_once_with('TV-MA')
            tags.setPlot.assert_called_once_with(
                'A suspicious death at a coastal elementary school draws attention to the frictions among three mothers and their families.')
            tags.setPlotOutline.assert_called_once_with(
                'A suspicious death at a coastal elementary school draws attention to the frictions among three mothers and their families.')
            tags.setTitle.assert_called_once_with("Somebody's Dead")
            tags.setOriginalTitle.assert_not_called()
            tags.setSortTitle.assert_not_called()
            tags.setTagLine.assert_not_called()
            tags.setGenres.assert_not_called()
            tags.setCountries.assert_not_called()
            tags.setDirectors.assert_called_once_with(['Jean-Marc Vallée'])
            tags.setStudios.assert_not_called()
            tags.setWriters.assert_called_once_with(['David E. Kelley'])
            tags.setDuration.assert_called_once_with(3070)
            tags.setPremiered.assert_called_once_with('2017-02-19')
            tags.setTags.assert_not_called()
            tags.setLastPlayed.assert_not_called()
            tags.setTrailer.assert_not_called()
            tags.setPath.assert_not_called()
            tags.setDateAdded.assert_called_once_with('2017-08-08 15:56:34')
            tags.setFirstAired.assert_called_once_with('2017-02-19')
            tags.setMediaType.assert_called_once_with('episode')
            tags.setResumePoint.assert_called_once_with(1013.04192, 3069.824)
            tags.setCast.assert_called_once()
            actors = [call('Cameron Crovetti', '', -1, ''),
                      call('Chloe Coleman', '', 1,
                           'http://server/Items/7433a3458d7273c335154131bffd1239/Images/Primary?tag=013bb6ff701743bb3c81814041813d58'),
                      call('Darby Camp', '', 2,
                           'http://server/Items/cb22ebcec96f1234f9a9225c71be7d68/Images/Primary?tag=c771f27f9cf2e1285bf58a47f291509e'),
                      call('David Monahan', '', 3, ''),
                      call('Gia Carides', '', 4, ''),
                      call('Hong Chau', '', 5,
                           'http://server/Items/5db5244b8f00e950206b8ad707dfb6a7/Images/Primary?tag=f55dc64600b82e5f04a92efb676d3632'),
                      call('Iain Armitage', '', 6,
                           'http://server/Items/107aa818b90db732c0fc9d1c67bbb7e4/Images/Primary?tag=9a5f5fd9faef9c84209df50205b28b6c'),
                      call('Ivy George', '', 7,
                           'http://server/Items/d066cce0adfc0f0376a020d0e497f2bf/Images/Primary?tag=5c60f575767bc1d68ffdcf4414d9a503'),
                      call('Joel Spence', '', 8, ''),
                      call('Joseph Cross', '', 9,
                           'http://server/Items/3773ec8adf3edcc803c65de38cde743a/Images/Primary?tag=f87ed6a508861d6b9796430a48f66d0d'),
                      call('Kathreen Khavari', '', 10, ''),
                      call('Kathryn Newton', '', 11,
                           'http://server/Items/ee99c45cc2a5f7aceebd3c2fd149a076/Images/Primary?tag=db01ae0f0c40cd45acfe49cc2f180bd6'),
                      call('Keisuke Hoashi', '', 12, ''),
                      call('Kelen Coleman', '', 13, ''),
                      call('Kimmy Shields', '', 14, ''),
                      call('Larry Bates', '', 15, ''),
                      call('Larry Sullivan', '', 16, ''),
                      call('Merrin Dungey', '', 17, ''),
                      call('P.J. Byrne', '', 18, ''),
                      call('Parker Croft', '', 19, ''),
                      call('Santiago Cabrera', '', 20,
                           'http://server/Items/22082f0fe135f345aa0659c866c36ae4/Images/Primary?tag=741246387959bd954534f187858bed46'),
                      call('Sarah Baker', '', 21, ''),
                      call('Sarah Burns', '', 22,
                           'http://server/Items/de546a959ddf4ec1af800783d80445a8/Images/Primary?tag=899399d24e670fa49a91620d27058b89'),
                      call('Sarah Sokolovic', '', 23,
                           'http://server/Items/451109bb07fbc6bd6a6aa148e7e45f23/Images/Primary?tag=6edbeb7761e48db6affbb13b5d63e2a1'),
                      call('Tim True', '', 24, ''),
                      call('Virginia Kull', '', 25, ''),
                      call('Carrie Wampler', '', 26, '')]
            self.assertEqual(actors, mock_base_xbmc.Actor.call_args_list)
            artwork = [call(
                'http://server/Items/c29c66263b2a0448725436a72f1a6b7e/Images/Primary?tag=2587e0e4f605b32429781de875bbe559',
                'thumb')]
            self.assertEqual(artwork, tags.addAvailableArtwork.call_args_list)
            video = [call(1920, 1080, 1.7777777777777777, 3070, 'h264', language='eng')]  # , hdrType='')]
            self.assertEqual(video, mock_base_xbmc.VideoStreamDetail.call_args_list)
            self.assertEqual([call(6, 'dts', 'eng')], mock_base_xbmc.AudioStreamDetail.call_args_list)

            mock_xbmcplugin.addDirectoryItems.assert_not_called()
            mock_base_xbmcplugin.setResolvedUrl.assert_called_once_with(handle=handle, succeeded=True,
                                                                        listitem=list_item)

    @patch('lib.addon.handlers.tvshow.xbmcgui')
    @patch('lib.addon.handlers.tvshow.xbmcplugin')
    @patch('lib.addon.handlers.base.xbmcplugin')
    @patch('lib.addon.handlers.base.xbmc')
    def test_tvshow_items(self, mock_base_xbmc, mock_base_xbmcplugin, mock_xbmcplugin, mock_xbmcgui):
        with tempfile.TemporaryDirectory() as temp_dir:
            in_json = json.loads(get_episode_resp)
            seasons_json = json.loads(get_series_seasons_resp)['Items']
            episodes_json = json.loads(get_episodes_resp)['Items']
            # pprint(in_json)
            settings = Mock(Settings)
            type(settings).profile_dir = PropertyMock(return_value=temp_dir)
            handle = 1
            addon = Mock(xbmcaddon.Addon)
            addon.getAddonInfo = get_addon_info

            server = Mock(Server)
            server.get_items.return_value = in_json['Items'], in_json['TotalRecordCount'], in_json['StartIndex']
            server.get_seasons.return_value = seasons_json
            server.get_episodes.return_value = episodes_json
            user = User('user', 'user_id', 'token')
            server.authenticate_by_password.return_value = user
            type(server).server = PropertyMock(return_value='http://server')
            server.image_url = lambda item_id, image_type='Primary', **kwargs: create_image_url(server, item_id,
                                                                                                image_type,
                                                                                                **kwargs)
            server.get_item_images.return_value = [{'ImageType': 'Banner'}, {'ImageType': 'Art'}, {'ImageType': 'Logo'},
                                                   {'ImageType': 'Primary'}, {'ImageType': 'Thumb'},
                                                   {'ImageType': 'Backdrop'}]

            list_item = Mock(xbmcgui.ListItem)()
            mock_xbmcgui.ListItem.return_value = list_item
            tags = MagicMock(xbmc.InfoTagVideo)()
            list_item.getVideoInfoTag.return_value = tags

            scraper = TvShowsScraper(server, debug_level=0)
            handlers = TvShowHandlers(settings, handle, None, addon, server, debug_level=2)

            shows = scraper.get_items(user)
            handlers.create_items_directory(shows)

            seasons = scraper.get_seasons(user, shows[0]['id'])
            handlers.create_seasons(seasons)

            episodes = scraper.get_episodes(user, shows[0]['id'], seasons[0]['id'])
            handlers.create_episodes(episodes)
