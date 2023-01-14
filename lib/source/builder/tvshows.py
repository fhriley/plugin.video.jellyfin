import logging
from typing import List, Dict, Any

import xbmc
import xbmcgui
import xbmcplugin

from lib.source import util
from lib.source.builder.base import Builder, set_common_tags, set_tag_if_have, get_url

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

    def build_episodes(self, episodes: List[Dict[str, Any]]):
        succeeded = False
        try:
            _log.debug('create_episodes')

            items = []
            is_folder = False

            for episode in episodes:
                series_id = episode['series_id']
                season_id = episode['season_id']
                episode_id = episode['id']
                info = episode['info']
                unique_id = util.get_plugin_url(self._addon, series_id=series_id, season_id=season_id, id=episode_id)

                list_item = xbmcgui.ListItem(episode['name'], offscreen=True)
                tags = list_item.getVideoInfoTag()
                set_common_tags(tags, info, unique_id)

                set_tag_if_have(info, 'season', tags.setSeason)
                set_tag_if_have(info, 'episode', tags.setEpisode)
                set_tag_if_have(info, 'sortseason', tags.setSortSeason)
                set_tag_if_have(info, 'sortepisode', tags.setSortEpisode)
                set_tag_if_have(info, 'aired', tags.setFirstAired)

                url = get_url(self._addon, 'tvshows', series_id, episode_id)
                items.append((url, list_item, is_folder))

            xbmcplugin.setContent(handle=self._handle, content='episodes')
            xbmcplugin.addDirectoryItems(handle=self._handle, items=items)

            succeeded = True
        finally:
            xbmcplugin.endOfDirectory(handle=self._handle, succeeded=succeeded)
