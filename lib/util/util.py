import logging
from typing import Iterable, Optional
from urllib.parse import urlparse, parse_qs, urlencode, quote_plus

import xbmcaddon

_log = logging.getLogger(__name__)


def get_plugin_url(addon: xbmcaddon.Addon, *args, **kwargs):
    path = '/'.join([quote_plus(arg) for arg in args])
    if kwargs:
        param_str = f'?{urlencode(kwargs)}'
    else:
        param_str = ''
    return f'plugin://{addon.getAddonInfo("id")}/{path}{param_str}'


def get_args_from_params(msg: str, params: dict, keys: Optional[Iterable[str]]) -> dict:
    url = params.get('url')
    if  url:
        parsed = urlparse(url)
        qs = parse_qs(parsed.query)
    else:
        url = params.get('id')
        if url is None:
            raise Exception(f'{msg}: no url/id provided')
        qs = {'id': [url]}

    _log.debug('get_args_from_params: qs=%s', qs)

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
