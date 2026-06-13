from fastapi import APIRouter

from infrastructure.scheduling.routes import control, status, tasks

router = APIRouter(prefix='/api/scheduler', tags=['Scheduled Task Management'])
router.include_router(status.router)
router.include_router(tasks.router)
router.include_router(control.router)
