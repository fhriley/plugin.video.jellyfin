import logging
import sys
import traceback
from typing import Optional, Dict, Any
from urllib.parse import urlparse, unquote_plus, parse_qsl

import requests
import xbmc
import xbmcaddon

import lib.scraper.queries as queries
from lib.api.jellyfin import Server, User, authenticate
from lib.builder.movies import MoviesBuilder
from lib.builder.tvshows import TvShowsBuilder
from lib.scraper.movies import MoviesScraper
from lib.scraper.tvshows import TvShowsScraper
from lib.util.log import KodiHandler, LOG_FORMAT
from lib.util.settings import Settings
from lib.util.util import get_server

_session: Optional[requests.Session] = None
_user_cache: Optional[Dict[str, User]] = None
_plugin_name = 'plugin.video.jellyfin'
_library_prefix = '/library'
_tvshows_prefix = f'{_library_prefix}/tvshows/'
_valid_cmds = {'plugin://{_plugin_name}{_tvshows_prefix}/'}


# plugin://plugin.video.jellyfin/library/tvshows

def get_params() -> dict:
    param_string = sys.argv[2][1:]
    if param_string:
        return dict(parse_qsl(param_string))
    return {}


# def play_item(log: logging.Logger, handle: int, item: Dict[str, Any]):
#     log.debug('Playing %s', pformat(item))
#     path = item['Path']
#     list_item = xbmcgui.ListItem(path=path)
#     list_item.setProperty('IsPlayable', 'true')
#
#     runtime_ticks = item.get('RunTimeTicks')
#     if runtime_ticks:
#         tag = list_item.getVideoInfoTag()
#         duration = ticks_to_seconds(runtime_ticks)
#         play_pos_ticks = (item.get('UserData') or {}).get('PlaybackPositionTicks', 0)
#         resume_time = play_pos_ticks / runtime_ticks * duration
#         resume_time = 31.3
#         log.debug('duration=%.1f resume=%.1f', duration, resume_time)
#         tag.setResumePoint(resume_time, duration)
#         #tag.setDuration(int(math.ceil(duration)))
#         #list_item.setProperty('StartOffset', '-1')
#
#     xbmcplugin.setResolvedUrl(handle, succeeded=True, listitem=list_item)
#
#     player = xbmc.Player()
#     if not player.isPlaying():
#         player.play(path, list_item)


def play_item(log: logging.Logger, handle: int, item: Dict[str, Any]):
    url = 'http://localhost:8080/jsonrpc'


def play_tvshow(log: logging.Logger, handle: int, server: Server, user: User, series_id: str, episode_id: str,
                path: str):
    episode = server.get_episode(user, series_id, episode_id,
                                 params={'fields': 'Path', 'enableUserData': 'true'})
    play_item(log, handle, episode)


def play_movie(log: logging.Logger, handle: int, server: Server, user: User, movie_id: str):
    movie = server.get_item(user, movie_id, params={'fields': 'Path', 'enableUserData': 'true'})
    play_item(log, handle, movie)


def main(*args):
    # xbmc.log('============================ start', xbmc.LOGINFO)
    global _session
    global _user_cache

    command = args[0]
    handle = int(args[1])

    log = None

    try:
        addon = xbmcaddon.Addon()
        settings = Settings(addon)

        level = logging.DEBUG if settings.scraper_debug_level > 0 else logging.INFO
        logging.basicConfig(format=LOG_FORMAT, level=level, handlers=[KodiHandler()])

        log = logging.getLogger(__name__)
        log.debug('============================ start debug_level=%s', settings.scraper_debug_level)

        if level == logging.DEBUG:
            for ii, arg in enumerate(args):
                log.debug('argv[%d]="%s"', ii, arg)

        if _session is None:
            _session = requests.Session()
            log.debug('creating new session')
        else:
            log.debug('reusing session')

        if _user_cache is None:
            _user_cache = {}

        server = get_server(_session, settings, addon, settings.scraper_debug_level)
        user = authenticate(server, _user_cache, settings.get('username'), settings.get('password'))

        parsed = urlparse(command)
        split_path = parsed.path.lstrip('/').rstrip('/').split('/')
        if len(split_path) < 2:
            log.warning('unknown command: %s', command)
            return

        if split_path[1] == 'tvshows':
            if len(split_path) == 4:
                series_id = unquote_plus(split_path[2])
                episode_id = unquote_plus(split_path[3])
                play_tvshow(log, handle, server, user, series_id, episode_id, parsed.path)
            else:
                scraper = TvShowsScraper(server, debug_level=0)
                builder = TvShowsBuilder(settings, handle, addon)
                if len(split_path) == 2:
                    jf_shows = queries.get_items(server, user, 'Series').get('Items') or []
                    jf_seasons = queries.get_all_seasons(server, user).get('Items') or []
                    shows = scraper.scrape_shows(jf_shows, jf_seasons)
                    shows = [show for show in shows if show['info']['title'] == 'The Flight Attendant']
                    builder.build_directory(shows)
                elif len(split_path) == 3:
                    series_id = unquote_plus(split_path[2])
                    episodes = scraper.get_episodes(user, series_id)
                    builder.build_episodes(episodes)

        elif split_path[1] == 'movies':
            if len(split_path) == 3:
                movie_id = unquote_plus(split_path[2])
                play_movie(log, handle, server, user, movie_id)
            else:
                scraper = MoviesScraper(server, debug_level=0)
                builder = MoviesBuilder(settings, handle, addon)
                if len(split_path) == 2:
                    jf_movies = queries.get_items(server, user, 'Movie').get('Items') or []
                    movies = scraper.scrape_movies(jf_movies)
                    movies = [movie for movie in movies if movie['info']['title'] == 'Avatar']
                    builder.build_directory(movies)

        log.debug('============================ finish')
    except Exception:
        try:
            if log:
                log.exception('main failed')
            else:
                xbmc.log(f'main failed: {traceback.format_exc()}', xbmc.LOGERROR)
        except Exception:
            pass
