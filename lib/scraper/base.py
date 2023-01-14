import datetime
import logging
import time
from abc import ABC, abstractmethod
from math import ceil
from typing import Optional, Dict, List, Tuple, Any
from urllib.parse import urlparse, parse_qs

from lib.api.jellyfin import Server, User

_log = logging.getLogger(__name__)


class ProxyDatetime(datetime.datetime):
    @classmethod
    def strptime(cls, date_string, fmt):
        return datetime.datetime(*(time.strptime(date_string, fmt)[:6]))


datetime.datetime = ProxyDatetime

_artwork = {
    'Primary': ['poster', 'thumb'],
    'Banner': ['banner'],
    'Art': ['clearart'],
    'Logo': ['clearlogo'],
    'Disc': ['discart'],
    'Backdrop': ['fanart'],
    'Thumb': ['landscape'],
}


def _ticks_to_seconds(ticks: int) -> float:
    return ticks * 100e-9


def get_artwork_from_item(server: Server, item: dict, artwork_map: Dict[str, List[str]] = None) -> Dict[str, str]:
    if artwork_map is None:
        artwork_map = _artwork
    artwork = {}
    tags = item.get('ImageTags') or {}
    for image_type, tag in tags.items():
        kodi_keys = artwork_map.get(image_type) or []
        for key in kodi_keys:
            artwork[key] = server.image_url(item['Id'], image_type, params={'tag': tag})
    return artwork


def _get_name(title: str, year: Optional[int] = None) -> str:
    if year:
        return f'{title} ({year})'
    return title


def get_people(server: Server, jf_item: dict) -> Tuple[List, List, List]:
    cast = []
    guest_stars = []
    directors = []
    writers = []

    for ii, jf_person in enumerate(jf_item.get('People') or []):
        person = {
            'name': jf_person['Name'],
        }

        role = jf_person.get('Role')
        if role:
            person['role'] = role

        image_tag = jf_person.get('PrimaryImageTag')
        if image_tag:
            person['thumb'] = server.image_url(jf_person['Id'], 'Primary', params={'tag': image_tag})

        typ = jf_person.get('Type')
        if typ == 'Actor':
            cast.append(person)
        elif typ == 'GuestStar':
            guest_stars.append(person)
        elif typ == 'Director':
            directors.append(person['name'])
        elif typ == 'Writer':
            writers.append(person['name'])
        elif typ != 'Producer':
            _log.warning('unknown person type: %s', typ)

    cast.extend(guest_stars)
    # for ii, person in enumerate(cast):
    #     person['order'] = ii

    return cast, directors, writers


def _get_trailer(jf_item: dict) -> Optional[str]:
    trailers = jf_item.get('RemoteTrailers')
    if trailers:
        for trailer in trailers:
            url: Optional[str] = trailer.get('Url')
            if url:
                parsed = urlparse(url)
                if 'youtube' in parsed.netloc:
                    if parsed.query:
                        qs = parse_qs(parsed.query)
                        video_id = qs.get('v')
                        if video_id:
                            return f'plugin://plugin.video.youtube/play/?video_id={video_id[0]}'
    return None


def get_datetime(obj: dict, jf_key: str, to_format: str = '%Y-%m-%d %H:%M:%S',
                 from_format: str = '%Y-%m-%dT%H:%M:%S') -> Optional[str]:
    val: Optional[str] = obj.get(jf_key)
    if val:
        dt = datetime.datetime.strptime(val[:19], from_format)
        return dt.strftime(to_format)
    return None


def _get_studios(obj: dict) -> List[str]:
    ret = []
    studios = obj.get('Studios') or {}
    for studio in studios:
        name = studio.get('Name')
        if name:
            ret.append(name)
    return ret


def get_media_streams(jf_item: dict) -> Tuple[List, List]:
    video_streams = []
    audio_streams = []
    for source in jf_item.get('MediaSources') or []:
        run_time_ticks = source.get('RunTimeTicks')
        if run_time_ticks:
            duration_s = _ticks_to_seconds(run_time_ticks)
        else:
            duration_s = None
        for stream in source.get('MediaStreams') or []:
            obj = {}
            if duration_s:
                obj['duration'] = duration_s
            typ = stream.get('Type')
            if typ == 'Video':
                aspect_ratio = stream.get('AspectRatio')
                if aspect_ratio:
                    try:
                        if ':' in aspect_ratio:
                            left, right = [float(val) for val in aspect_ratio.split(':')]
                            obj['aspect'] = left / right
                        else:
                            obj['aspect'] = float(aspect_ratio)
                    except Exception:
                        _log.exception('failed to parse AspectRatio: "%s"', aspect_ratio)
                video_range_type = stream.get('VideoRangeType')
                if video_range_type:
                    obj['video_range_type'] = video_range_type
                for jf_key, kodi_key in (
                        ('Width', 'width'), ('Height', 'height'), ('Language', 'language'),
                        ('Codec', 'codec'), ('VideoRangeType', 'video_range_type')):
                    val = stream.get(jf_key)
                    if val:
                        obj[kodi_key] = val
                video_streams.append(obj)
            elif typ == 'Audio':
                for jf_key, kodi_key in (('Channels', 'channels'), ('Language', 'language'), ('Codec', 'codec')):
                    val = stream.get(jf_key)
                    if val:
                        obj[kodi_key] = val
                audio_streams.append(obj)

    return video_streams, audio_streams


def _get_unique_id_from_url(url: Optional[str]) -> Optional[str]:
    if url:
        parsed = urlparse(url)
        return parsed.path.split('/')[-1]
    return None


_provider_to_external = {
    'imdb': 'IMDb',
    'tmdb': 'TheMovieDb',
}

_provider_keys = _provider_to_external.keys()

_external_to_provider = {val: key for key, val in _provider_to_external.items()}


def _get_unique_ids(obj: dict) -> Dict[str, str]:
    external_keys = set(_provider_to_external.values())
    unique_ids = {}

    provider_ids = obj.get('ProviderIds') or {}
    for key, val in provider_ids.items():
        key = key.lower()
        external_key = _provider_to_external.get(key)
        if external_key is not None:
            unique_ids[key] = val
            external_keys.discard(external_key)

    for url in obj.get('ExternalUrls') or {}:
        name = url.get('Name')
        if name in external_keys:
            uid = _get_unique_id_from_url(url.get('Url'))
            if uid:
                unique_ids[_external_to_provider[name]] = uid
                external_keys.discard(name)

    return unique_ids


_user_cache: Optional[Dict[str, User]] = None


class Scraper(ABC):
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

    @abstractmethod
    def get_items(self, user: User) -> List[Dict[str, Any]]:
        raise NotImplementedError

    def _get_artwork_map(self) -> Dict[str, List[str]]:
        return _artwork

    def _get_items(self, user: User, item_type: str, media_type: str,
                   artwork_map: Optional[Dict[str, List[str]]] = None) -> List[Dict[str, Any]]:
        fields = ('AirTime,CustomRating,DateCreated,ExternalUrls,Genres,OriginalTitle'
                  ',Overview,Path,People,ProviderIds,Taglines,Tags'
                  ',RemoteTrailers,ForcedSortName,Studios,MediaSources')
        params = {'recursive': 'true', 'fields': fields, 'imageTypeLimit': 1, 'enableTotalRecordCount': 'true',
                  'IncludePeople': 'true', 'IncludeMedia': 'true', 'IncludeGenres': 'true',
                  'IncludeStudios': 'true', 'IncludeArtists': 'true',
                  'enableUserData': 'true', 'enableImages': 'true', 'IncludeItemTypes': item_type, 'sortBy': 'SortName'}
        jf_items = self._server.get_items(user, params=params).get('Items') or []
        if self._debug_level > 1:
            from pprint import pformat
            _log.debug(f'---------------- START JF {media_type.upper()} ----------------')
            _log.debug(pformat(jf_items))
            _log.debug(f'---------------- END JF {media_type.upper()} ----------------')

        try:
            items = []
            for jf_item in jf_items:
                info = self._get_info(jf_item, media_type, artwork_map)
                items.append({'name': _get_name(info['title'], info.get('year')), 'id': jf_item['Id'], 'info': info})

            if self._debug_level > 1:
                from pprint import pformat
                _log.debug(f'---------------- START {media_type.upper()} ----------------')
                _log.debug(pformat(items))
                _log.debug(f'---------------- END {media_type.upper()} ----------------')
            return items
        except Exception:
            from pprint import pformat
            _log.error(pformat(jf_items))
            raise

    def _get_info(self, jf_item: dict, media_type: str, artwork_map: Dict[str, List[str]]) -> dict:
        info = {'mediatype': media_type}

        cast, directors, writers = get_people(self._server, jf_item)

        if cast:
            info['cast'] = cast

        if directors:
            info['director'] = directors

        if writers:
            info['writer'] = writers

        runtime_ticks = jf_item.get('RunTimeTicks')
        duration_s = None
        if runtime_ticks is not None:
            duration_s = _ticks_to_seconds(runtime_ticks)
            info['duration'] = int(ceil(duration_s))

        keys = {'title': 'Name', 'originaltitle': 'OriginalTitle', 'plot': 'Overview',
                'plotoutline': 'Overview', 'year': 'ProductionYear',
                'mpaa': 'OfficialRating', 'rating': 'CommunityRating', 'path': 'Path',
                'dateadded': 'DateCreated', 'status': 'Status'}
        for kodi_key, jf_key in keys.items():
            val = jf_item.get(jf_key)
            if val is not None:
                info[kodi_key] = val

        datetime_keys = {'premiered': ('PremiereDate', '%Y-%m-%d'),
                         'dateadded': ('DateCreated', '%Y-%m-%d %H:%M:%S')}
        for kodi_key, jf_info in datetime_keys.items():
            val = get_datetime(jf_item, *jf_info)
            if val is not None:
                info[kodi_key] = val

        studios = []
        for studio in jf_item.get('Studios') or []:
            name = studio.get('Name')
            if name:
                studios.append(name)
        if studios:
            info['studio'] = studios

        genres = jf_item.get('Genres')
        if genres:
            info['genre'] = genres

        tags = jf_item.get('Tags')
        if tags:
            info['tag'] = tags

        sort_name = jf_item.get('ForcedSortName')
        if sort_name:
            info['sorttitle'] = sort_name

        taglines = jf_item.get('Taglines')
        if taglines:
            info['tagline'] = taglines[0]

        trailer = _get_trailer(jf_item)
        if trailer:
            info['trailer'] = trailer

        studios = _get_studios(jf_item)
        if studios:
            info['studio'] = studios

        user_data = jf_item.get('UserData')
        if user_data:
            play_count = user_data.get('PlayCount')
            if play_count is not None:
                info['playcount'] = play_count
            else:
                play_count = 0
            if play_count == 0 and user_data.get('Played', 0) > 0:
                info['playcount'] = 1
            last_played = get_datetime(user_data, 'LastPlayedDate')
            if last_played:
                info['lastplayed'] = last_played
            play_back_position_ticks = user_data.get('PlaybackPositionTicks')
            if play_back_position_ticks:
                play_back_position_s = _ticks_to_seconds(play_back_position_ticks)
                info['resume_point'] = [play_back_position_s, duration_s]

        artwork = get_artwork_from_item(self._server, jf_item, artwork_map)
        if artwork:
            info['artwork'] = artwork

        unique_ids = _get_unique_ids(jf_item)
        if unique_ids:
            info['unique_ids'] = unique_ids

        # 'country' 'ProductionLocations': ['United States of America'],
        # 'set'
        # 'setoverview'

        video, audio = get_media_streams(jf_item)
        if video:
            info['video'] = video
        if audio:
            info['audio'] = audio

        return info
