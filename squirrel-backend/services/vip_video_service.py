import logging
from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from models.vip_video_record import VipVideoRecord
from utils.url_helper import extract_top_level_domain

logger = logging.getLogger(__name__)


class VipVideoService:

    @staticmethod
    def is_vip_video(url: str, session: Session) -> bool:
        record = session.query(VipVideoRecord).filter(
            VipVideoRecord.url == url
        ).first()
        return record is not None

    @staticmethod
    def record_vip_video(
        url: str,
        error_message: Optional[str] = None,
        error_type: Optional[str] = None
    ) -> Optional[VipVideoRecord]:
        from core.database import get_session

        try:
            with get_session() as session:
                site = extract_top_level_domain(url)

                existing = session.query(VipVideoRecord).filter(
                    VipVideoRecord.url == url
                ).first()

                if existing:
                    existing.retry_count += 1
                    existing.error_message = error_message
                    existing.error_type = error_type
                    existing.updated_at = datetime.now()
                    session.commit()

                    logger.info(
                        f"Updated VIP video record: url={url}, "
                        f"retry_count={existing.retry_count}"
                    )
                    return existing

                record = VipVideoRecord(
                    url=url,
                    site=site,
                    error_message=error_message,
                    error_type=error_type,
                    retry_count=1
                )
                session.add(record)
                session.commit()

                logger.info(f"Created VIP video record: url={url}, site={site}")
                return record

        except IntegrityError:
            logger.warning(f"VIP video record already exists: url={url}")
            return None
        except Exception as e:
            logger.error(f"Failed to record VIP video: url={url}, error={e}")
            return None


vip_video_service = VipVideoService()
