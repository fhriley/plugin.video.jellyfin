from typing import Optional, Union

import lib.generic.scraper.base as base
from lib.generic.api.jellyfin import User


class MoviesScraper(base.Scraper):
    def search_by_title(self, user: User, title: str, year: Optional[Union[str, int]] = None):
        return self._search_by_title(user, title, 'Movie', year)[-1]

    def get_by_id(self, user: User, movie_id: str):
        return self._get_by_id(user, movie_id, 'movie')[-1]
