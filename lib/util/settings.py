import logging
import os.path
import uuid
from typing import Union, Callable

import simplejson as json
import xbmcaddon
import xbmcvfs

_log = logging.getLogger(__name__)


def _to_bool(val: str) -> bool:
    return val == 'true'


def _bool_to_str(val: bool) -> str:
    return 'true' if val else 'false'


def load_settings_file(path):
    if os.path.isfile(path):
        try:
            with open(path, 'r') as in_file:
                return json.load(in_file)
        except Exception as exc:
            _log.warning(f'failed to open settings file "{path}": {exc}')
            try:
                os.remove(path)
            except Exception as exc:
                _log.warning(f'failed to delete settings file "{path}": {exc}')

    settings = {'device_id': uuid.uuid4().hex}

    try:
        with open(path, 'w') as out_file:
            json.dump(settings, out_file)
    except Exception as exc:
        _log.warning(f'failed to save settings file "{path}": {exc}')

    return settings


class Settings:
    SETTINGS_FILE_NAME = 'settings.json'

    def __init__(self, addon: xbmcaddon.Addon):
        self._addon = addon
        self._profile_dir = xbmcvfs.translatePath(addon.getAddonInfo('profile'))
        self._settings = load_settings_file(os.path.join(self._profile_dir, self.SETTINGS_FILE_NAME))
        try:
            self._debug_level = self.get_int('debug')
        except Exception:
            self._debug_level = 0

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
        return self._settings['device_id']

    @property
    def debug_level(self):
        return self._debug_level
