from typing import List, Dict, Any

import xbmc
import xbmcgui

from lib.source.builder.base import Builder


class MoviesBuilder(Builder):
    def _build_directory_set_list_item(self, list_item: xbmcgui.ListItem, item_id: str, jf_item: dict):
        pass

    def _build_directory_set_tags(self, tags: xbmc.InfoTagVideo, item_id: str, info: dict):
        # TODO: box sets
        # setSetId/setSet/setSetOverview
        pass

    def build_directory(self, items: List[Dict[str, Any]]):
        self._build_directory(items, 'movies')
