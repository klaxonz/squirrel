from fastapi import APIRouter

from . import artists, auth, catalog, comments, library, playback, recommendations, search, videos

router = APIRouter(prefix='/api/music', tags=['音乐接口'])
router.include_router(search.router)
router.include_router(recommendations.router)
router.include_router(catalog.router)
router.include_router(library.router)
router.include_router(auth.router)
router.include_router(playback.router)
router.include_router(comments.router)
router.include_router(artists.router)
router.include_router(videos.router)
