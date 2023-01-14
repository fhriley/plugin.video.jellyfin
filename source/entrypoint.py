import logging
import traceback
from pprint import pformat
from typing import Optional, Dict
from urllib.parse import urlparse, unquote

import requests
import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin

from lib.addon.entrypoint import get_server
from lib.addon.handlers.tvshow import TvShowHandlers
from lib.addon.log import KodiHandler, LOG_FORMAT
from lib.addon.settings import Settings
from lib.generic.api.jellyfin import Server, User
from lib.generic.scraper.tvshows import TvShowsScraper

_session: Optional[requests.Session] = None
_user_cache: Optional[Dict[str, User]] = None
_plugin_name = 'plugin.video.jellyfin'
_library_prefix = '/library'
_tvshows_prefix = f'{_library_prefix}/tvshows/'
_valid_cmds = {'plugin://{_plugin_name}{_tvshows_prefix}/'}
_player: Optional[xbmc.Player] = None


# plugin://plugin.video.jellyfin/library/tvshows

def authenticate(log: logging.Logger, server: Server, username: str, password: str) -> User:
    global _user_cache
    user = _user_cache.get(username)
    if not user or not server.is_authenticated(user):
        user = server.authenticate_by_password(username, password)
        _user_cache[user.user] = user
    log.debug('authenticate: user=%s', user)
    return user


def main(*args):
    # xbmc.log('============================ start', xbmc.LOGINFO)
    global _session
    global _user_cache
    global _player

    command = args[0]
    handle = int(args[1])

    log = None

    try:
        addon = xbmcaddon.Addon()
        settings = Settings(addon)

        level = logging.DEBUG if settings.debug_level > 0 else logging.INFO
        logging.basicConfig(format=LOG_FORMAT, level=level, handlers=[KodiHandler()])

        log = logging.getLogger(__name__)
        log.debug('============================ start debug_level=%s', settings.debug_level)

        if level == logging.DEBUG:
            for ii, arg in enumerate(args):
                log.debug('argv[%d]="%s"', ii, arg)

        if _session is None:
            _session = requests.Session()
            log.debug('creating new session')
        else:
            log.debug('reusing session')

        if _user_cache is None:
            _user_cache = {}

        if _player is None:
            _player = xbmc.Player()

        server = get_server(_session, settings, addon)
        user = authenticate(log, server, settings.get('username'), settings.get('password'))

        parsed = urlparse(command)
        split_path = parsed.path.lstrip('/').rstrip('/').split('/')
        if len(split_path) < 2:
            log.warning('unknown command: %s', command)
            return

        if split_path[1] == 'tvshows':
            if len(split_path) == 4:
                series_id = unquote(split_path[2])
                episode_id = unquote(split_path[3])
                episode = server.get_episode(user, series_id, episode_id,
                                             params={'fields': 'Path', 'enableUserData': 'true'})
                log.debug('%s', pformat(episode))
                path = episode['Path']
                list_item = xbmcgui.ListItem(path=path)
                #list_item.setInfo('video', {})
                list_item.setProperty('IsPlayable', 'true')
                #list_item.setPath(path)
                xbmcplugin.setResolvedUrl(handle, succeeded=True, listitem=list_item)
                if not _player.isPlaying():
                    _player.play(path, list_item)
            else:
                scraper = TvShowsScraper(server, debug_level=0)
                handlers = TvShowHandlers(settings, handle, addon, server, debug_level=1)
                if len(split_path) == 2:
                    shows = scraper.get_items(user)
                    shows = [show for show in shows if show['info']['title'] == 'The Flight Attendant']
                    handlers.create_items_directory(shows)
                elif len(split_path) == 3:
                    series_id = unquote(split_path[2])
                    episodes = scraper.get_episodes(user, series_id)
                    handlers.create_episodes(episodes)

        log.debug('============================ finish')
    except Exception:
        try:
            if log:
                log.exception('main failed')
            else:
                xbmc.log(f'main failed: {traceback.format_exc()}', xbmc.LOGERROR)
        except Exception:
            pass
