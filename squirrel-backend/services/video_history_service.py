from datetime import datetime
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from core.database import get_session
from models.video import Video
from models.video_history import VideoHistory


class VideoHistoryService:
    def __init__(self):
        pass

    def update_watch_history(self, video_id: int, watch_duration: int, last_position: int,
                             total_duration: int) -> None:
        """更新视频观看历史"""
        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            try:
                with get_session() as session:
                    history_stmt = (
                        select(VideoHistory)
                        .where(
                            VideoHistory.video_id == video_id,
                        )
                        .with_for_update()
                    )
                    history = session.scalars(history_stmt).first()

                    if history:
                        history.watch_duration = watch_duration
                        history.last_position = last_position
                        history.total_duration = total_duration
                        history.updated_at = datetime.now()
                    else:
                        history = VideoHistory(
                            video_id=video_id,
                            watch_duration=watch_duration,
                            last_position=last_position,
                            total_duration=total_duration
                        )
                        session.add(history)
                    session.commit()
                    break

            except IntegrityError:
                session.rollback()
                retry_count += 1
                if retry_count >= max_retries:
                    raise Exception("更新观看历史失败：并发冲突无法解决")
                continue

            except Exception as e:
                session.rollback()
                raise e

    def get_watch_history(self, page: int = 1, page_size: int = 20) -> tuple[List[dict], int]:
        # 使用 select 语句查询总数
        with get_session() as session:
            total = len(session.scalars(select(VideoHistory)).all())

            stmt = select(VideoHistory).order_by(VideoHistory.updated_at.desc()).offset(
                (page - 1) * page_size).limit(page_size)

            results = session.scalars(stmt).all()

            video_ids = [result.id for result in results]
            videos = session.exec(select(Video).where(Video.id.in_(video_ids))).all()
            video_dict = {video.id: video for video in videos}

            history_list = []
            for history in results:
                if video_dict.get(history.id) is None:
                    continue
                video = video_dict[history.id]
                history_list.append({
                    "id": history.id,
                    "video_id": video.id,
                    "title": video.title,
                    "thumbnail": video.thumbnail,
                    "duration": video.duration,
                    "url": video.url,
                    "uploaded_at": video.uploaded_at,
                    "watch_duration": history.watch_duration,
                    "last_position": history.last_position,
                    "total_duration": history.total_duration,
                    "updated_at": history.updated_at
                })

            return history_list, total

    def clear_history(self, video_ids: Optional[List[str]] = None) -> None:
        """清空观看历史"""
        with get_session() as session:
            if video_ids:
                stmt = select(VideoHistory).where(VideoHistory.video_id.in_(video_ids))
                histories = session.scalars(stmt).all()
                for history in histories:
                    session.delete(history)
            else:
                stmt = select(VideoHistory)
                histories = session.scalars(stmt).all()
                for history in histories:
                    session.delete(history)
            session.commit()


video_history_service = VideoHistoryService()
