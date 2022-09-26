import random
from typing import List, Optional

from starlette.applications import Starlette
from starlette.routing import Route
from starlette.templating import Jinja2Templates

from plex import PlexClient, Video

templates = Jinja2Templates(directory="templates")


async def generate_videos(current_video: Optional[Video] = None) -> List[Video]:
    client = PlexClient()
    similar_videos = []
    if current_video:
        similar_videos = [video async for video in current_video.similar_videos()]
        random.shuffle(similar_videos)

    all_videos = [video async for video in client.get_videos()]
    random.shuffle(all_videos)

    return similar_videos[:5] + all_videos[:40]


async def video_index(request):
    videos = await generate_videos()
    return templates.TemplateResponse(
        "video_index.html",
        {"videos": videos, "request": request},
    )


async def view_video(request):
    client = PlexClient()
    current_video_id = request.path_params["video_id"]
    current_video = await client.get_video(current_video_id)
    videos = await generate_videos(current_video)
    return templates.TemplateResponse(
        "view_video.html",
        {"videos": videos, "current_video": current_video, "request": request},
    )


routes = [Route("/", video_index), Route("/video/{video_id:path}", view_video)]

app = Starlette(routes=routes)
