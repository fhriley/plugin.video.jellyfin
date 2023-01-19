import logging
from typing import Optional, Dict, Any

import simplejson as json
import xbmc

_get_episode_kodi_id_json_rpc = '''{
    "id": "libTvShows",
    "jsonrpc": "2.0",
    "method": "VideoLibrary.GetEpisodes",
    "params": {
        "filter": {
            "field": "uniqueid_value",
            "operator": "is",
            "value": "%s"
        }
    }
}'''

_get_episode_details_json_rpc = '''{
    "id": "libTvShows",
    "jsonrpc": "2.0",
    "method": "VideoLibrary.GetEpisodeDetails",
    "params": {
        "episodeid": %s,
        "properties": [%s]
    }
}'''

_refresh_episode_json_rpc = '''{
    "id": "libTvShows",
    "jsonrpc": "2.0",
    "method": "VideoLibrary.RefreshEpisode",
    "params": {
        "episodeid": %s,
        "ignorenfo": true
    }
}'''


def json_rpc(log: logging.Logger, command: str) -> Dict[str, Any]:
    log.debug('%s', command)
    resp = xbmc.executeJSONRPC(command)
    return json.loads(resp)


def get_kodi_episode_id(log: logging.Logger, jf_id: str) -> Optional[int]:
    resp = json_rpc(log, _get_episode_kodi_id_json_rpc % jf_id)
    log.debug('%s', resp)
    episodes = (resp.get('result') or {}).get('episodes')
    if not episodes:
        return None
    return episodes[0].get('episodeid')


def get_jf_episode_id(log: logging.Logger, kodi_id: int) -> Optional[str]:
    details = get_kodi_episode_details(log, kodi_id, 'uniqueid')
    return (details.get('uniqueid') or {}).get('jellyfin')


def get_kodi_episode_details(log: logging.Logger, kodi_id: int, *properties) -> Optional[Dict[str, Any]]:
    props = ','.join([f'"{prop}"' for prop in properties])
    resp = json_rpc(log, _get_episode_details_json_rpc % (kodi_id, props))
    log.debug('%s', resp)
    return (resp.get('result') or {}).get('episodedetails')


def refresh_kodi_episode(log: logging.Logger, kodi_id: int):
    json_rpc(log, _refresh_episode_json_rpc % kodi_id)
