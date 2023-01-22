import logging
import os
import xml.etree.ElementTree as ET
from pprint import pformat
from typing import Optional, Dict

import xbmcaddon
import xbmcgui
import xbmcplugin

from lib.api.jellyfin import authenticate, Server, User
from lib.builder.base import Builder
from lib.scraper.base import Scraper
from lib.scraper.queries import find_by_title, get_artwork
from lib.util import util
from lib.util.settings import Settings

# Global so it gets reused between invocations of the interpreters
_user_cache: Optional[Dict[str, User]] = None


def parse_nfo(log: logging.Logger, xml: str):
    root = ET.fromstring(xml)
    if root.tag not in ('movie', 'tvshow', 'episodedetails'):
        raise Exception('invalid nfo')

    vals = {child.tag: child.text for child in root}
    vals['type'] = root.tag
    log.debug('%s', vals)

    title = vals.get('title')
    if not title:
        raise Exception('no "title" in nfo')

    year = vals.get('year')
    if not year:
        raise Exception('no "year" in nfo')

    try:
        vals['year'] = int(year)
    except ValueError:
        raise Exception('invalid "year" in nfo')

    return vals


class Router:
    def __init__(self, settings: Settings, handle: int, addon: xbmcaddon.Addon, server: Server,
                 debug_level: Optional[int] = 0):
        global _user_cache
        self._server = server
        self._settings = settings
        self._handle = handle
        self._addon = addon
        self._debug_level = debug_level
        if _user_cache is None:
            _user_cache = {}
        self._log = logging.getLogger(__name__)

    def execute(self, scraper: Scraper, builder: Builder, params: dict):
        self._log.debug('execute: params=%s server=%s', params, self._server)
        global _user_cache

        try:
            action = params.get('action')
            if not action:
                self._log.debug('no action provided')
                return

            action = action.lower()
            func = getattr(self, action)
            if func:
                user = authenticate(self._server, _user_cache, self._settings.get('username'),
                                    self._settings.get('password'))
                self._log.debug('execute: start executing %s()', func.__name__)
                func(user, scraper, builder, params)
                self._log.debug('execute: finished executing %s()', func.__name__)
            else:
                self._log.debug('execute: action %s not implemented', action)
        except Exception:
            self._log.error('execute: params=%s server=%s', params, self._server)
            raise

    def find(self, user: User, scraper: Scraper, builder: Builder, params: dict):
        try:
            title = params.get('title')
            if not title:
                raise Exception('find: no title provided')
            year = params.get('year')
            self._log.debug('find: title="%s" year=%s', title, year)
            jf_items = find_by_title(self._server, user, scraper.jf_item_type, title, year).get('Items') or []
            items = scraper.scrape_find(jf_items)
            if self._log.isEnabledFor(logging.DEBUG):
                self._log.debug('find result:%s%s', os.linesep, pformat(items))
            builder.build_find_directory(items)
        except Exception:
            xbmcplugin.endOfDirectory(handle=self._handle, succeeded=False)
            raise

    def getartwork(self, user: User, scraper: Scraper, builder: Builder, params: dict):
        try:
            in_params = util.get_args_from_params(self._log, 'getartwork', params, ('id',))
            self._log.debug('getartwork: in_params=%s', in_params)
            jellyfin_id = in_params['id']
            jf_artwork = get_artwork(self._server, user, jellyfin_id)
            artwork = scraper.scrape_artwork(jf_artwork)
            builder.build_artwork(jellyfin_id, artwork)
        except Exception:
            xbmcplugin.setResolvedUrl(handle=self._handle, succeeded=False, listitem=xbmcgui.ListItem(offscreen=True))
            raise

    def nfourl(self, user: User, scraper: Scraper, builder: Builder, params: dict):
        try:
            self._log.debug('nfourl: in_params=%s', params)
            nfo = params.get('nfo')
            if not nfo:
                raise Exception('invalid nfo')
            vals = parse_nfo(self._log, nfo)
            jf_items = find_by_title(self._server, user, scraper.jf_item_type, vals['title'], vals['year']).get(
                'Items') or []
            items = scraper.scrape_find(jf_items)
            if self._log.isEnabledFor(logging.DEBUG):
                self._log.debug('find result:%s%s', os.linesep, pformat(items))
            builder.build_find_directory(items)
        except Exception:
            xbmcplugin.endOfDirectory(handle=self._handle, succeeded=False)
            raise
