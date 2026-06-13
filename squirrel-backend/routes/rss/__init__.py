from fastapi import APIRouter

from . import accounts, entries, feeds, sync

router = APIRouter(prefix='/api/rss', tags=['rss'])
router.include_router(accounts.router)
router.include_router(sync.router)
router.include_router(feeds.router)
router.include_router(entries.router)
