from fastapi import APIRouter

from domains.playlist.interfaces.http import collection, detail, items, playback

router = APIRouter(prefix='/api/playlist', tags=['Playlist API'])
router.include_router(collection.router)
router.include_router(detail.router)
router.include_router(items.router)
router.include_router(playback.router)
