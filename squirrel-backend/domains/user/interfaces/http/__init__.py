from fastapi import APIRouter

from domains.user.interfaces.http import auth, config, profile

router = APIRouter(prefix='/api/users', tags=['Users API'])
router.include_router(auth.router)
router.include_router(profile.router)
router.include_router(config.router)
