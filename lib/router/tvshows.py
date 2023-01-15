import xbmcgui
import xbmcplugin

from lib.api.jellyfin import User
from lib.builder.tvshows import TvShowsBuilder
from lib.router.base import Router
from lib.scraper.queries import get_item, get_episodes_min, get_seasons
from lib.scraper.tvshows import TvShowsScraper
from lib.util import util


class TvShowsRouter(Router):
    def getdetails(self, user: User, scraper: TvShowsScraper, builder: TvShowsBuilder, params: dict):
        try:
            in_params = util.get_args_from_params(self._log, 'getdetails', params, ('id',))
            self._log.debug('getdetails: in_params=%s', in_params)
            jf_show = get_item(self._server, user, in_params['id'])
            jf_seasons = get_seasons(self._server, user, in_params['id']).get('Items') or []
            show = scraper.scrape_show(jf_show, jf_seasons)
            builder.build_show(show)
        except Exception:
            xbmcplugin.setResolvedUrl(handle=self._handle, succeeded=False, listitem=xbmcgui.ListItem(offscreen=True))
            raise

    def getepisodelist(self, user: User, scraper: TvShowsScraper, builder: TvShowsBuilder, params: dict):
        try:
            in_params = util.get_args_from_params(self._log, 'getepisodelist', params, ('id',))
            self._log.debug('getepisodelist: in_params=%s', in_params)
            jf_episodes = get_episodes_min(self._server, user, in_params['id']).get('Items') or []
            episodes = scraper.scrape_episodes(jf_episodes)
            builder.build_episodes_directory(episodes)
        except Exception:
            xbmcplugin.endOfDirectory(handle=self._handle, succeeded=False)
            raise

    def getepisodedetails(self, user: User, scraper: TvShowsScraper, builder: TvShowsBuilder, params: dict):
        try:
            in_params = util.get_args_from_params(self._log, 'getepisodedetails', params, ('id',))
            self._log.debug('getepisodedetails: in_params=%s', in_params)
            jf_episode = get_item(self._server, user, in_params['id'])
            episode = scraper.scrape_episode(jf_episode)
            builder.build_episode(episode)
        except Exception:
            xbmcplugin.setResolvedUrl(handle=self._handle, succeeded=False, listitem=xbmcgui.ListItem(offscreen=True))
            raise
