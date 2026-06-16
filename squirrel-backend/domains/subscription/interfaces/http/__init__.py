from fastapi import APIRouter

from domains.subscription.interfaces.http import basic, imports, refresh

router = APIRouter(prefix='/api/subscription', tags=['Subscriptions'])
router.include_router(basic.router)
router.include_router(imports.router)
router.include_router(refresh.router)
