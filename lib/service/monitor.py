import logging
import os
import time
from pprint import pformat
from typing import Callable, Dict, Any

import simplejson as json
import xbmc

from lib.api.jellyfin import Server, User
from lib.service.json_rpc import get_jf_episode_id, get_jf_movie_id, get_jf_tvshow_id, get_kodi_episode_details, \
    get_kodi_movie_details
from lib.util.settings import Settings


class Monitor(xbmc.Monitor):
    def __init__(self, settings: Settings, server: Server, user: User, on_quit: Callable):
        super().__init__()
        self._log = logging.getLogger(__name__)
        self._settings = settings
        self._server = server
        self._user = user
        self._on_quit = on_quit
        self._handlers = {
            ('xbmc', 'VideoLibrary.OnUpdate'): self._videolibrary_on_update,
            ('xbmc', 'VideoLibrary.OnScanStarted'): self._videolibrary_on_scan_started,
        }

    def onNotification(self, sender: str, method: str, data: str):
        self._log.debug('onNotification: sender=%s, method=%s', sender, method)
        if self._log.isEnabledFor(logging.DEBUG) and data:
            self._log.debug('%s%s', os.linesep, pformat(json.loads(data)))
        try:
            handler: Callable = self._handlers.get((sender, method))
            if handler:
                message = json.loads(data)
                handler(message)
        except Exception:
            self._log.exception('onNotification failed')

    def _videolibrary_on_update(self, message: Dict[str, Any]):
        if message.get('added'):
            return
        playcount = message.get('playcount')
        if playcount is None:
            return

        item = message.get('item') or {}
        kodi_id = item.get('id')
        kodi_type = item.get('type')
        playcount = message.get('playcount', 0)
        if not kodi_id:
            self._log.warning('no item id in notification')
            return
        if not kodi_type:
            self._log.warning('no item type in notification')
            return

        if kodi_type not in ('episode', 'movie'):
            self._log.debug('ignoring item type %s', kodi_type)
            return

        jf_id = None
        details = None
        if kodi_type == 'episode':
            jf_id = get_jf_episode_id(self._log, kodi_id)
            details = get_kodi_episode_details(self._log, kodi_id, 'playcount')
        elif kodi_type == 'movie':
            jf_id = get_jf_movie_id(self._log, kodi_id)
            details = get_kodi_movie_details(self._log, kodi_id, 'playcount')
        if not jf_id:
            self._log.warning('no jellyfin id in kodi db')
            return

        self._log.debug('%s', jf_id)

        current_playcount = None
        if details:
            current_playcount = details.get('playcount')
            self._log.debug('current_playcount=%s new_playcount=%s', current_playcount, playcount)

        if playcount != current_playcount:
            if playcount > 0:
                self._server.mark_watched(self._user, jf_id)
            else:
                self._server.mark_unwatched(self._user, jf_id)
        else:
            self._log.debug('playcount unchanged')

    def _videolibrary_on_scan_started(self, _: Dict[str, Any]):
        self._settings.last_sync_time = self._server.get_server_time()

    def abortRequested(self):
        if os.environ.get('NOT_IN_KODI'):
            return False
        else:
            return super().abortRequested()

    def waitForAbort(self, timeout: float = None) -> bool:
        if os.environ.get('NOT_IN_KODI'):
            time.sleep(timeout)
        else:
            return super().waitForAbort(timeout)
