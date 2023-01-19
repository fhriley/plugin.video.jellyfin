import logging
import sys
import traceback
from typing import Type, Union, Optional
from urllib.parse import parse_qsl, unquote_plus

import requests
import xbmc
import xbmcaddon

from lib.api.jellyfin import Server
from lib.builder.movies import MoviesBuilder
from lib.builder.tvshows import TvShowsBuilder
from lib.router.movies import MoviesRouter
from lib.router.tvshows import TvShowsRouter
from lib.scraper.movies import MoviesScraper
from lib.scraper.tvshows import TvShowsScraper
from lib.util.log import KodiHandler, LOG_FORMAT
from lib.util.settings import Settings
from lib.util.util import get_server


def get_params() -> dict:
    param_string = sys.argv[2][1:]
    if param_string:
        return dict(parse_qsl(param_string))
    return {}


# Global so it gets reused between invocations of the interpreters
_session: Optional[requests.Session] = None
_log: Optional[logging.Logger] = None


def _log_config(level):
    logging.basicConfig(format=LOG_FORMAT, level=level, handlers=[KodiHandler()], force=True)


def main(router_class: Type[Union[MoviesRouter, TvShowsRouter]],
         scraper_class: Type[Union[MoviesScraper, TvShowsScraper]],
         builder_class: Type[Union[MoviesBuilder, TvShowsBuilder]]):
    # xbmc.log('============================ start', xbmc.LOGINFO)
    global _session
    global _log
    handle = int(sys.argv[1])
    log = None

    try:
        addon = xbmcaddon.Addon()
        settings = Settings(addon)

        level = logging.DEBUG if settings.debug_level > 0 else logging.INFO
        if _log is None:
            _log_config(level)
            _log = logging.getLogger(__name__)
        else:
            if level != _log.getEffectiveLevel():
                _log_config(level)

        _log.debug('============================ start debug_level=%s', settings.debug_level)

        if level == logging.DEBUG:
            for ii, arg in enumerate(sys.argv):
                _log.debug('argv[%d]=%s', ii, arg)

        if _session is None:
            _session = requests.Session()
            _log.debug('creating new session')
        else:
            _log.debug('reusing session')

        server = get_server(_session, settings, addon)
        params = get_params()
        router = router_class(settings, handle, addon, server, debug_level=settings.debug_level)
        scraper = scraper_class(server, settings.debug_level)
        builder = builder_class(settings, handle, addon)

        router.execute(scraper, builder, params)

        _log.debug('============================ finish')
    except Exception:
        try:
            if log:
                _log.exception('main failed')
            else:
                xbmc.log(f'main failed: {traceback.format_exc()}', xbmc.LOGERROR)
        except Exception:
            pass
