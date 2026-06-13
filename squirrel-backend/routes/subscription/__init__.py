from fastapi import APIRouter

from . import basic, imports, refresh, sync_dashboard

router = APIRouter(prefix='/api/subscription', tags=['Subscription API'])
router.include_router(basic.router)
router.include_router(sync_dashboard.router)
router.include_router(refresh.router)
router.include_router(imports.router)
