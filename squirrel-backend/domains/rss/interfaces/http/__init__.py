from fastapi import APIRouter

from domains.rss.interfaces.http import accounts, entries, feeds, sync

router = APIRouter(prefix='/api/rss', tags=['RSS API'])
router.include_router(accounts.router)
router.include_router(sync.router)
router.include_router(feeds.router)
router.include_router(entries.router)
