from fastapi import APIRouter

from domains.subscription.interfaces.http import basic, dependencies, imports, refresh, sync_dashboard

router = APIRouter(prefix='/api/subscriptions', tags=['Subscriptions'])
router.include_router(basic.router)
router.include_router(imports.router)
router.include_router(refresh.router)
router.include_router(sync_dashboard.router)
