from typing import Optional

from sqlalchemy.orm import Session

from models.blocked_video_record import BlockedVideoRecord as VipVideoRecord
from services.blocked_video_service import is_blocked_video, record_blocked_video


def is_vip_video(url: str, session: Session) -> bool:
    return is_blocked_video(url, session, reason_codes=['vip_required'])


def record_vip_video(
    url: str,
    error_message: Optional[str] = None,
    error_type: Optional[str] = None,
) -> Optional[VipVideoRecord]:
    return record_blocked_video(
        url=url,
        reason_code='vip_required',
        error_message=error_message,
        error_type=error_type,
    )
