from fastapi import APIRouter
from pydantic import BaseModel

from core.config import settings

router = APIRouter(
    tags=['设置接口']
)


class ConsumerSettings(BaseModel):
    downloadConsumers: int
    extractConsumers: int
    subscribeConsumers: int


@router.get("/api/settings")
def get_settings():
    return {
        "code": 0,
        "data": {
            "downloadConsumers": settings.DOWNLOAD_CONSUMERS,
            "extractConsumers": settings.EXTRACT_CONSUMERS,
            "subscribeConsumers": settings.SUBSCRIBE_CONSUMERS
        }
    }


@router.post("/api/settings")
def update_settings(settings: ConsumerSettings):
    settings.DOWNLOAD_CONSUMERS = settings.downloadConsumers
    settings.EXTRACT_CONSUMERS = settings.extractConsumers
    settings.SUBSCRIBE_CONSUMERS = settings.subscribeConsumers
    from main import restart_consumers
    restart_consumers()
    return {"code": 0, "msg": "Settings updated successfully"}
