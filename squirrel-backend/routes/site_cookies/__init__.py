from fastapi import APIRouter

from routes.site_cookies import bulk_import, cookiecloud, single_upload

router = APIRouter(prefix='/api/site-cookies', tags=['site-cookies'])
router.include_router(single_upload.router)
router.include_router(bulk_import.router)
router.include_router(cookiecloud.router)
