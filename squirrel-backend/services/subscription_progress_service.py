from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Any

from core.cache import RedisClient
from common import constants


client = RedisClient.get_instance().get_client()


def progress_key(sub_id: int) -> str:
    return f"{constants.REDIS_KEY_SUBSCRIPTION_UPDATE_PROGRESS_PREFIX}{sub_id}"


def set_progress(sub_id: int, data: Dict[str, Any]) -> None:
    base = {"subscriptionId": sub_id, "updatedAt": datetime.now(timezone.utc).isoformat()}
    client.hset(progress_key(sub_id), mapping={**base, **data})
    client.expire(progress_key(sub_id), 24 * 3600)


def tick_progress(sub_id: int) -> None:
    key = progress_key(sub_id)
    try:
        client.hincrby(key, "processed", 1)
        client.hset(key, mapping={"updatedAt": datetime.now(timezone.utc).isoformat()})
    except Exception:
        pass


def maybe_complete(sub_id: int) -> None:
    try:
        key = progress_key(sub_id)
        data = client.hgetall(key) or {}
        total = int(data.get("total", 0) or 0)
        processed = int(data.get("processed", 0) or 0)
        phase = data.get("phase", "")
        status = data.get("status", "")
        if 0 < total <= processed and phase == "extracting" and status == "in_progress":
            now_iso = datetime.now(timezone.utc).isoformat()
            set_progress(sub_id, {
                "status": "completed",
                "phase": "finalizing",
                "finishedAt": now_iso,
            })
    except Exception:
        pass


