import logging
from concurrent.futures import ThreadPoolExecutor
from pprint import pformat

import simplejson as json

import websocket
from lib.api.jellyfin import Server, User
from lib.service.entrypoint import PlaybackMonitor
from lib.service.json_rpc import get_kodi_episode_id, refresh_kodi_episode
from lib.service.queries import get_item

_user_data_changed_handlers = {
    'Episode': (get_kodi_episode_id, refresh_kodi_episode)
}


def user_data_changed(log: logging.Logger, player: PlaybackMonitor, server: Server, user: User, data):
    log.debug("user_data_changed handler")
    for item_info in data.get('UserDataList') or []:
        item_id = item_info.get('ItemId')
        if not item_id:
            log.warning('got user data change with no ItemId')
            return

        if player.playing_state and item_id == player.playing_state.jf_id:
            log.debug('%s is currently playing, skipping', item_id)
            continue

        jf_item = get_item(server, user, item_id)
        if log.isEnabledFor(logging.DEBUG):
            log.debug('%s', pformat(jf_item))

        jf_item_type = jf_item.get('Type')
        funcs = _user_data_changed_handlers.get(jf_item_type)

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


def library_changed(log: logging.Logger, player: PlaybackMonitor, server: Server, user: User, data):
    log.debug("library_changed handler")


_handlers = {
    'UserDataChanged': user_data_changed,
    'LibraryChanged': library_changed,
}


def on_ws_message(log: logging.Logger, executor: ThreadPoolExecutor, player: PlaybackMonitor, server: Server,
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
                executor.submit(handler, log, player, server, user, data)
    except Exception:
        log.exception('ws message failure')


def on_ws_error(log: logging.Logger, message: str):
    log.error('%s', message)


def ws_app_loop(log: logging.Logger, wsapp: websocket.WebSocketApp):
    log.debug('ws thread started')
    try:
        wsapp.run_forever(reconnect=1)
    except Exception:
        log.exception('wsapp.run_forever() failed')
