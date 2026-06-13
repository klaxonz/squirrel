from collections.abc import AsyncGenerator

from services.music.service import MusicService


async def get_music_service() -> AsyncGenerator[MusicService, None]:
    service = MusicService()
    try:
        yield service
    finally:
        await service.aclose()
