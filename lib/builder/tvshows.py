import logging
from typing import List, Dict, Any

import xbmc
import xbmcgui
import xbmcplugin

from lib.builder.base import Builder, set_common_tags, set_tag_if_have, get_url
from lib.util import util

_log = logging.getLogger(__name__)


class TvShowsBuilder(Builder):
    def _build_directory_set_list_item(self, list_item: xbmcgui.ListItem, item_id: str, jf_item: dict):
        # list_item.setContentLookup(False)
        pass

    def _build_directory_set_tags(self, tags: xbmc.InfoTagVideo, item_id: str, info: dict):
        set_tag_if_have(info, 'tvshowtitle', tags.setTvShowTitle)
        set_tag_if_have(info, 'status', tags.setTvShowStatus)
        set_tag_if_have(info, 'aired', tags.setFirstAired)
        seasons = info.get('seasons') or []
        for season in seasons:
            tags.addSeason(season['number'], season['name'])
            artwork = season.get('artwork')
            if artwork:
                tags.addAvailableArtwork(artwork['url'], artwork['type'], season=season['number'])
        # episode_guide = util.get_plugin_url(self._addon, id=item_id)
        # tags.setEpisodeGuide(episode_guide)

    def build_directory(self, items: List[Dict[str, Any]]):
        self._build_directory(items, 'tvshows')

    def build_show(self, jf_item: Dict[str, Any]):
        item_id = jf_item['id']
        info = jf_item['info']

        list_item = xbmcgui.ListItem(jf_item['name'], offscreen=True)

        tags = list_item.getVideoInfoTag()
        set_common_tags(tags, info, item_id)

        set_tag_if_have(info, 'tvshowtitle', tags.setTvShowTitle)
        set_tag_if_have(info, 'status', tags.setTvShowStatus)
        set_tag_if_have(info, 'aired', tags.setFirstAired)
        seasons = info.get('seasons') or []
        for season in seasons:
            artwork = season.get('artwork')
            if artwork:
                tags.addAvailableArtwork(artwork['url'], artwork['type'], season=season['number'])
        tags.setEpisodeGuide(util.get_plugin_url(self._addon, 'tvshows', id=item_id))

        xbmcplugin.setResolvedUrl(handle=self._handle, succeeded=True, listitem=list_item)

    def build_episodes_directory(self, episodes: List[Dict[str, Any]]):
        _log.debug('create_episodes')

        items = []
        is_folder = False

        for episode in episodes:
            episode_id = episode['id']
            info = episode['info']

            list_item = xbmcgui.ListItem(episode['name'], offscreen=True)
            tags = list_item.getVideoInfoTag()
            set_common_tags(tags, info, episode_id)

            set_tag_if_have(info, 'season', tags.setSeason)
            set_tag_if_have(info, 'episode', tags.setEpisode)
            set_tag_if_have(info, 'sortseason', tags.setSortSeason)
            set_tag_if_have(info, 'sortepisode', tags.setSortEpisode)
            set_tag_if_have(info, 'aired', tags.setFirstAired)

            url = get_url(self._addon, 'tvshows', id=episode_id)
            items.append((url, list_item, is_folder))

        xbmcplugin.setContent(handle=self._handle, content='episodes')
        xbmcplugin.addDirectoryItems(handle=self._handle, items=items)
        xbmcplugin.endOfDirectory(handle=self._handle, succeeded=True)

    def build_episode(self, episode: Dict[str, Any]):
        list_item = xbmcgui.ListItem(episode['name'], offscreen=True)
        tags = list_item.getVideoInfoTag()

        info = episode['info']
        set_common_tags(tags, info, episode['id'])

        set_tag_if_have(info, 'season', tags.setSeason)
        set_tag_if_have(info, 'episode', tags.setEpisode)
        set_tag_if_have(info, 'sortseason', tags.setSortSeason)
        set_tag_if_have(info, 'sortepisode', tags.setSortEpisode)
        set_tag_if_have(info, 'aired', tags.setFirstAired)

        xbmcplugin.setResolvedUrl(handle=self._handle, succeeded=True, listitem=list_item)
