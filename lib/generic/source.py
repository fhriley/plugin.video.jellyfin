import logging
from typing import Optional, Dict, List, Any

from lib.generic.api.jellyfin import User, Server

_log = logging.getLogger(__name__)
_user_cache: Optional[Dict[str, User]] = None


def _get_name(title: str, year: Optional[int] = None) -> str:
    if year:
        return f'{title} ({year})'
    return title


class Source:
    def __init__(self, server: Server, debug_level: Optional[int] = 0):
        global _user_cache
        self._server = server
        self._debug_level = debug_level

        if _user_cache is None:
            _user_cache = {}
            _log.debug('creating new user cache')
        else:
            _log.debug('reusing user_cache')

    @property
    def server(self):
        return self._server

    def _get(self, user: User, item_type: str) -> List[Dict[str, Any]]:
        params = {'Recursive': 'true', 'enableTotalRecordCount': 'false',
                  'IncludePeople': 'false', 'IncludeMedia': 'false', 'IncludeGenres': 'false',
                  'IncludeStudios': 'false', 'IncludeArtists': 'false', 'IncludeItemTypes': item_type,
                  'enableUserData': 'false', 'enableImages': 'false','sortBy': 'SortName'}

        jf_items, _, _ = self._server.get_items(user=user, params=params)

        if self._debug_level > 1:
            from pprint import pformat
            _log.debug(f'---------------- START JF {item_type.upper()} ----------------')
            _log.debug(pformat(jf_items))
            _log.debug(f'---------------- END JF {item_type.upper()} ----------------')

        try:
            items = []
            for jf_item in jf_items:
                production_year = jf_item.get('ProductionYear')
                # name = _get_name(jf_item['Name'], production_year)
                item = {'id': jf_item['Id'], 'title': jf_item['Name']}
                if production_year:
                    item['year'] = production_year
                items.append(item)

            if self._debug_level > 1:
                from pprint import pformat
                _log.debug(f'---------------- START {item_type.upper()} ----------------')
                _log.debug(pformat(items))
                _log.debug(f'---------------- END {item_type.upper()} ----------------')

            return items
        except Exception:
            from pprint import pformat
            _log.error(pformat(jf_items))
            raise


class TvShowsSource(Source):
    def get(self, user: User) -> List[Dict[str, Any]]:
        return self._get(user, 'Series')

    def get_seasons(self, user: User, show_id: str) -> List[Dict[str, Any]]:
        params = {'enableUserData': 'false', 'enableImages': 'false', 'sortBy': 'PremiereDate,SortName'}
        jf_seasons = self._server.get_seasons(user, show_id, params=params)
        return [{'number': season['IndexNumber'], 'name': season['Name'], 'id': season['Id']} for season in jf_seasons]

    def get_episodes(self, user: User, show_id: str, season_id: str) -> List[Dict[str, Any]]:
        params = {'seasonId': season_id, 'enableUserData': 'false', 'enableImages': 'false',
                  'sortBy': 'PremiereDate,SortName'}
        jf_episodes = self._server.get_episodes(user, show_id, params=params)
        return [{'number': episode['IndexNumber'], 'name': episode['Name'], 'id': episode['Id'],
                 'season_number': episode['ParentIndexNumber']} for episode in
                jf_episodes]
