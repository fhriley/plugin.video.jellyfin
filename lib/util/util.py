import logging
from typing import Iterable, Optional
from urllib.parse import urlparse, parse_qs, urlencode, quote_plus, unquote_plus
import os

import requests
import xbmc
import xbmcaddon
import xbmcgui

from lib.api.jellyfin import Server
from lib.util.settings import Settings


def ticks_to_seconds(ticks: int) -> float:
    return max(ticks, 0) * 1e-7


def get_server(session: requests.Session, settings: Settings, addon: xbmcaddon.Addon) -> Server:
    server_url = unquote_plus(settings.get('serverurl')) or os.environ.get('SERVERURL') or ''
    device_name = xbmc.getInfoLabel('System.FriendlyName') or os.environ.get('DEVICENAME') or ''
    version = addon.getAddonInfo('version') or '0.0.1'
    verify_cert = settings.get_bool('sslverify')
    return Server(session, server_url, settings.client_name, device_name, settings.device_id, version, verify_cert,
                  log_raw_resp=settings.debug_level > 2)


def get_plugin_url(addon: xbmcaddon.Addon, *args, **kwargs):
    path = '/'.join([quote_plus(arg) for arg in args])
    if kwargs:
        param_str = f'?{urlencode(kwargs)}'
    else:
        param_str = ''
    return f'plugin://{addon.getAddonInfo("id")}/{path}{param_str}'


def get_args_from_params(log: logging.Logger, msg: str, params: dict, keys: Optional[Iterable[str]]) -> dict:
    url = params.get('url')
    if url:
        parsed = urlparse(url)
        qs = parse_qs(parsed.query)
    else:
        url = params.get('id')
        if url is None:
            raise Exception(f'{msg}: no url/id provided')
        qs = {'id': [url]}

    log.debug('get_args_from_params: qs=%s', qs)

    ret = {'url': url}

    if keys:
        for key in keys:
            vals = qs.get(key)
            if not vals:
                raise Exception(f'{msg}: no "{key}" provided in {url}')
            ret[key] = vals[0]
    else:
        for key, vals in qs.items():
            ret[key] = vals[0]

    return ret


def get_jf_id_from_list_item(list_item: xbmcgui.ListItem) -> str:
    tag: xbmc.InfoTagVideo = list_item.getVideoInfoTag()
    return tag.getUniqueID('jellyfin')
