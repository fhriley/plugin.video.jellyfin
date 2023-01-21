import asyncio
import datetime
import logging
import socket
from concurrent.futures import ThreadPoolExecutor
from pprint import pformat
from typing import Dict, Any

import simplejson as json

import websockets
from lib.api.jellyfin import Server, User
from lib.service.entrypoint import PlaybackMonitor
from lib.service.json_rpc import get_kodi_episode_id, refresh_kodi_episode, remove_kodi_episode, get_kodi_id, \
    remove_kodi_movie, remove_kodi_tvshow, get_kodi_movie_id, refresh_kodi_movie, refresh_kodi_tvshow, \
    get_kodi_tvshow_id, scan_kodi_tvshows, scan_kodi_movies
from lib.service.queries import NotFound, get_item
from lib.util.settings import Settings

def get_kodi_season_id(log: logging.Logger, jf_item: Dict[str, Any], jf_id: str) -> int:
    series_id = jf_item['SeriesId']
    return get_kodi_tvshow_id(log, series_id)

_get_kodi_episode_id = lambda log, jf_item, jf_id: get_kodi_episode_id(log, jf_id)
_get_kodi_tvshow_id = lambda log, jf_item, jf_id: get_kodi_tvshow_id(log, jf_id)
_get_kodi_movie_id = lambda log, jf_item, jf_id: get_kodi_movie_id(log, jf_id)

_changed_handlers = {
    'Episode': (_get_kodi_episode_id, refresh_kodi_episode),
    'Season': (get_kodi_season_id, refresh_kodi_tvshow),
    'Series': (_get_kodi_tvshow_id, refresh_kodi_tvshow),
    'Movie': (_get_kodi_movie_id, refresh_kodi_movie),
}

_added_handlers = {
    'Episode': scan_kodi_tvshows,
    'Series': scan_kodi_tvshows,
    'Movie': scan_kodi_movies,
}


def _call_changed_handler(log: logging.Logger, player: PlaybackMonitor, server: Server, user: User, item_id: str):
    if player.playing_state and item_id == player.playing_state.jf_id:
        log.debug('%s is currently playing, skipping', item_id)
        return

    jf_item = get_item(server, user, item_id)
    if log.isEnabledFor(logging.DEBUG):
        log.debug('%s', pformat(jf_item))

    jf_item_type = jf_item.get('Type')
    funcs = _changed_handlers.get(jf_item_type)

    if funcs:
        get_id, func = funcs
        kodi_id = get_id(log, jf_item, item_id)
        log.debug('%s kodi_id=%s', jf_item_type, kodi_id)
        func(log, kodi_id)
    else:
        log.debug('unhandled jellyfin type: %s', jf_item_type)


def _added_handler(log: logging.Logger, server: Server, user: User, item_id: str):
    jf_item = get_item(server, user, item_id)
    if log.isEnabledFor(logging.DEBUG):
        log.debug('%s', pformat(jf_item))
    return jf_item.get('Type')


# def _call_added_handler(log: logging.Logger, server: Server, user: User, item_id: str):
#     jf_item = get_item(server, user, item_id)
#     if log.isEnabledFor(logging.DEBUG):
#         log.debug('%s', pformat(jf_item))
#
#     jf_item_type = jf_item.get('Type')
#     jf_path = jf_item.get('Path')
#     scan_func: Callable = _added_handlers.get(jf_item_type)
#
#     if scan_func:
#         if jf_path:
#             directory = PurePath(jf_path).parent
#             log.debug('scanning %s at %s', jf_item_type, directory)
#             scan(log, directory)
#         else:
#             log.warning('%s %s: no path', jf_item_type, item_id)
#     else:
#         log.debug('unhandled jellyfin type: %s', jf_item_type)


def _removed_handler(log: logging.Logger, item_id: str):
    kodi_id, typ = get_kodi_id(log, item_id)
    log.debug('kodi_id=%s', kodi_id)
    if typ == 'movie':
        remove_kodi_movie(log, kodi_id)
    elif typ == 'episode':
        remove_kodi_episode(log, kodi_id)
    elif typ == 'tvshow':
        remove_kodi_tvshow(log, kodi_id)


def user_data_changed(log: logging.Logger, player: PlaybackMonitor, settings: Settings, server: Server, user: User,
                      message_time: datetime.datetime, data):
    '''
    {'Data': {'UserDataList': [{'IsFavorite': False,
                               'ItemId': '16a8433c712dceefb0a1538f3609e589',
                               'Key': '295936001007',
                               'LastPlayedDate': '2023-01-20T13:28:27.377Z',
                               'PlayCount': 5,
                               'PlaybackPositionTicks': 0,
                               'Played': True},
                              {'IsFavorite': False,
                               'ItemId': 'f685903ca281da3b87c639c554d5b11c',
                               'Key': '295936001',
                               'PlayCount': 0,
                               'PlaybackPositionTicks': 0,
                               'Played': False,
                               'UnplayedItemCount': 4}],
             'UserId': 'd4d75bfbe12f420f9ad25dc7cd1de12a'},
    'MessageId': 'bd4574fe111746978a6b822645b368e0',
    'MessageType': 'UserDataChanged'}
    '''
    try:
        log.debug("user_data_changed handler")

        for item_info in data.get('UserDataList') or []:
            item_id = item_info.get('ItemId')
            if not item_id:
                log.warning('got user data change with no ItemId')
                return
            try:
                _call_changed_handler(log, player, server, user, item_id)
            except NotFound:
                log.warning('%s not found', item_id)

        settings.last_sync_time = message_time
    except Exception:
        log.exception('user_data_changed failure')


def library_changed(log: logging.Logger, player: PlaybackMonitor, settings: Settings, server: Server, user: User,
                    message_time: datetime.datetime, data):
    '''
    {'Data': {'CollectionFolders': ['767bffe4f11c93ef34b805451a696a4e',
                                   'f137a2dd21bbc1b99aa5c0f6bf02a805',
                                   '9d7ad6afe9afa2dab1a2f6e00ad28fa6'],
             'FoldersAddedTo': [],
             'FoldersRemovedFrom': ['616d2250e5b88041f5b1b5af1ad32578',
                                    '518d9a04e60be4acbc54fe0dd1fd4208',
                                    'd47cd8e0f2cecf2289a1f24d8c44b040'],
             'IsEmpty': False,
             'ItemsAdded': [],
             'ItemsRemoved': ['074a92eccb6ea578ad33c94175ee6a14',
                              '59ba46de911bb9eb7bd1db6287c325d8',
                              '82c282227046ada318e90b9bad543be8',
                              '1b5bf3c964d0c430287da7482a9c1951',
                              'e8a71d7f97adb80925b73338f209e4fb',
                              '6e19e13c85e2addb69ceffeab6977a5c'],
             'ItemsUpdated': ['72cc9ff80565b9245038f28d335fd3a1']},
    'MessageId': '99ca2ebdcb2241d3a0e5c16654bfa653',
    'MessageType': 'LibraryChanged'}
    '''
    try:
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

        for item_id in updated:
            try:
                _call_changed_handler(log, player, server, user, item_id)
            except NotFound:
                log.warning('%s not found', item_id)

        added_types = set()

        for item_id in added:
            try:
                added_types.add(_added_handler(log, server, user, item_id))
            except NotFound:
                log.warning('%s not found', item_id)

        for item_id in removed:
            try:
                _removed_handler(log, item_id)
            except NotFound:
                log.warning('%s not found', item_id)

        if 'Series' in added_types or 'Episode' in added_types:
            scan_kodi_tvshows(log)
        if 'Movie' in added_types:
            scan_kodi_movies(log)

        settings.last_sync_time = message_time
    except Exception:
        log.exception('library_changed failure')


_handlers = {
    'UserDataChanged': user_data_changed,
    'LibraryChanged': library_changed,
}


async def on_ws_message(log: logging.Logger, player: PlaybackMonitor, settings: Settings, server: Server,
                        user: User, message_str: str, message_time: datetime.datetime):
    try:
        message = json.loads(message_str)
        from pprint import pformat
        log.debug('\n%s', pformat(message))

        message_type = message.get('MessageType')
        handler = _handlers.get(message_type)
        if handler:
            data = message.get('Data')
            if data:
                asyncio.get_running_loop().run_in_executor(None, handler, log, player, settings, server, user,
                                                           message_time, data)
    except Exception:
        log.exception('ws message failure')


async def ws_task(player, settings: Settings, server: Server, user: User):
    log = logging.getLogger('ws_task')
    log.debug('ws_task started')

    logging.getLogger('websockets.client').setLevel(logging.INFO)

    try:
        url = server.ws_url(user)
        while True:
            try:
                async with websockets.connect(url, compression=None, open_timeout=3, ping_interval=5,
                                              ping_timeout=3, close_timeout=3) as ws:
                    while True:
                        try:
                            message = await ws.recv()
                            message_time = server.get_server_time()
                            await on_ws_message(log, player, settings, server, user, message, message_time)
                        except websockets.ConnectionClosedError:
                            break
                        except Exception:
                            log.exception('ws_task failure')
            except socket.gaierror:
                log.debug('websockets.connect("%s") failure', url)
                await asyncio.sleep(1)
    except Exception:
        log.exception('ws_task failure')
    finally:
        log.debug('ws_task exiting')


def ws_event_loop(loop, ws_future):
    log = logging.getLogger('ws_event_loop')
    try:
        asyncio.set_event_loop(loop)
        with ThreadPoolExecutor(max_workers=1) as executor:
            loop.set_default_executor(executor)
            loop.run_until_complete(ws_future)
    except Exception:
        log.exception('failed')
    except asyncio.exceptions.CancelledError:
        log.debug('cancelled')
    finally:
        log.debug('exiting')
