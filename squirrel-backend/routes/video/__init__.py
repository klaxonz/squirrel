from fastapi import APIRouter

from routes.video import listing, random, save

router = APIRouter(prefix='/api/video', tags=['频道视频接口'])
router.include_router(save.router)
router.include_router(listing.router)
router.include_router(random.router)
