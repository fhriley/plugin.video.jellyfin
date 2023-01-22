import datetime
import logging
import uuid
from typing import Union, Callable, Optional

import xbmcaddon
import xbmcvfs


def _to_bool(val: str) -> bool:
    return val == 'true'


def _bool_to_str(val: bool) -> str:
    return 'true' if val else 'false'


class Settings:
    SETTINGS_FILE_NAME = 'settings.json'

    def __init__(self, addon: xbmcaddon.Addon):
        self._log = logging.getLogger(__name__)
        self._addon = addon
        self._profile_dir = xbmcvfs.translatePath(addon.getAddonInfo('profile'))
        if not self.device_id:
            self._addon.setSetting('device_id', uuid.uuid4().hex)
        try:
            self._scraper_debug_level = self.get_int('scraper_debug')
        except Exception:
            self._scraper_debug_level = 0

    def update_logger(self):
        self._log = logging.getLogger(__name__)

    def get(self, key: str, convert: Callable[[str], Union[str, bool, int]] = str) -> Union[str, bool, int]:
        return convert(self._addon.getSetting(key))

    def get_bool(self, key: str) -> bool:
        return self.get(key, _to_bool)

    def get_int(self, key: str) -> bool:
        return self.get(key, int)

    def set(self, key: str, val, convert: Callable = str):
        self._addon.setSetting(key, convert(val))

    def set_bool(self, key: str, val: bool):
        self.set(key, _bool_to_str(val))

    @property
    def profile_dir(self):
        return self._profile_dir

    @property
    def client_name(self):
        return 'Kodi Jellyfin Scraper'

    @property
    def device_id(self):
        return self._addon.getSetting('device_id')

    @property
    def scraper_debug_level(self):
        return self._scraper_debug_level

    @property
    def service_debug_level(self):
        return self.get_int('service_debug')

    @property
    def service_log_level(self):
        return logging.DEBUG if self.service_debug_level > 0 else logging.INFO

    @property
    def last_sync_time(self) -> Optional[datetime.datetime]:
        dt = self._addon.getSetting('last_sync_time')
        if dt:
            return datetime.datetime.fromisoformat(dt)
        return None

    @last_sync_time.setter
    def last_sync_time(self, value: datetime.datetime):
        current = self.last_sync_time
        if current is None or value > current:
            self._addon.setSetting('last_sync_time', value.isoformat())
