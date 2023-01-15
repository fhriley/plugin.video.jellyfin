import logging

import xbmcgui
import xbmcplugin

from lib.api.jellyfin import User
from lib.builder.movies import MoviesBuilder
from lib.router.base import Router
from lib.scraper.movies import MoviesScraper
from lib.scraper.queries import get_item
from lib.util import util

_log = logging.getLogger(__name__)


class MoviesRouter(Router):
    def getdetails(self, user: User, scraper: MoviesScraper, builder: MoviesBuilder, params: dict):
        try:
            in_params = util.get_args_from_params('getdetails', params, ('id',))
            _log.debug('getdetails: in_params=%s', in_params)
            jf_movie = get_item(self._server, user, in_params['id'])
            movie = scraper.scrape_movie(jf_movie)
            builder.build_movie(movie)
        except Exception:
            xbmcplugin.setResolvedUrl(handle=self._handle, succeeded=False, listitem=xbmcgui.ListItem(offscreen=True))
            raise
