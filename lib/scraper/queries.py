from typing import List, Dict, Any, Optional

from lib.api.jellyfin import User, Server

_SONARR_REPLACEMENTS = [
    (': ', ' - '),
    ('?', '!'),
]


def find_by_title(server: Server, user: User, item_type: str, title: str, year: Optional[str]) -> Dict[str, Any]:
    params = {'searchTerm': title, 'Limit': 24, 'Recursive': 'true', 'enableTotalRecordCount': 'true',
              'IncludePeople': 'false', 'IncludeMedia': 'false', 'IncludeGenres': 'false',
              'IncludeStudios': 'false', 'IncludeArtists': 'false', 'IncludeItemTypes': item_type,
              'enableUserData': 'false', 'enableImages': 'false', 'imageTypeLimit': 1}
    if year:
        params['years'] = str(year)
    jf_items = server.get_items(user=user, params=params)

    if not jf_items:
        # Jellyfin doesn't do fuzzy search so handle the various replacements that Sonarr does here
        new_title = title
        for orig, repl in _SONARR_REPLACEMENTS:
            new_title = new_title.replace(repl, orig)
            params['searchTerm'] = new_title
            jf_items = server.get_items(user=user, params=params)
            if jf_items:
                break

    return jf_items


def find_movie_by_title(server: Server, user: User, title: str, year: Optional[str]) -> Dict[str, Any]:
    return find_by_title(server, user, 'Movie', title, year)


def find_series_by_title(server: Server, user: User, title: str, year: Optional[str]) -> Dict[str, Any]:
    return find_by_title(server, user, 'Series', title, year)


def get_item(server: Server, user: User, item_id: str) -> Dict[str, Any]:
    fields = ('AirTime,CustomRating,DateCreated,ExternalUrls,Genres,OriginalTitle'
              ',Overview,Path,People,ProviderIds,Taglines,Tags'
              ',RemoteTrailers,ForcedSortName,Studios,MediaSources')
    params = {'fields': fields, 'imageTypeLimit': 1, 'enableTotalRecordCount': 'true',
              'IncludePeople': 'true', 'IncludeMedia': 'true', 'IncludeGenres': 'true',
              'IncludeStudios': 'true', 'IncludeArtists': 'true',
              'enableUserData': 'true', 'enableImages': 'true', 'ids': item_id}
    jf_items = server.get_items(user, params=params).get('Items')
    if not jf_items:
        raise Exception(f'item with id {item_id} not found')
    return jf_items[0]


def get_items(server: Server, user: User, item_type: str) -> List[Dict[str, Any]]:
    fields = ('AirTime,CustomRating,DateCreated,ExternalUrls,Genres,OriginalTitle'
              ',Overview,Path,People,ProviderIds,Taglines,Tags'
              ',RemoteTrailers,ForcedSortName,Studios,MediaSources')
    params = {'recursive': 'true', 'fields': fields, 'imageTypeLimit': 1, 'enableTotalRecordCount': 'true',
              'IncludePeople': 'true', 'IncludeMedia': 'true', 'IncludeGenres': 'true',
              'IncludeStudios': 'true', 'IncludeArtists': 'true',
              'enableUserData': 'true', 'enableImages': 'true', 'IncludeItemTypes': item_type, 'sortBy': 'SortName'}
    return server.get_items(user, params=params).get('Items') or []


def get_seasons(server: Server, user: User, series_id: str):
    params = {'enableUserData': 'false', 'enableImages': 'true', 'imageTypeLimit': 1}
    return server.get_seasons(user, series_id, params=params)


def seasons_by_series(jf_seasons):
    seasons = {}
    for season in jf_seasons:
        series = seasons.setdefault(season['SeriesId'], [])
        series.append(season)
    return seasons


def get_all_seasons(server: Server, user: User, chunk_size=100):
    params = {'enableUserData': 'false', 'enableImages': 'true', 'imageTypeLimit': 1, 'sortBy': 'PremiereDate'}
    jf_seasons = server.get_seasons(user, chunk_size=chunk_size, params=params).get('Items') or []
    return seasons_by_series(jf_seasons)


def get_episodes(server: Server, user: User, series_id: Optional[str] = None, season_id: Optional[str] = None,
                 chunk_size: Optional[int] = 0) -> Dict[str, Any]:
    fields = ('AirTime,CustomRating,DateCreated,ExternalUrls,Genres,OriginalTitle'
              ',Overview,Path,People,ProviderIds,Taglines,Tags'
              ',RemoteTrailers,ForcedSortName,Studios,MediaSources')
    params = {'fields': fields, 'imageTypeLimit': 1, 'enableTotalRecordCount': 'true',
              'IncludePeople': 'true', 'IncludeMedia': 'true', 'IncludeGenres': 'true',
              'IncludeStudios': 'true', 'IncludeArtists': 'true',
              'enableUserData': 'true', 'enableImages': 'true', 'sortBy': 'PremiereDate', 'userId': user.uuid}
    if season_id:
        params['seasonId'] = season_id
    return server.get_episodes(user, series_id, chunk_size=chunk_size, params=params)


def get_episodes_min(server: Server, user: User, series_id: Optional[str] = None, season_id: Optional[str] = None,
                     chunk_size: Optional[int] = 0) -> Dict[str, Any]:
    params = {'enableTotalRecordCount': 'true',
              'IncludePeople': 'false', 'IncludeMedia': 'false', 'IncludeGenres': 'false',
              'IncludeStudios': 'false', 'IncludeArtists': 'false',
              'enableUserData': 'false', 'enableImages': 'false', 'sortBy': 'PremiereDate', 'userId': user.uuid}
    if season_id:
        params['seasonId'] = season_id
    return server.get_episodes(user, series_id, chunk_size=chunk_size, params=params)


def get_artwork(server: Server, user: User, item_id: str):
    params = {'imageTypeLimit': 1, 'enableTotalRecordCount': 'true',
              'IncludePeople': 'false', 'IncludeMedia': 'false', 'IncludeGenres': 'false',
              'IncludeStudios': 'false', 'IncludeArtists': 'false',
              'enableUserData': 'false', 'enableImages': 'true', 'ids': item_id}
    jf_items = server.get_items(user, params=params).get('Items')
    if not jf_items:
        raise Exception(f'item with id {item_id} not found')
    return jf_items[0]
