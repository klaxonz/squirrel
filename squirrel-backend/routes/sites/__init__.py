from fastapi import APIRouter

from . import catalog, connectivity, login, youtube_oauth

router = APIRouter(prefix='/api/sites', tags=['sites'])
router.add_api_route('', catalog.get_supported_sites, methods=['GET'])
router.include_router(catalog.router)
router.include_router(connectivity.router)
router.include_router(login.router)
router.include_router(youtube_oauth.router)
