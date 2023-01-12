import logging
import sys
import traceback
from typing import Optional, Dict

import requests
import xbmc
import xbmcaddon

from lib.addon.entrypoint import get_server
from lib.addon.log import KodiHandler, LOG_FORMAT
from lib.addon.settings import Settings
from lib.generic.api.jellyfin import Server, User
from lib.source.items import get_tvshows

_session: Optional[requests.Session] = None
_user_cache: Optional[Dict[str, User]] = None


def authenticate(log: logging.Logger, server: Server, username: str, password: str) -> User:
    global _user_cache
    user = _user_cache.get(username)
    if not user or not server.is_authenticated(user):
        user = server.authenticate_by_password(username, password)
        _user_cache[user.user] = user
    log.debug('authenticate: user=%s', user)
    return user


def main():
    # xbmc.log('============================ start', xbmc.LOGINFO)
    global _session
    global _user_cache

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

        if _user_cache is None:
            _user_cache = {}

        server = get_server(_session, settings, addon)
        user = authenticate(log, server, settings.get('username'), settings.get('password'))
        get_tvshows(handle, server, user, debug_level=settings.debug_level)

        log.debug('============================ finish')
    except Exception:
        try:
            if log:
                log.exception('main failed')
            else:
                xbmc.log(f'main failed: {traceback.format_exc()}', xbmc.LOGERROR)
        except Exception:
            pass
