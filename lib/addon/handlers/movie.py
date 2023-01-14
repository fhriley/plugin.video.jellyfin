from typing import Optional

import xbmc
import xbmcaddon

from lib.addon.handlers.base import Handlers
from lib.addon.settings import Settings
from lib.generic.api.jellyfin import Server
from lib.generic.scraper import movies


class MovieHandlers(Handlers):
    def __init__(self, settings: Settings, handle: int, params: dict, addon: xbmcaddon.Addon,
                 server: Server, debug_level: Optional[int] = 0):
        scraper = movies.MoviesScraper(server, debug_level=debug_level)
        super().__init__(scraper, settings, handle, params, addon)
        self.__scraper = scraper

    def _getdetails_set_tags(self, tags: xbmc.InfoTagVideo, item_id: str, info: dict):
        # TODO: box sets
        # setSetId/setSet/setSetOverview
        pass
