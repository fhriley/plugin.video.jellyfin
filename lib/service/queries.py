from typing import Dict, Any

from lib.api.jellyfin import Server, User
from lib.util.exceptions import NotFound


def get_item(server: Server, user: User, item_id: str) -> Dict[str, Any]:
    params = {'enableTotalRecordCount': 'true',
              'IncludePeople': 'false', 'IncludeMedia': 'false', 'IncludeGenres': 'false',
              'IncludeStudios': 'false', 'IncludeArtists': 'false',
              'enableUserData': 'false', 'enableImages': 'false', 'ids': item_id}
    jf_items = server.get_items(user, params=params).get('Items')
    if not jf_items:
        raise NotFound('%s not found', item_id)
    return jf_items[0]
