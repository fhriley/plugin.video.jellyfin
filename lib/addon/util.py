import logging
from typing import Iterable, Optional
from urllib.parse import urlparse, parse_qs, urlencode

import xbmcaddon

_log = logging.getLogger(__name__)


def get_plugin_url(addon: xbmcaddon.Addon, **kwargs):
    if kwargs:
        param_str = urlencode(kwargs)
    else:
        param_str = ''
    return f'plugin://{addon.getAddonInfo("id")}?{param_str}'


def get_params_from_url(msg: str, params: dict, keys: Optional[Iterable[str]]) -> dict:
    url = params.get('url') or params.get('id')
    if not url:
        raise Exception(f'{msg}: no url/id provided')

    parsed = urlparse(url)
    qs = parse_qs(parsed.query)

    _log.debug('get_params_from_url: qs=%s', qs)

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
