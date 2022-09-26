import os
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Any, AsyncIterator, Callable, Optional
from urllib.parse import urlencode

import aiohttp


@dataclass
class Video:
    """Video object representing a video that can be played by the app"""

    vid: str
    name: str
    thumbnail_url: str
    stream_url: str
    similar_videos: Callable = lambda: []


class PlexClient:
    """Client for Plex 'API'. Provides a few limited methods that are useful for this application."""

    def __init__(self):
        self.base_url = os.environ.get("PLEX_HOST")
        self.token = os.environ.get("PLEX_TOKEN")
        self.playlist = os.environ.get("PLEX_PLAYLIST")

    def _build_url(self, path, *, params: Optional[dict[str, Any]] = None):
        """Build a valid Plex URL by adding the API token and base URL"""
        if not params:
            params = {}
        params["X-Plex-Token"] = self.token
        qs = urlencode(params)
        return f"{self.base_url}{path}?{qs}"

    async def _do_request(self, url):
        """Perform an API request"""
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                return await response.text()

    def _build_stream_url(self, vid: str):
        """Given a Plex video key, build a URL that can be used to transcode/stream the video"""
        params = {
            "path": vid,
            "offset": 0,
            "copyts": 1,
            "protocol": "hls",
            "mediaIndex": 0,
            "directPlay": 0,
            "directStream": 1,
            "X-Plex-Platform": "Chrome",
            "X-Plex-Token": self.token,
        }
        return self._build_url("/video/:/transcode/universal/start.m3u8", params=params)

    def _build_thumbnail_url(self, url: str):
        """Given a partial URL to a Plex video thumbnail, generate a URL to a resized version"""
        params = {
            "url": url,
            "width": 512,
            "height": 288,
            "minSize": 0,
            "upscale": 1,
            "X-Plex-Platform": "Chrome",
        }
        return self._build_url("/photo/:/transcode", params=params)

    def _video_object_from_xml(self, item: ET.Element) -> Video:
        return Video(
            vid=item.get("key", ""),
            name=item.get("title", ""),
            thumbnail_url=self._build_thumbnail_url(item.get("thumb", "")),
            stream_url=self._build_stream_url(item.get("key", "")),
            similar_videos=lambda: self.get_videos_in_series(
                item.get("grandparentKey", "")
            ),
        )

    async def get_videos(self) -> AsyncIterator[Video]:
        """Get all videos from the given playlist"""
        res = await self._do_request(
            self._build_url(f"/playlists/{self.playlist}/items")
        )
        root = ET.fromstring(res)
        for item in root.findall("Video"):
            yield self._video_object_from_xml(item)

    async def get_videos_in_series(self, series_key: str) -> AsyncIterator[Video]:
        res = await self._do_request(self._build_url(series_key + "/allLeaves"))
        root = ET.fromstring(res)
        for item in root.findall("Video"):
            yield self._video_object_from_xml(item)

    async def get_video(self, id: str) -> Optional[Video]:
        res = await self._do_request(self._build_url(id))
        root = ET.fromstring(res)
        item = root.find("Video")
        if item:
            return self._video_object_from_xml(item)
        else:
            return None
