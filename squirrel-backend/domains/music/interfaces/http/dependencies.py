from collections.abc import AsyncGenerator

from domains.music.application.services.service import MusicService


async def get_music_service() -> AsyncGenerator[MusicService, None]:
    service = MusicService()
    try:
        yield service
    finally:
        await service.aclose()
