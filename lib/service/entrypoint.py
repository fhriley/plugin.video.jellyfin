import asyncio
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from threading import Thread, current_thread

import requests
import xbmcaddon

from lib.api.jellyfin import authenticate
from lib.service.monitor import Monitor
from lib.service.playback_monitor import PlaybackMonitor
from lib.service.websocket_client import ws_event_loop, ws_task
from lib.util.log import LOG_FORMAT, KodiHandler
from lib.util.settings import Settings
from lib.util.util import get_server


def main():
    current_thread().name = 'Service'

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

        playback_update_secs = settings.get_int('playback_update_secs')

        with requests.Session() as session:
            with ThreadPoolExecutor(max_workers=5) as executor:
                server = get_server(session, settings, addon)
                user = authenticate(server, user_cache, settings.get('username') or os.getenv('USERNAME'),
                                    settings.get('password') or os.getenv('PASSWORD'))

                player = PlaybackMonitor(server, user)
                loop = asyncio.new_event_loop()
                loop.set_default_executor(executor)
                ws_future = loop.create_task(ws_task(executor, player, settings, server, user), name='ws_task')
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
                    monitor.waitForAbort(playback_update_secs)
    except KeyboardInterrupt:
        pass
    except Exception:
        log.exception('main failed')
    finally:
        on_quit(ws_future)
        if ws_event_loop_thread:
            ws_event_loop_thread.join()
        log.debug('exiting')
