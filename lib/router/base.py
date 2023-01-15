import logging
import os
from pprint import pformat
from typing import Optional

import xbmcaddon
import xbmcgui
import xbmcplugin

from lib.api.jellyfin import authenticate, Server, User
from lib.builder.base import Builder
from lib.scraper.base import Scraper
from lib.scraper.queries import find_by_title, get_artwork
from lib.util import util
from lib.util.settings import Settings

_log = logging.getLogger(__name__)


class Router:
    _user_cache = None

    def __init__(self, settings: Settings, handle: int, addon: xbmcaddon.Addon, server: Server,
                 debug_level: Optional[int] = 0):
        self._server = server
        self._settings = settings
        self._handle = handle
        self._addon = addon
        self._debug_level = debug_level
        if self._user_cache is None:
            self._user_cache = {}

    def execute(self, scraper: Scraper, builder: Builder, params: dict):
        _log.debug('execute: params=%s server=%s', params, self._server)

        try:
            action = params.get('action')
            if not action:
                _log.debug('no action provided')
                return

            func = getattr(self, action)
            if func:
                user = authenticate(self._server, self._user_cache, self._settings.get('username'),
                                    self._settings.get('password'))
                _log.debug('execute: start executing %s()', func.__name__)
                func(user, scraper, builder, params)
                _log.debug('execute: finished executing %s()', func.__name__)
            else:
                _log.debug('execute: action %s not implemented', action)
        except Exception:
            _log.error('execute: params=%s server=%s', params, self._server)
            raise

    def find(self, user: User, scraper: Scraper, builder: Builder, params: dict):
        try:
            title = params.get('title')
            if not title:
                raise Exception('find: no title provided')
            year = params.get('year')
            _log.debug('find: title="%s" year=%s', title, year)
            jf_items = find_by_title(self._server, user, scraper.jf_item_type, title, year).get('Items') or []
            items = scraper.scrape_find(jf_items)
            if _log.isEnabledFor(logging.DEBUG):
                _log.debug('find result:%s%s', os.linesep, pformat(items))
            builder.build_find_directory(items)
        except Exception:
            xbmcplugin.endOfDirectory(handle=self._handle, succeeded=False)
            raise

    def getartwork(self, user: User, scraper: Scraper, builder: Builder, params: dict):
        try:
            in_params = util.get_params_from_url('getartwork', params, ('id',))
            _log.debug('getartwork: in_params=%s', in_params)
            jellyfin_id = in_params['id']
            jf_artwork = get_artwork(self._server, user, jellyfin_id)
            artwork = scraper.scrape_artwork(jf_artwork)
            builder.build_artwork(jellyfin_id, artwork)
        except Exception:
            xbmcplugin.setResolvedUrl(handle=self._handle, succeeded=False, listitem=xbmcgui.ListItem(offscreen=True))
            raise

    def nfourl(self, user: User, scraper: Scraper, builder: Builder, params: dict):
        xbmcplugin.endOfDirectory(handle=self._handle, succeeded=False)
