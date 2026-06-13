from __future__ import annotations

import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

RECENT_ERRORS_KEY = 'metrics:errors:recent'
RECENT_ERRORS_TTL_SECONDS = 86400


class RecentErrorStore:
    def __init__(self, redis_client) -> None:
        self.redis = redis_client

    def record(self, site: str, url: str, error_type: str, error_msg: str, max_records: int = 100) -> None:
        try:
            record = json.dumps(
                {
                    'time': datetime.now().isoformat(),
                    'site': site,
                    'url': url,
                    'type': error_type,
                    'msg': error_msg[:2000],
                }
            )
            self.redis.lpush(RECENT_ERRORS_KEY, record)
            self.redis.ltrim(RECENT_ERRORS_KEY, 0, max_records - 1)
            self.redis.expire(RECENT_ERRORS_KEY, RECENT_ERRORS_TTL_SECONDS)
        except Exception as exc:
            # infrastructure boundary -- metrics must never crash the caller
            logger.error('Failed to record error detail: %s', exc)

    def list_recent(self, limit: int = 50) -> list:
        try:
            records = self.redis.lrange(RECENT_ERRORS_KEY, 0, limit - 1)
            return [json.loads(record) for record in records]
        except Exception as exc:
            # infrastructure boundary -- metrics must never crash the caller
            logger.error('Failed to get recent errors: %s', exc)
            return []
