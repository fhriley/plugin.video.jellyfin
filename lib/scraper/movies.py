from typing import List, Dict, Any

import lib.scraper.base as base


class MoviesScraper(base.Scraper):
    @property
    def jf_item_type(self):
        return 'Movie'

    @property
    def kodi_media_type(self):
        return 'movies'

    def scrape_movie(self, jf_movie: Dict[str, Any]) -> Dict[str, Any]:
        return self._scrape_item(jf_movie, 'movie')

    def scrape_movies(self, jf_movies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [self.scrape_movie(jf_movie) for jf_movie in jf_movies]
