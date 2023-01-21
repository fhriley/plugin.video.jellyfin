import asyncio
import logging
import socket
from concurrent.futures import ThreadPoolExecutor
from pprint import pformat

import simplejson as json

import websockets
from lib.api.jellyfin import Server, User
from lib.service.entrypoint import PlaybackMonitor
from lib.service.json_rpc import get_kodi_episode_id, refresh_kodi_episode
from lib.service.queries import get_item

_changed_handlers = {
    'Episode': (get_kodi_episode_id, refresh_kodi_episode)
}


def _call_handler(log: logging.Logger, player: PlaybackMonitor, server: Server, user: User, item_id: str):
    if player.playing_state and item_id == player.playing_state.jf_id:
        log.debug('%s is currently playing, skipping', item_id)
        return

    jf_item = get_item(server, user, item_id)
    if log.isEnabledFor(logging.DEBUG):
        log.debug('%s', pformat(jf_item))

    jf_item_type = jf_item.get('Type')
    funcs = _changed_handlers.get(jf_item_type)

    if funcs:
        get_id, refresh = funcs
        kodi_id = get_id(log, item_id)
        if kodi_id:
            log.debug('%s kodi_id=%s', jf_item_type, kodi_id)
            refresh(log, kodi_id)
        else:
            log.warning('could not find kodi id for jellyfin %s %s', jf_item_type, item_id)
    else:
        log.debug('unhandled jellyfin type: %s', jf_item_type)


def user_data_changed(log: logging.Logger, player: PlaybackMonitor, server: Server, user: User, data):
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
    log.debug("user_data_changed handler")
    for item_info in data.get('UserDataList') or []:
        item_id = item_info.get('ItemId')
        if not item_id:
            log.warning('got user data change with no ItemId')
            return
        _call_handler(log, player, server, user, item_id)


def library_changed(log: logging.Logger, player: PlaybackMonitor, server: Server, user: User, data):
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
    log.debug("library_changed handler")
    items = set()
    for key in ('ItemsAdded', 'ItemsRemoved', 'ItemsUpdated'):
        items.update(data.get(key) or [])
    for item_id in items:
        _call_handler(log, player, server, user, item_id)


_handlers = {
    'UserDataChanged': user_data_changed,
    'LibraryChanged': library_changed,
}


async def on_ws_message(log: logging.Logger, player: PlaybackMonitor, server: Server,
                        user: User, message_str: str):
    try:
        message = json.loads(message_str)
        from pprint import pformat
        log.debug('\n%s', pformat(message))

        message_type = message.get('MessageType')
        handler = _handlers.get(message_type)
        if handler:
            data = message.get('Data')
            if data:
                asyncio.get_running_loop().run_in_executor(None, handler, log, player, server, user, data)
    except Exception:
        log.exception('ws message failure')


async def ws_task(player, server: Server, user: User):
    log = logging.getLogger('ws_task')
    log.debug('ws_task started')

    logging.getLogger('websockets.client').setLevel(logging.INFO)

    try:
        url = server.ws_url(user)
        while True:
            try:
                async with websockets.connect(url, compression=None, open_timeout=3, ping_interval=3,
                                              ping_timeout=3, close_timeout=1) as ws:
                    while True:
                        try:
                            message = await ws.recv()
                            await on_ws_message(log, player, server, user, message)
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
        with ThreadPoolExecutor(max_workers=5) as executor:
            loop.set_default_executor(executor)
            loop.run_until_complete(ws_future)
    except Exception:
        log.exception('failed')
    except asyncio.exceptions.CancelledError:
        log.debug('cancelled')
    finally:
        log.debug('exiting')
