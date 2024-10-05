from fastapi import APIRouter
from pydantic import BaseModel

from common.config import GlobalConfig

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
            "downloadConsumers": GlobalConfig.DOWNLOAD_CONSUMERS,
            "extractConsumers": GlobalConfig.EXTRACT_CONSUMERS,
            "subscribeConsumers": GlobalConfig.SUBSCRIBE_CONSUMERS
        }
    }


@router.post("/api/settings")
def update_settings(settings: ConsumerSettings):
    GlobalConfig.DOWNLOAD_CONSUMERS = settings.downloadConsumers
    GlobalConfig.EXTRACT_CONSUMERS = settings.extractConsumers
    GlobalConfig.SUBSCRIBE_CONSUMERS = settings.subscribeConsumers
    from main import restart_consumers
    restart_consumers()
    return {"code": 0, "msg": "Settings updated successfully"}
