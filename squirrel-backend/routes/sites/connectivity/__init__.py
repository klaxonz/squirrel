from fastapi import APIRouter

from routes.sites.connectivity import all_sites, batch, single

router = APIRouter()
router.include_router(single.router)
router.include_router(batch.router)
router.include_router(all_sites.router)
