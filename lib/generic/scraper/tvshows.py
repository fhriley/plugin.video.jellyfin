import logging
from typing import Optional, Dict, List, Any

import lib.generic.scraper.base as base
from lib.generic.api.jellyfin import User

_log = logging.getLogger(__name__)

_episode_artwork = {
    'Art': ['clearart', 'tvshow.clearart'],
    'Logo': ['clearlogo', 'tvshow.clearlogo'],
    'Disc': ['discart'],
    'Backdrop': ['fanart', 'fanart_image'],
    'Thumb': ['landscape', 'tvshow.landscape'],
    'Primary': ['thumb']
}


class TvShowsScraper(base.Scraper):
    def get_items(self, user: User) -> List[Dict[str, Any]]:
        jf_items = self._get_items(user, 'Series', 'tvshow')

        try:
            items = []
            for jf_item in jf_items:
                info = jf_item['info']
                info['tvshowtitle'] = info['title']

                premiered = info.get('premiered')
                if premiered:
                    info['aired'] = premiered

                jf_seasons = self._server.get_seasons(user, jf_item['id'])

                if self._debug_level > 1:
                    from pprint import pformat
                    _log.debug('---------------- START JF SEASONS ----------------')
                    _log.debug(pformat(jf_seasons))
                    _log.debug('---------------- END JF SEASONS ----------------')

                seasons = []
                for jf_season in jf_seasons:
                    season = {'id': jf_season['Id'], 'name': jf_season['Name'], 'number': jf_season['IndexNumber'],
                              'series_id': jf_season['SeriesId']}
                    year = jf_season.get('ProductionYear')
                    if year:
                        season['year'] = year
                    val = base.get_datetime(jf_season, 'PremiereDate', '%Y-%m-%d')
                    if val is not None:
                        season['premiered'] = val
                    image_tags = jf_season.get('ImageTags') or {}
                    primary_tag = image_tags.get('Primary')
                    if primary_tag:
                        url = self._server.image_url(jf_season['Id'], 'Primary', params={'tag': primary_tag})
                        season['artwork'] = {'type': 'poster', 'url': url}
                    seasons.append(season)
                if seasons:
                    info['seasons'] = seasons

                items.append(jf_item)

            return items
        except Exception:
            from pprint import pformat
            _log.error(pformat(jf_items))
            raise

    def get_episodes(self, user: User, series_id: str, season_id: Optional[str] = None) -> List[Dict[str, Any]]:
        # https://jellyfin.riley-home.net/Shows/7879d2c8a44a666d6846d4eea026ddd3/Episodes?seasonId=7e77c3bc32fda3944166b301e1f4ab04&userId=d4d75bfbe12f420f9ad25dc7cd1de12a&Fields=ItemCounts%2CPrimaryImageAspectRatio%2CBasicSyncInfo%2CCanDelete%2CMediaSourceCount%2COverview
        fields = ('AirTime,CustomRating,DateCreated,ExternalUrls,Genres,OriginalTitle'
                  ',Overview,Path,People,ProviderIds,Taglines,Tags'
                  ',RemoteTrailers,ForcedSortName,Studios,MediaSources')
        params = {'fields': fields, 'imageTypeLimit': 1, 'enableTotalRecordCount': 'true',
                  'IncludePeople': 'true', 'IncludeMedia': 'true', 'IncludeGenres': 'true',
                  'IncludeStudios': 'true', 'IncludeArtists': 'true',
                  'enableUserData': 'true', 'enableImages': 'true', 'sortBy': 'PremiereDate', 'userId': user.uuid}
        if season_id:
            params['seasonId'] = season_id
        jf_episodes = self._server.get_episodes(user, series_id, params=params)
        if self._debug_level > 1:
            from pprint import pformat
            _log.debug('---------------- START JF EPISODES ----------------')
            _log.debug(pformat(jf_episodes))
            _log.debug('---------------- END JF EPISODES ----------------')

        try:
            episodes = []

            for jf_episode in jf_episodes:
                info = self._get_info(jf_episode, 'episode', _episode_artwork)

                info['season'] = jf_episode['ParentIndexNumber']
                info['episode'] = jf_episode['IndexNumber']

                airs_after_season = jf_episode.get("AirsAfterSeasonNumber")
                if airs_after_season:
                    info['sortseason'] = airs_after_season + 1
                    info['sortepisode'] = 0
                airs_before_season = jf_episode.get("AirsBeforeSeasonNumber")
                if airs_before_season:
                    info['sortseason'] = airs_before_season
                    info['sortepisode'] = 0
                airs_before_episode = jf_episode.get("AirsBeforeEpisodeNumber")
                if airs_before_episode:
                    info['sortepisode'] = airs_before_episode

                premiered = info.get('premiered')
                if premiered:
                    info['aired'] = premiered

                artwork = info.get('artwork') or {}
                thumb = artwork.get('thumb')
                if not thumb:
                    keys = [('ParentThumbImageTag', 'ParentThumbItemId', 'Thumb'),
                            ('SeriesPrimaryImageTag', 'SeriesId', 'Primary')]
                    for tag_key, id_key, typ in keys:
                        item_id = jf_episode.get(id_key)
                        tag = jf_episode.get(tag_key)
                        if item_id and tag:
                            artwork['thumb'] = self._server.image_url(item_id, typ, params={'tag': tag})
                            info['artwork'] = artwork
                            break

                episode = {'name': info['title'], 'series_id': series_id, 'season_id': jf_episode['SeasonId'],
                           'id': jf_episode['Id'], 'info': info}
                episodes.append(episode)

            if self._debug_level > 1:
                from pprint import pformat
                _log.debug('---------------- START EPISODES ----------------')
                _log.debug(pformat(episodes))
                _log.debug('---------------- END EPISODES ----------------')

            return episodes
        except Exception:
            from pprint import pformat
            _log.error(pformat(jf_episodes))
            raise

    def _get_artwork_map(self) -> Dict[str, List[str]]:
        return _episode_artwork
