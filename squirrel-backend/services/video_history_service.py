from datetime import datetime
from typing import List, Optional

from sqlalchemy.exc import IntegrityError
from sqlmodel import select, col

from core.database import get_session
from models import Video
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
                        .with_for_update()  # 添加行级锁
                    )
                    history = session.exec(history_stmt).first()

                    if history:
                        # 更新现有记录
                        history.watch_duration = watch_duration
                        history.last_position = last_position
                        history.total_duration = total_duration
                        history.updated_at = datetime.now()
                    else:
                        # 创建新记录
                        history = VideoHistory(
                            video_id=video_id,
                            watch_duration=watch_duration,
                            last_position=last_position,
                            total_duration=total_duration
                        )
                        session.add(history)

                    session.commit()
                    break  # 成功后跳出重试循环

            except IntegrityError:
                # 如果发生并发冲突，回滚并重试
                session.rollback()
                retry_count += 1
                if retry_count >= max_retries:
                    raise Exception("更新观看历史失败：并发冲突无法解决")
                continue

            except Exception as e:
                # 其他异常直接抛出
                session.rollback()
                raise e

    def get_watch_history(self, page: int = 1, page_size: int = 20) -> tuple[List[dict], int]:
        """获取观看历史列表"""
        # 使用 select 语句查询总数
        with get_session() as session:
            total = len(session.exec(select(VideoHistory)).all())

            stmt = select(VideoHistory).order_by(col(VideoHistory.updated_at).desc()).offset(
                (page - 1) * page_size).limit(page_size)

            results = session.exec(stmt).all()

            video_ids = [result.video_id for result in results]
            videos = session.exec(select(Video).where(Video.video_id.in_(video_ids))).all()
            video_dict = {video.video_id: video for video in videos}

            # 组合数据
            history_list = []
            for history in results:
                if video_dict.get(history.video_id) is None:
                    continue
                video = video_dict[history.video_id]
                history_list.append({
                    "id": history.id,
                    "video_id": video.video_id,
                    "title": video.video_title,
                    "thumbnail": video.thumbnail,
                    "duration": video.duration,
                    "url": video.video_url,
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
                # 使用 select 语句删除指定视频的历史记录
                stmt = select(VideoHistory).where(VideoHistory.video_id.in_(video_ids))
                histories = session.exec(stmt).all()
                for history in histories:
                    session.delete(history)
            else:
                # 使用 select 语句删除所有历史记录
                stmt = select(VideoHistory)
                histories = session.exec(stmt).all()
                for history in histories:
                    session.delete(history)
            session.commit()
