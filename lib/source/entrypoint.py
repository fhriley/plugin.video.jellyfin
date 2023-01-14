import logging
import sys
import traceback
from pprint import pformat
from typing import Optional, Dict
from urllib.parse import urlparse, unquote, parse_qsl

import requests
import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin

from lib.api.jellyfin import Server, User, authenticate
from lib.scraper.tvshows import TvShowsScraper
from lib.source.builder.tvshows import TvShowsBuilder
from lib.source.log import KodiHandler, LOG_FORMAT
from lib.source.settings import Settings

_session: Optional[requests.Session] = None
_user_cache: Optional[Dict[str, User]] = None
_plugin_name = 'plugin.video.jellyfin'
_library_prefix = '/library'
_tvshows_prefix = f'{_library_prefix}/tvshows/'
_valid_cmds = {'plugin://{_plugin_name}{_tvshows_prefix}/'}


# plugin://plugin.video.jellyfin/library/tvshows

def get_params() -> dict:
    param_string = sys.argv[2][1:]
    if param_string:
        return dict(parse_qsl(param_string))
    return {}


def get_server(session: requests.Session, settings: Settings, addon: xbmcaddon.Addon) -> Server:
    server_url = settings.get('serverurl')
    device_name = xbmc.getInfoLabel('System.FriendlyName')
    version = addon.getAddonInfo('version')
    verify_cert = settings.get_bool('sslverify')
    return Server(session, server_url, settings.client_name, device_name, settings.device_id, version, verify_cert,
                  log_raw_resp=settings.debug_level > 2)


def main(*args):
    # xbmc.log('============================ start', xbmc.LOGINFO)
    global _session
    global _user_cache

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

        server = get_server(_session, settings, addon)
        user = authenticate(server, _user_cache, settings.get('username'), settings.get('password'))

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
                list_item.setProperty('IsPlayable', 'true')
                xbmcplugin.setResolvedUrl(handle, succeeded=True, listitem=list_item)
                player = xbmc.Player()
                if not player.isPlaying():
                    player.play(path, list_item)
            else:
                scraper = TvShowsScraper(server, debug_level=0)
                builder = TvShowsBuilder(settings, handle, addon)
                if len(split_path) == 2:
                    shows = scraper.get_items(user)
                    shows = [show for show in shows if show['info']['title'] == 'The Flight Attendant']
                    builder.build_directory(shows)
                elif len(split_path) == 3:
                    series_id = unquote(split_path[2])
                    episodes = scraper.get_episodes(user, series_id)
                    builder.build_episodes(episodes)

        log.debug('============================ finish')
    except Exception:
        try:
            if log:
                log.exception('main failed')
            else:
                xbmc.log(f'main failed: {traceback.format_exc()}', xbmc.LOGERROR)
        except Exception:
            pass
