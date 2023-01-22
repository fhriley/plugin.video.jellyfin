import asyncio
import logging
import os
from pprint import pformat
from threading import Thread, current_thread
from typing import List

import requests
import xbmc
import xbmcaddon

from lib.api.jellyfin import authenticate, Server, User
from lib.service.monitor import Monitor
from lib.service.playback_monitor import PlaybackMonitor
from lib.service.websocket_client import ws_event_loop, ws_task, library_changed, sync_library
from lib.util.log import LOG_FORMAT, KodiHandler
from lib.util.settings import Settings
from lib.util.util import get_server


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


def main(args: List[str]):
    thread = current_thread()
    thread.name = 'Service'
    handlers = [KodiHandler()]
    if os.environ.get('NOT_IN_KODI'):
        handlers = None
    logging.basicConfig(format=LOG_FORMAT, level=logging.DEBUG, handlers=handlers, force=True)
    log = logging.getLogger(__name__)
    ws_future = None
    ws_event_loop_thread = None

    def on_quit(future):
        if future and not future.done():
            future.cancel()

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

        with requests.Session() as session:
            server = get_server(session, settings, addon)
            user = authenticate(server, user_cache, settings.get('username') or os.getenv('USERNAME'),
                                settings.get('password') or os.getenv('PASSWORD'))

            player = PlaybackMonitor(server, user)
            loop = asyncio.new_event_loop()
            ws_future = loop.create_task(ws_task(player, settings, server, user), name='ws_task')
            monitor = Monitor(settings, server, user, lambda: on_quit(ws_future))
            ws_event_loop_thread = Thread(target=ws_event_loop, args=(loop, ws_future),
                                          name='ws_event_loop')
            ws_event_loop_thread.start()

            while not monitor.abortRequested():
                try:
                    if player.isPlaying() and player.playing_state and player.playing_state.jf_id:
                        time_s = player.getTime()
                        log.debug('%s: %.2f', player.playing_state.jf_id, time_s)
                        server.send_playback_time(user, player.playing_state.jf_id, time_s)
                except Exception:
                    log.exception('playback state update failed')
                monitor.waitForAbort(3)
    except KeyboardInterrupt:
        pass
    except Exception:
        log.exception('main failed')
    finally:
        on_quit(ws_future)
        if ws_event_loop_thread:
            ws_event_loop_thread.join()
        log.debug('exiting')
