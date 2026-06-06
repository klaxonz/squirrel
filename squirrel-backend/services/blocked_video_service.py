import logging
from collections.abc import Iterable
from datetime import datetime
from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models.blocked_video_record import BlockedVideoRecord
from utils.url_helper import extract_top_level_domain

logger = logging.getLogger(__name__)


def is_blocked_video(
    url: str,
    session: Session,
    *,
    reason_codes: Optional[Iterable[str]] = None,
) -> bool:
    query = session.query(BlockedVideoRecord).filter(
        BlockedVideoRecord.url == url,
    )
    if reason_codes:
        query = query.filter(BlockedVideoRecord.reason_code.in_(list(reason_codes)))
    return query.first() is not None


def record_blocked_video(
    *,
    url: str,
    reason_code: str,
    error_message: Optional[str] = None,
    error_type: Optional[str] = None,
) -> Optional[BlockedVideoRecord]:
    from core.database import get_session

    try:
        with get_session() as session:
            site = extract_top_level_domain(url)

            existing = session.query(BlockedVideoRecord).filter(
                BlockedVideoRecord.url == url,
            ).first()

            if existing:
                existing.reason_code = reason_code
                existing.retry_count += 1
                existing.error_message = error_message
                existing.error_type = error_type
                existing.updated_at = datetime.now()
                session.commit()

                logger.info(
                    'Updated blocked video record: url=%s, reason=%s, retry_count=%s',
                    url,
                    reason_code,
                    existing.retry_count,
                )
                return existing

            record = BlockedVideoRecord(
                url=url,
                site=site,
                reason_code=reason_code,
                error_message=error_message,
                error_type=error_type,
                retry_count=1,
            )
            session.add(record)
            session.commit()

            logger.info('Created blocked video record: url=%s, site=%s, reason=%s', url, site, reason_code)
            return record

    except IntegrityError:
        logger.warning('Blocked video record already exists: url=%s, reason=%s', url, reason_code)
        return None
    except (ConnectionError, OSError, ValueError, TypeError) as exc:
        logger.error('Failed to record blocked video: url=%s, reason=%s, error=%s', url, reason_code, exc)
        return None
