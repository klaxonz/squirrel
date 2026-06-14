import logging
from collections.abc import Callable, Generator, Iterable
from datetime import datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from domains.video.domain.models.blocked_video_record import BlockedVideoRecord
from infrastructure.database.session import get_session as _default_get_session
from infrastructure.site_catalog.url import extract_top_level_domain

SessionFactory = Callable[[], Generator[Session, None, None]]

logger = logging.getLogger(__name__)


class BlockedVideoService:
    def __init__(self, session_factory: SessionFactory | None = None):
        self._session_factory = session_factory or _default_get_session

    @staticmethod
    def is_blocked_video(
        url: str,
        session: Session,
        *,
        reason_codes: Iterable[str] | None = None,
    ) -> bool:
        query = session.query(BlockedVideoRecord).filter(
            BlockedVideoRecord.url == url,
        )
        if reason_codes:
            query = query.filter(BlockedVideoRecord.reason_code.in_(list(reason_codes)))
        return query.first() is not None

    def record_blocked_video(
        self,
        *,
        url: str,
        reason_code: str,
        error_message: str | None = None,
        error_type: str | None = None,
    ) -> BlockedVideoRecord | None:
        try:
            with self._session_factory() as session:
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
                        "Updated blocked video record: url=%s, reason=%s, retry_count=%s",
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

                logger.info("Created blocked video record: url=%s, site=%s, reason=%s", url, site, reason_code)
                return record

        except IntegrityError:
            logger.warning("Blocked video record already exists: url=%s, reason=%s", url, reason_code)
            return None
        except (ConnectionError, OSError, ValueError, TypeError) as exc:
            logger.error("Failed to record blocked video: url=%s, reason=%s, error=%s", url, reason_code, exc)
            return None


blocked_video_service = BlockedVideoService()
is_blocked_video = blocked_video_service.is_blocked_video
record_blocked_video = blocked_video_service.record_blocked_video
