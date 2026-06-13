from fastapi import APIRouter

from routes.connectivity import batch, quick, single

router = APIRouter(prefix='/api/connectivity', tags=['Connectivity'])
router.include_router(single.router)
router.include_router(batch.router)
router.include_router(quick.router)
