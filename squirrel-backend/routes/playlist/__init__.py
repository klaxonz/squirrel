from fastapi import APIRouter

from routes.playlist import collection, detail, items, playback

router = APIRouter(prefix='/api/playlist', tags=['播放列表接口'])
router.include_router(collection.router)
router.include_router(detail.router)
router.include_router(items.router)
router.include_router(playback.router)
