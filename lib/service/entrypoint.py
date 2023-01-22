import asyncio
import logging
import os
import traceback
from concurrent.futures import ThreadPoolExecutor
from threading import Thread, current_thread

import requests
import xbmc
import xbmcaddon

from lib.api.jellyfin import authenticate
from lib.service.monitor import Monitor
from lib.service.playback_monitor import PlaybackMonitor
from lib.service.websocket_client import ws_event_loop, ws_task
from lib.util.log import LOG_FORMAT, KodiHandler, LogHolder
from lib.util.settings import Settings
from lib.util.util import get_server


def _log_config(level):
    logging.basicConfig(format=LOG_FORMAT, level=level, handlers=[KodiHandler()], force=True)


def main():
    current_thread().name = 'Service'

    ws_future = None
    ws_event_loop_thread = None
    log_holder = None

    def on_quit(future):
        if future and not future.done():
            future.cancel()

    try:
        user_cache = {}
        addon = xbmcaddon.Addon()
        settings = Settings(addon)

        level = settings.service_log_level
        _log_config(level)
        log_holder = LogHolder.getLogger(__name__)

        playback_update_secs = settings.get_int('playback_update_secs')

        with requests.Session() as session:
            with ThreadPoolExecutor(max_workers=5) as executor:
                server = get_server(session, settings, addon, settings.service_debug_level)
                user = authenticate(server, user_cache, settings.get('username') or os.getenv('USERNAME'),
                                    settings.get('password') or os.getenv('PASSWORD'))

                player = PlaybackMonitor(server, user)
                loop = asyncio.new_event_loop()
                loop.set_default_executor(executor)
                ws_future = loop.create_task(ws_task(executor, player, settings, server, user), name='ws_task')
                monitor = Monitor(settings, server, user, lambda: on_quit(ws_future))
                ws_event_loop_thread = Thread(target=ws_event_loop, args=(loop, ws_future), name='ws_event_loop')
                ws_event_loop_thread.start()

                while not monitor.abortRequested():
                    new_level = settings.service_log_level
                    if new_level != level:
                        level = new_level
                        _log_config(level)
                        LogHolder.update_all()

                    try:
                        if player.isPlaying() and player.playing_state and player.playing_state.jf_id:
                            time_s = player.getTime()
                            log_holder.log.debug('%s: %.2f', player.playing_state.jf_id, time_s)
                            server.send_playback_time(user, player.playing_state.jf_id, time_s)
                    except Exception:
                        log_holder.log.exception('playback state update failed')
                    monitor.waitForAbort(playback_update_secs)
    except KeyboardInterrupt:
        pass
    except Exception:
        try:
            if log_holder:
                log_holder.log.exception('main failed')
            else:
                xbmc.log(f'main failed: {traceback.format_exc()}', xbmc.LOGERROR)
        except Exception:
            pass
    finally:
        on_quit(ws_future)
        if ws_event_loop_thread:
            ws_event_loop_thread.join()
        if log_holder:
            log_holder.log.debug('exiting')
        else:
            xbmc.log(f'exiting', xbmc.LOGINFO)
