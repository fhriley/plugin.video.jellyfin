from typing import List, Dict, Any

import xbmc
import xbmcgui
import xbmcplugin

from lib.builder.base import Builder, set_common_tags


class MoviesBuilder(Builder):
    def _build_directory_set_list_item(self, list_item: xbmcgui.ListItem, item_id: str, jf_item: dict):
        pass

    def _build_directory_set_tags(self, tags: xbmc.InfoTagVideo, item_id: str, info: dict):
        # TODO: box sets
        # setSetId/setSet/setSetOverview
        pass

    def build_directory(self, items: List[Dict[str, Any]]):
        self._build_directory(items, 'movies')

    def build_movie(self, jf_item: Dict[str, Any]):
        item_id = jf_item['id']
        info = jf_item['info']

        list_item = xbmcgui.ListItem(jf_item['name'], offscreen=True)

        tags = list_item.getVideoInfoTag()
        set_common_tags(tags, info, item_id)

        # TODO: box sets
        # setSetId/setSet/setSetOverview

        xbmcplugin.setResolvedUrl(handle=self._handle, succeeded=True, listitem=list_item)
