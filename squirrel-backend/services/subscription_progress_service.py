from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Any

from core.cache import RedisClient
from common import constants


client = RedisClient.get_instance().get_client()


def progress_key(sub_id: int) -> str:
    return f"{constants.REDIS_KEY_SUBSCRIPTION_UPDATE_PROGRESS_PREFIX}{sub_id}"





