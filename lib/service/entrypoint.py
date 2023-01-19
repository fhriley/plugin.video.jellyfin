import logging
import os
from concurrent.futures import ThreadPoolExecutor
from threading import Thread
from typing import List

import requests
import xbmc
import xbmcaddon
import xbmcgui

import websocket
from lib.api.jellyfin import authenticate
from lib.service.monitor import Monitor
from lib.service.playback_monitor import PlaybackMonitor
from lib.service.websocket_client import on_ws_message, on_ws_error, ws_app_loop
from lib.util.log import LOG_FORMAT, KodiHandler
from lib.util.settings import Settings
from lib.util.util import get_jf_id_from_list_item, get_server


class AbortWatcher:
    def __init__(self, monitor: xbmc.Monitor):
        self._monitor = monitor
        self._abort_requested = False
        self._thread = Thread(target=self._abort_watcher, name='abort_watcher')

    @property
    def abort_requested(self):
        return self._abort_requested

    def _abort_watcher(self):
        while not self._monitor.abortRequested():
            self._monitor.waitForAbort(1)
        self._abort_requested = True


# TODO: need notification from kodi on watched/unwatched, deleted, etc

def main(args: List[str]):
    handlers = [KodiHandler()]
    if os.environ.get('NOT_IN_KODI'):
        handlers = None
    logging.basicConfig(format=LOG_FORMAT, level=logging.DEBUG, handlers=handlers, force=True)
    log = logging.getLogger(__name__)
    wsapp = None

    try:
        user_cache = {}
        addon = xbmcaddon.Addon()
        settings = Settings(addon)

        # VideoLibrary.OnUpdate
        # VideoLibrary.OnRemove
        # VideoLibrary.OnScanStarted
        # VideoLibrary.OnScanFinished
        # VideoLibrary.OnCleanStarted
        # VideoLibrary.OnCleanFinished
        # VideoLibrary.OnRefresh
        # System.OnSleep
        # System.OnWake

        with ThreadPoolExecutor(max_workers=5) as executor:
            with requests.Session() as session:
                server = get_server(session, settings, addon)
                user = authenticate(server, user_cache, settings.get('username') or os.getenv('USERNAME'),
                                    settings.get('password') or os.getenv('PASSWORD'))

                monitor = Monitor(server, user)
                player = PlaybackMonitor(server, user)

                ws_log = logging.getLogger('websocket')
                url = server.ws_url(user)
                wsapp = websocket.WebSocketApp(url, header=server.get_headers(user),
                                               on_message=lambda wsapp, message: on_ws_message(ws_log, executor, player,
                                                                                               server, user, message),
                                               on_error=lambda wsapp, message: on_ws_error(ws_log, message))
                ws_thread = Thread(target=ws_app_loop, args=(ws_log, wsapp), daemon=True)
                ws_thread.start()

                while not monitor.abortRequested():
                    try:
                        if player.isPlaying() and player.playing_state and player.playing_state.jf_id:
                            time_s = player.getTime()
                            log.debug('%s: %.2f', player.playing_state.jf_id, time_s)
                            server.send_playback_time(user, player.playing_state.jf_id, time_s)
                    except Exception:
                        log.exception('playback state update failed')
                    monitor.waitForAbort(1)
    except Exception:
        log.exception('main failed')
    finally:
        if wsapp:
            wsapp.close()
