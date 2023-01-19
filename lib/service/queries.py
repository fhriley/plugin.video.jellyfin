from typing import Dict, Any

from lib.api.jellyfin import Server, User


def get_item(server: Server, user: User, item_id: str) -> Dict[str, Any]:
    params = {'enableTotalRecordCount': 'true',
              'IncludePeople': 'false', 'IncludeMedia': 'false', 'IncludeGenres': 'false',
              'IncludeStudios': 'false', 'IncludeArtists': 'false',
              'enableUserData': 'false', 'enableImages': 'false', 'ids': item_id}
    jf_items = server.get_items(user, params=params).get('Items')
    if not jf_items:
        raise Exception(f'item with id {item_id} not found')
    return jf_items[0]
