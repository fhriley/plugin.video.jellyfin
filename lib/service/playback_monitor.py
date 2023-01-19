import logging
import os
from typing import Optional

import xbmc
import xbmcgui

from lib.api.jellyfin import Server, User
from lib.service.json_rpc import get_kodi_episode_details
from lib.util.util import get_jf_id_from_list_item


class PlayingState:
    def __init__(self, start_s: float, list_item: xbmcgui.ListItem):
        self._start_s = start_s
        self._jf_id = get_jf_id_from_list_item(list_item) or None
        tag: xbmc.InfoTagVideo = list_item.getVideoInfoTag()
        self._kodi_id = tag.getDbId()
        self._playcount = tag.getPlayCount()

    @property
    def start_s(self):
        return self._start_s

    @property
    def kodi_id(self) -> int:
        return self._kodi_id

    @property
    def jf_id(self) -> Optional[str]:
        return self._jf_id

    @property
    def playcount(self) -> int:
        return self._playcount


class PlaybackMonitor(xbmc.Player):
    def __init__(self, server: Server, user: User):
        super().__init__()
        self._log = logging.getLogger(__name__)
        self._server = server
        self._user = user
        self._playing_state: Optional[PlayingState] = None
        self._latest_time = 0

    @property
    def playing_state(self) -> Optional[PlayingState]:
        return self._playing_state

    def isPlaying(self) -> bool:
        if os.environ.get('NOT_IN_KODI'):
            return False
        else:
            return super().isPlaying()

    def getTime(self) -> float:
        try:
            self._latest_time = super().getTime()
        except Exception:
            self._log.exception('getTime failed')
        return self._latest_time

    def onPlayBackStarted(self):
        self._log.debug('onPlayBackStarted()')
        try:
            self._playing_state = PlayingState(self.getTime(), self.getPlayingItem())
            if self._playing_state.jf_id:
                self._log.debug('playing jf_id=%s kodi_id=%s', self._playing_state.jf_id, self._playing_state.kodi_id)
                self._server.send_playback_started(self._user, self._playing_state.jf_id, self._playing_state.start_s)
            else:
                self._log.warning('no jellyfin id for item id %s', self._playing_state.kodi_id)
        except Exception:
            self._log.exception('onPlayBackStarted failed')

    def onPlayBackEnded(self):
        self._log.debug('onPlayBackEnded()')
        self.onPlayBackStopped()

    def onPlayBackStopped(self):
        self._log.debug('onPlayBackStopped()')
        try:
            if self._playing_state and self._playing_state.jf_id:
                details = get_kodi_episode_details(self._log, self._playing_state.kodi_id, 'playcount', 'resume')
                playcount = details.get('playcount')
                position = (details.get('resume') or {}).get('position', None)
                self._server.send_playback_stopped(self._user, self._playing_state.jf_id, position)
                if playcount is not None and playcount != self._playing_state.playcount:
                    if playcount > 0:
                        self._server.mark_watched(self._user, self._playing_state.jf_id)
                    else:
                        self._server.mark_unwatched(self._user, self._playing_state.jf_id)
            self._playing_state = None
        except Exception:
            self._log.exception('onPlayBackStopped failed')

    def onPlayBackError(self):
        self._log.debug('onPlayBackError()')
        self.onPlayBackStopped()

    def onPlayBackPaused(self):
        self._log.debug('onPlayBackPaused()')
        try:
            if self._playing_state and self._playing_state.jf_id:
                self._server.send_playback_paused(self._user, self._playing_state.jf_id, self.getTime())
        except Exception:
            self._log.exception('onPlayBackPaused failed')

    def onPlayBackResumed(self):
        self._log.debug('onPlayBackResumed()')
        try:
            if self._playing_state and self._playing_state.jf_id:
                self._server.send_playback_unpaused(self._user, self._playing_state.jf_id, self.getTime())
        except Exception:
            self._log.exception('onPlayBackResumed failed')

    def onPlayBackSeek(self, time, seekOffset):
        time /= 1000.0
        seekOffset /= 1000.0
        self._log.debug('onPlayBackSeek(%s, %s)', time, seekOffset)
        try:
            self._latest_time = time
            if self._playing_state and self._playing_state.jf_id:
                self._server.send_playback_time(self._user, self._playing_state.jf_id, time)
        except Exception:
            self._log.exception('onPlayBackSeek failed')
