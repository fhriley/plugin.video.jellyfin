import logging
from pprint import pformat
from typing import Optional, Dict, Any, Tuple

import simplejson as json
import xbmc

from lib.util.exceptions import NotFound


def json_rpc(log: logging.Logger, method: str, id: Optional[str] = None, **params) -> Optional[Dict[str, Any]]:
    command = {'jsonrpc': '2.0', 'method': method, 'params': params}
    if id:
        command['id'] = id
    if log.isEnabledFor(logging.DEBUG):
        log.debug('%s', pformat(command))
    resp = xbmc.executeJSONRPC(json.dumps(command))
    if resp:
        return json.loads(resp)


def _get_kodi_id(log: logging.Logger, jf_id: str, lib_id: str, method: str, result_key: str, id_key: str) -> int:
    resp = json_rpc(log, method, id=lib_id, filter={
        'field': 'uniqueid_value',
        'operator': 'is',
        'value': jf_id,
    })
    log.debug('%s', resp)
    items = (resp.get('result') or {}).get(result_key)
    if not items:
        raise NotFound('%s not found', jf_id)
    return items[0].get(id_key)


def get_kodi_episode_id(log: logging.Logger, jf_id: str) -> int:
    return _get_kodi_id(log, jf_id, 'libTvShows', 'VideoLibrary.GetEpisodes', 'episodes', 'episodeid')


def get_kodi_tvshow_id(log: logging.Logger, jf_id: str) -> int:
    return _get_kodi_id(log, jf_id, 'libTvShows', 'VideoLibrary.GetTvShows', 'tvshows', 'tvshowid')


def get_kodi_movie_id(log: logging.Logger, jf_id: str) -> int:
    return _get_kodi_id(log, jf_id, 'libMovies', 'VideoLibrary.GetMovies', 'movies', 'movieid')


def get_kodi_id(log: logging.Logger, jf_id: str) -> Tuple[int, str]:
    for lib_id, method, result_key, id_key, typ in (
            ('libMovies', 'VideoLibrary.GetMovies', 'movies', 'movieid', 'movie'),
            ('libTvShows', 'VideoLibrary.GetEpisodes', 'episodes', 'episodeid', 'episode'),
            ('libTvShows', 'VideoLibrary.GetTVShows', 'tvshows', 'tvshowid', 'tvshow')
    ):
        try:
            return _get_kodi_id(log, jf_id, lib_id, method, result_key, id_key), typ
        except NotFound:
            pass
    raise NotFound('%s not found', jf_id)


def _get_kodi_details(log: logging.Logger, kodi_id: int, lib_id: str, method: str, id_key: str, result_key: str,
                      *properties) -> Optional[Dict[str, Any]]:
    kwargs = {
        id_key: kodi_id,
    }
    if properties:
        kwargs['properties'] = properties
    resp = json_rpc(log, method, id=lib_id, **kwargs)
    log.debug('%s', resp)
    return (resp.get('result') or {}).get(result_key)


def get_kodi_episode_details(log: logging.Logger, kodi_id: int, *properties) -> Optional[Dict[str, Any]]:
    return _get_kodi_details(log, kodi_id, 'libTvShows', 'VideoLibrary.GetEpisodeDetails', 'episodeid',
                             'episodedetails', *properties)


def get_kodi_movie_details(log: logging.Logger, kodi_id: int, *properties) -> Optional[Dict[str, Any]]:
    return _get_kodi_details(log, kodi_id, 'libMovies', 'VideoLibrary.GetMovieDetails', 'movieid', 'moviedetails',
                             *properties)


def _get_jf_id(log: logging.Logger, kodi_id: int, lib_id: str, method: str, id_key: str, result_key: str):
    details = _get_kodi_details(log, kodi_id, lib_id, method, id_key, result_key, 'uniqueid')
    return (details.get('uniqueid') or {}).get('jellyfin')


def get_jf_episode_id(log: logging.Logger, kodi_id: int) -> Optional[str]:
    return _get_jf_id(log, kodi_id, 'libTvShows', 'VideoLibrary.GetEpisodeDetails', 'episodeid', 'episodedetails')


def get_jf_tvshow_id(log: logging.Logger, kodi_id: int) -> Optional[str]:
    return _get_jf_id(log, kodi_id, 'libTvShows', 'VideoLibrary.GetTvShowDetails', 'tvshowid', 'tvshowdetails')


def get_jf_movie_id(log: logging.Logger, kodi_id: int) -> Optional[str]:
    return _get_jf_id(log, kodi_id, 'libMovies', 'VideoLibrary.GetMovieDetails', 'movieid', 'moviedetails')


def refresh_kodi_episode(log: logging.Logger, kodi_id: int):
    json_rpc(log, 'VideoLibrary.RefreshEpisode', id='libTvShows', episodeid=kodi_id, ignorenfo=True)


def refresh_kodi_tvshow(log: logging.Logger, kodi_id: int):
    json_rpc(log, 'VideoLibrary.RefreshTvShow', id='libTvShows', tvshowid=kodi_id, ignorenfo=True,
             refreshepisodes=False)


def refresh_kodi_movie(log: logging.Logger, kodi_id: int):
    json_rpc(log, 'VideoLibrary.RefreshMovie', id='libMovies', movieid=kodi_id, ignorenfo=True)


def remove_kodi_episode(log: logging.Logger, kodi_id: int):
    json_rpc(log, 'VideoLibrary.RemoveEpisode', id='libTvShows', episodeid=kodi_id)


def remove_kodi_tvshow(log: logging.Logger, kodi_id: int):
    json_rpc(log, 'VideoLibrary.RemoveTVShow', id='libMovies', tvshowid=kodi_id)


def remove_kodi_movie(log: logging.Logger, kodi_id: int):
    json_rpc(log, 'VideoLibrary.RemoveMovie', id='libMovies', movieid=kodi_id)


def scan_kodi(log: logging.Logger, directory: Optional[str] = None):
    kwargs = {
        'showdialogs': False,
    }
    if directory:
        kwargs['directory'] = directory
    json_rpc(log, 'VideoLibrary.Scan', **kwargs)
