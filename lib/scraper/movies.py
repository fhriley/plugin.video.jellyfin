from typing import List, Dict, Any

import lib.scraper.base as base
from lib.api.jellyfin import User


class MoviesScraper(base.Scraper):
    def get_items(self, user: User) -> List[Dict[str, Any]]:
        return self._get_items(user, 'Movie', 'movie')
