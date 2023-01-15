from typing import Dict, List, Any

import lib.scraper.base as base


class TvShowsScraper(base.Scraper):
    @property
    def jf_item_type(self):
        return 'Series'

    @property
    def kodi_media_type(self):
        return 'tvshows'

    def scrape_show(self, jf_show: Dict[str, Any], jf_seasons: List[Dict[str, Any]]) -> Dict[str, Any]:
        if self._debug_level > 1:
            base.print_debug_info(self._log, 'JF SCRAPE SHOW', jf_show)

        try:
            show = self._scrape_item(jf_show, 'tvshow')
            info = show['info']
            info['tvshowtitle'] = info['title']

            premiered = info.get('premiered')
            if premiered:
                info['aired'] = premiered

            seasons = self.scrape_seasons(jf_seasons)
            if seasons:
                info['seasons'] = seasons

            if self._debug_level > 1:
                base.print_debug_info(self._log, 'SCRAPE SHOW', show)

            return show
        except Exception:
            base.exception(self._log, jf_show)
            raise

    def scrape_shows(self, jf_shows: List[Dict[str, Any]], jf_seasons: Dict[str, List[Dict[str, Any]]]) -> List[
        Dict[str, Any]]:
        return [self.scrape_show(jf_show, jf_seasons.get(jf_show['Id'])) for jf_show in jf_shows or []]

    def scrape_season(self, jf_season: Dict[str, Any]) -> Dict[str, Any]:
        if self._debug_level > 1:
            base.print_debug_info(self._log, 'JF SCRAPE SEASON', jf_season)

        try:
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

            if self._debug_level > 1:
                base.print_debug_info(self._log, 'SCRAPE SEASON', season)

            return season
        except Exception:
            base.exception(self._log, jf_season)
            raise

    def scrape_seasons(self, jf_seasons: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [self.scrape_season(jf_season) for jf_season in jf_seasons or []]

    def scrape_episode(self, jf_episode: Dict[str, Any]) -> Dict[str, Any]:
        if self._debug_level > 1:
            base.print_debug_info(self._log, 'SCRAPE JF EPISODE', jf_episode)

        try:
            episode = self._scrape_item(jf_episode, 'episode', base.episode_artwork)
            info = episode['info']

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

            episode['name'] = info['title']
            episode['season_id'] = jf_episode['SeasonId']
            series_id = jf_episode.get('SeriesId')
            if series_id:
                episode['series_id'] = series_id

            if self._debug_level > 1:
                base.print_debug_info(self._log, 'SCRAPE EPISODE', episode)

            return episode
        except Exception:
            base.exception(self._log, jf_episode)
            raise

    def scrape_episodes(self, jf_episodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [self.scrape_episode(jf_episode) for jf_episode in jf_episodes or []]
