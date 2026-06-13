from fastapi import APIRouter

from domains.video.interfaces.http import listing, random, save

router = APIRouter(prefix='/api/video', tags=['Video API'])
router.include_router(save.router)
router.include_router(listing.router)
router.include_router(random.router)
