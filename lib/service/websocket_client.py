import asyncio
import concurrent.futures
import datetime
import logging
from concurrent.futures import ThreadPoolExecutor
from pprint import pformat
from typing import Dict, Any, Optional, Tuple, Iterable

import simplejson as json

import websockets
from lib.api.jellyfin import Server, User
from lib.service.entrypoint import PlaybackMonitor
from lib.service.json_rpc import refresh_kodi_episode, remove_kodi_episode, get_kodi_id, \
    remove_kodi_movie, remove_kodi_tvshow, refresh_kodi_movie, refresh_kodi_tvshow, \
    scan_kodi_tvshows, scan_kodi_movies, get_kodi_episode_id, get_kodi_tvshow_id, get_kodi_movie_id
from lib.service.queries import NotFound, get_item
from lib.util.settings import Settings


def sync_library(log: logging.Logger, executor: ThreadPoolExecutor, settings: Settings, player: PlaybackMonitor,
                 server: Server, user: User):
    if settings.last_sync_time:
        log.debug('last_sync_time=%s', settings.last_sync_time)
        current_time = server.get_server_time()
        data = server.get_sync_queue(user, settings.last_sync_time)
        if log.isEnabledFor(logging.DEBUG):
            log.debug('%s', pformat(data))
        library_changed(log, executor, player, settings, server, user, current_time, data)


_changed_handlers = {
    'Episode': ('Id', get_kodi_episode_id, refresh_kodi_episode),
    'Season': ('SeriesId', get_kodi_tvshow_id, refresh_kodi_tvshow),
    'Series': ('Id', get_kodi_tvshow_id, refresh_kodi_tvshow),
    'Movie': ('Id', get_kodi_movie_id, refresh_kodi_movie),
}

_added_handlers = {
    'Episode': scan_kodi_tvshows,
    'Series': scan_kodi_tvshows,
    'Movie': scan_kodi_movies,
}


def _get_item_and_id(server: Server, user: User, item_id: str) -> Tuple[Optional[Dict[str, Any]], str]:
    try:
        return get_item(server, user, item_id), item_id
    except NotFound:
        return None, item_id


def _call_changed_handlers(log: logging.Logger, executor: ThreadPoolExecutor, player: PlaybackMonitor, server: Server,
                           user: User, item_ids: Iterable[str]):
    if player.playing_state:
        item_ids = [item_id for item_id in item_ids if item_id != player.playing_state.jf_id]
        if not item_ids:
            return

    get_item_futures = [executor.submit(_get_item_and_id, server, user, item_id) for item_id in item_ids]

    get_id_futures = {}
    seen = set()

    for fut in concurrent.futures.as_completed(get_item_futures):
        jf_item, item_id = fut.result()
        if not jf_item:
            log.warning('%s not found', item_id)
            continue

        if log.isEnabledFor(logging.DEBUG):
            log.debug('%s', pformat(jf_item))

        jf_item_type = jf_item.get('Type')
        handlers = _changed_handlers.get(jf_item_type)
        if handlers:
            id_key, get_id, _ = handlers
            jf_id = jf_item[id_key]
            if jf_id in seen:
                continue
            seen.add(jf_id)
            get_id_futures[executor.submit(get_id, log, jf_id)] = (jf_item_type, jf_id)
        else:
            log.debug('unhandled jellyfin type: %s', jf_item_type)

    func_futures = []
    # For each kodi id, call the handler function
    for fut in concurrent.futures.as_completed(get_id_futures.keys()):
        jf_item_type, jf_id = get_id_futures[fut]
        try:
            kodi_id = fut.result()
        except NotFound:
            log.warning('%s not found', jf_id)
            continue

        log.debug('%s kodi_id=%s', jf_item_type, kodi_id)
        _, _, refresh = _changed_handlers[jf_item_type]
        func_futures.append(executor.submit(refresh, log, kodi_id))

    for fut in concurrent.futures.as_completed(func_futures):
        exc = fut.exception()
        if exc:
            raise exc


def _added_handler(log: logging.Logger, server: Server, user: User, item_id: str) -> Tuple[str, Optional[str]]:
    try:
        jf_item = get_item(server, user, item_id)
        if log.isEnabledFor(logging.DEBUG):
            log.debug('%s', pformat(jf_item))
        return item_id, jf_item.get('Type')
    except NotFound:
        log.warning('%s not found', item_id)
        return item_id, None


def _removed_handler(log: logging.Logger, item_id: str):
    try:
        kodi_id, typ = get_kodi_id(log, item_id)
        log.debug('kodi_id=%s', kodi_id)
        if typ == 'movie':
            remove_kodi_movie(log, kodi_id)
        elif typ == 'episode':
            remove_kodi_episode(log, kodi_id)
        elif typ == 'tvshow':
            remove_kodi_tvshow(log, kodi_id)
    except NotFound:
        log.warning('%s not found', item_id)


def user_data_changed(log: logging.Logger, executor: ThreadPoolExecutor, player: PlaybackMonitor, settings: Settings,
                      server: Server, user: User, message_time: datetime.datetime, data):
    log.debug("user_data_changed handler")

    item_ids = []
    for item_info in data.get('UserDataList') or []:
        item_id = item_info.get('ItemId')
        if item_id:
            item_ids.append(item_id)
        else:
            log.warning('got user data change with no ItemId')

    _call_changed_handlers(log, executor, player, server, user, item_ids)

    settings.last_sync_time = message_time


def library_changed(log: logging.Logger, executor: ThreadPoolExecutor, player: PlaybackMonitor, settings: Settings,
                    server: Server, user: User, message_time: datetime.datetime, data):
    log.debug("library_changed handler")

    added = {val for val in data.get('ItemsAdded') or []}
    updated = {val for val in data.get('ItemsUpdated') or []}
    removed = {val for val in data.get('ItemsRemoved') or []}

    user_data = data.get('UserDataChanged')
    if user_data:
        updated.update([item['ItemId'] for item in user_data])

    updated.difference_update(added)
    removed.difference_update(updated)
    removed.difference_update(added)

    _call_changed_handlers(log, executor, player, server, user, updated)
    futures = [executor.submit(_removed_handler, log, item_id) for item_id in removed]

    try:
        added_futures = [executor.submit(_added_handler, log, server, user, item_id) for item_id in added]
        added_types = set()

        for fut in concurrent.futures.as_completed(added_futures):
            item_id, typ = fut.result()
            if typ:
                added_types.add(typ)
            else:
                log.warning('%s not found', item_id)

        if 'Series' in added_types or 'Episode' in added_types:
            scan_kodi_tvshows(log)
        if 'Movie' in added_types:
            scan_kodi_movies(log)
    finally:
        concurrent.futures.wait(futures)

    for fut in futures:
        exc = fut.exception()
        if exc:
            raise exc

    settings.last_sync_time = message_time


_handlers = {
    'UserDataChanged': user_data_changed,
    'LibraryChanged': library_changed,
}


async def on_ws_message(log: logging.Logger, executor: ThreadPoolExecutor, player: PlaybackMonitor, settings: Settings,
                        server: Server, user: User, message_str: str, message_time: datetime.datetime):
    message = json.loads(message_str)
    if log.isEnabledFor(logging.DEBUG):
        log.debug('\n%s', pformat(message))

    message_type = message.get('MessageType')
    handler = _handlers.get(message_type)
    if handler:
        data = message.get('Data')
        if data:
            handler(log, executor, player, settings, server, user, message_time, data)


async def ws_task(executor: ThreadPoolExecutor, player: PlaybackMonitor, settings: Settings, server: Server,
                  user: User):
    log = logging.getLogger('ws_task')
    log.debug('ws_task started')

    logging.getLogger('websockets.client').setLevel(logging.INFO)

    try:
        url = server.ws_url(user)
        while True:
            try:
                log.setLevel(settings.service_log_level)
                log.debug('connecting to %s', url)
                async with websockets.connect(url, compression=None, open_timeout=3, ping_interval=5,
                                              ping_timeout=3, close_timeout=3) as ws:
                    sync_library(log, executor, settings, player, server, user)

                    while True:
                        try:
                            message_time = server.get_server_time()
                            message = await ws.recv()
                        except (OSError, websockets.WebSocketException):
                            log.error('websockets recv error')
                            break
                        try:
                            log.setLevel(settings.service_log_level)
                            await on_ws_message(log, executor, player, settings, server, user, message, message_time)
                        except Exception:
                            log.exception('ws_task failure')
                            break
            except (OSError, websockets.WebSocketException):
                log.error('websockets.connect failure', url)
            except Exception:
                log.exception('connection loop failure')
            await asyncio.sleep(1)
    except Exception:
        log.exception('ws_task failure')
    finally:
        log.debug('ws_task exiting')


def ws_event_loop(loop, settings, ws_future):
    log = logging.getLogger('ws_event_loop')
    try:
        asyncio.set_event_loop(loop)
        loop.run_until_complete(ws_future)
    except Exception:
        log.exception('failed')
    except asyncio.exceptions.CancelledError:
        log.setLevel(settings.service_log_level)
        log.debug('cancelled')
    finally:
        log.setLevel(settings.service_log_level)
        log.debug('exiting')
