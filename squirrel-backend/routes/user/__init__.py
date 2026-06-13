from fastapi import APIRouter

from . import auth, config, profile

router = APIRouter(prefix='/api/users', tags=['users'])
router.include_router(auth.router)
router.include_router(profile.router)
router.include_router(config.router)
