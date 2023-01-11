import logging
import sys
import traceback
from typing import Optional

import requests
import xbmc
import xbmcaddon

from lib.addon.log import KodiHandler, LOG_FORMAT
from lib.addon.settings import Settings
from lib.generic.api.jellyfin import Server

_session: Optional[requests.Session] = None


def main():
    # xbmc.log('============================ start', xbmc.LOGINFO)
    global _session
    handle = int(sys.argv[1])
    log = None

    try:
        addon = xbmcaddon.Addon()
        settings = Settings(addon)

        level = logging.DEBUG if settings.debug_level > 0 else logging.INFO
        logging.basicConfig(format=LOG_FORMAT, level=level, handlers=[KodiHandler()])

        log = logging.getLogger(__name__)
        log.debug('============================ start debug_level=%s', settings.debug_level)

        if level == logging.DEBUG:
            for ii, arg in enumerate(sys.argv):
                log.debug('argv[%d]=%s', ii, arg)

        if _session is None:
            _session = requests.Session()
            log.debug('creating new session')
        else:
            log.debug('reusing session')

        log.debug('============================ finish')
    except Exception:
        try:
            if log:
                log.exception('main failed')
            else:
                xbmc.log(f'main failed: {traceback.format_exc()}', xbmc.LOGERROR)
        except Exception:
            pass
