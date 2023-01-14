import logging
from math import ceil
from typing import Callable, Optional, List, Dict, Any
from urllib.parse import urlencode, quote

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin

import lib.addon.util as util
import lib.generic.scraper.base as base
from lib.addon.settings import Settings
from lib.generic.api.jellyfin import User

_log = logging.getLogger(__name__)


def set_tag_if_have(info: dict, key: str, set_func: Callable):
    val = info.get(key)
    if val is not None:
        set_func(val)


def set_common_tags(tags: xbmc.InfoTagVideo, info: dict, unique_id: Optional[str] = None):
    # TODO
    # setUserRating
    # addVideoStream
    # addAudioStream
    # addSubtitleStream

    unique_ids = info.get('unique_ids') or {}
    if unique_id:
        unique_ids['jellyfin'] = unique_id
    if unique_ids:
        tags.setUniqueIDs(unique_ids, defaultuniqueid='jellyfin')

    set_tag_if_have(info, 'year', tags.setYear)
    set_tag_if_have(info, 'rating', tags.setRating)
    set_tag_if_have(info, 'playcount', tags.setPlaycount)
    set_tag_if_have(info, 'mpaa', tags.setMpaa)
    set_tag_if_have(info, 'plot', tags.setPlot)
    set_tag_if_have(info, 'plotoutline', tags.setPlotOutline)
    set_tag_if_have(info, 'title', tags.setTitle)
    set_tag_if_have(info, 'originaltitle', tags.setOriginalTitle)
    set_tag_if_have(info, 'sorttitle', tags.setSortTitle)
    set_tag_if_have(info, 'tagline', tags.setTagLine)
    set_tag_if_have(info, 'genre', tags.setGenres)
    set_tag_if_have(info, 'country', tags.setCountries)
    set_tag_if_have(info, 'director', tags.setDirectors)
    set_tag_if_have(info, 'studio', tags.setStudios)
    set_tag_if_have(info, 'writer', tags.setWriters)
    set_tag_if_have(info, 'duration', tags.setDuration)
    set_tag_if_have(info, 'premiered', tags.setPremiered)
    set_tag_if_have(info, 'tag', tags.setTags)
    # _set_tag_if_have(info, '', tags.setProductionCode)
    set_tag_if_have(info, 'lastplayed', tags.setLastPlayed)
    # _set_tag_if_have(info, '', tags.setVotes)
    set_tag_if_have(info, 'trailer', tags.setTrailer)
    # set_tag_if_have(info, 'path', tags.setPath)
    set_tag_if_have(info, 'dateadded', tags.setDateAdded)
    set_tag_if_have(info, 'mediatype', tags.setMediaType)
    resume_point = info.get('resume_point')
    if resume_point:
        tags.setResumePoint(resume_point[0], resume_point[1] or 0.0)
    actors = [xbmc.Actor(actor.get('name') or '', actor.get('role') or '', actor.get('order') or -1,
                         actor.get('thumb') or '')
              for actor in (info.get('cast') or [])]
    if actors:
        tags.setCast(actors)

    for image_type, image_url in (info.get('artwork') or {}).items():
        tags.addAvailableArtwork(image_url, image_type)

    for video in info.get('video') or []:
        duration = int(ceil(video.get('duration', 0.0)))
        hdr_type = video.get('video_range_type') or ''
        if hdr_type == 'SDR':
            hdr_type = ''
        # TODO: hdrType=hdr_type
        tags.addVideoStream(
            xbmc.VideoStreamDetail(video.get('width', 0), video.get('height', 0), video.get('aspect', 0.0),
                                   duration, video.get('codec') or '', language=video.get('language') or ''))

    for audio in info.get('audio') or []:
        tags.addAudioStream(
            xbmc.AudioStreamDetail(audio.get('channels', -1), audio.get('codec') or '', audio.get('language') or ''))

def get_url(addon, *args, **kwargs):
    path = '/'.join([quote(arg) for arg in args])
    if kwargs:
        param_str = f'?{urlencode(kwargs)}'
    else:
        param_str = ''
    return f'plugin://{addon.getAddonInfo("id")}/library/tvshows/{path}{param_str}'

class Handlers:
    def __init__(self, scraper: base.Scraper, settings: Settings, handle: int, addon: xbmcaddon.Addon):
        self.__scraper = scraper
        self._settings = settings
        self._handle = handle
        self._addon = addon

    def _create_items_directory_set_list_item(self, list_item: xbmcgui.ListItem, item_id: str, jf_item: dict):
        pass

    def _create_items_directory_set_tags(self, tags: xbmc.InfoTagVideo, item_id: str, info: dict):
        pass

    def create_items_directory(self, user: User):
        raise NotImplementedError

    def _create_items_directory(self, jf_items: List[Dict[str, Any]], media_type: str):
        succeeded = False
        try:
            _log.debug('_create_items_directory')
            items = []
            is_folder = True

            for jf_item in jf_items:
                item_id = jf_item['id']
                info = jf_item['info']

                list_item = xbmcgui.ListItem(jf_item['name'], offscreen=True)

                self._create_items_directory_set_list_item(list_item, item_id, jf_item)

                tags = list_item.getVideoInfoTag()
                unique_id = util.get_plugin_url(self._addon, id=item_id)
                set_common_tags(tags, info, unique_id)
                self._create_items_directory_set_tags(tags, item_id, info)

                url = get_url(self._addon, item_id)
                items.append((url, list_item, is_folder))

            xbmcplugin.setContent(handle=self._handle, content=media_type)
            xbmcplugin.addDirectoryItems(handle=self._handle, items=items)
            succeeded = True
        finally:
            xbmcplugin.endOfDirectory(handle=self._handle, succeeded=succeeded)
