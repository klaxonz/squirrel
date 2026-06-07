from services.video_crud_service import (
    create_video,
    get_video_by_id,
    get_video_by_url,
    get_videos_by_urls,
    save_remote_video,
)
from services.video_list_service import (
    get_video,
    list_videos,
)
from services.video_random_service import (
    get_random_video,
)

__all__ = [
    "create_video",
    "get_random_video",
    "get_video",
    "get_video_by_id",
    "get_video_by_url",
    "get_videos_by_urls",
    "list_videos",
    "save_remote_video",
]


class VideoService:
    @staticmethod
    def get_video(*args, **kwargs):
        return get_video(*args, **kwargs)

    @staticmethod
    def list_videos(*args, **kwargs):
        return list_videos(*args, **kwargs)

    @staticmethod
    def create_video(*args, **kwargs):
        return create_video(*args, **kwargs)

    @staticmethod
    def get_video_by_id(*args, **kwargs):
        return get_video_by_id(*args, **kwargs)

    @staticmethod
    def get_video_by_url(*args, **kwargs):
        return get_video_by_url(*args, **kwargs)

    @staticmethod
    def get_videos_by_urls(*args, **kwargs):
        return get_videos_by_urls(*args, **kwargs)

    @staticmethod
    def save_remote_video(*args, **kwargs):
        return save_remote_video(*args, **kwargs)

    @staticmethod
    def get_random_video(*args, **kwargs):
        return get_random_video(*args, **kwargs)
