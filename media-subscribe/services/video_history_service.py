from datetime import datetime
from typing import List, Optional

from sqlmodel import select, col

from core.database import get_session
from model.video_history import VideoHistory
from model.channel import ChannelVideo


class VideoHistoryService:
    def __init__(self):
        pass

    def update_watch_history(self, video_id: str, channel_id: str, watch_duration: int, last_position: int,
                             total_duration: int) -> None:
        """更新视频观看历史"""
        # 使用 select 语句查找现有记录
        with get_session() as session:
            history_stmt = select(VideoHistory).where(VideoHistory.video_id == video_id,
                                                      VideoHistory.channel_id == channel_id)
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
                    channel_id=channel_id,
                    watch_duration=watch_duration,
                    last_position=last_position,
                    total_duration=total_duration
                )
                session.add(history)
            session.commit()

    def get_watch_history(self, page: int = 1, page_size: int = 20) -> tuple[List[dict], int]:
        """获取观看历史列表"""
        # 使用 select 语句查询总数
        with get_session() as session:
            count_stmt = select(VideoHistory)
            total = len(session.exec(count_stmt).all())

            stmt = select(VideoHistory).order_by(col(VideoHistory.updated_at).desc()).offset(
                (page - 1) * page_size).limit(page_size)

            results = session.exec(stmt).all()

            video_ids = [result.video_id for result in results]
            videos = session.exec(select(ChannelVideo).where(ChannelVideo.video_id.in_(video_ids))).all()
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
                    "channel_id": video.channel_id,
                    "channel_name": video.channel_name,
                    "channel_avatar": video.channel_avatar,
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
