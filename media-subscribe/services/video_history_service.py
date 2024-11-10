from datetime import datetime
from typing import List, Optional

from sqlalchemy import desc
from sqlmodel import Session, select

from model.video_history import VideoHistory
from model.channel import ChannelVideo

class VideoHistoryService:
    def __init__(self, session: Session):
        self.session = session

    def update_watch_history(self, video_id: str, channel_id: str, watch_duration: int, last_position: int, total_duration: int) -> None:
        """更新视频观看历史"""
        # 使用 select 语句查找现有记录
        history_stmt = select(VideoHistory).where(VideoHistory.video_id == video_id, VideoHistory.channel_id == channel_id)
        history = self.session.exec(history_stmt).first()

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
            self.session.add(history)

        self.session.commit()

    def get_watch_history(self, page: int = 1, page_size: int = 20) -> tuple[List[dict], int]:
        """获取观看历史列表"""
        # 使用 select 语句查询总数
        count_stmt = select(VideoHistory)
        total = len(self.session.exec(count_stmt).all())

        # 使用 select 语句获取历史记录并关联视频信息
        stmt = (
            select(VideoHistory, ChannelVideo)
            .join(ChannelVideo, VideoHistory.video_id == ChannelVideo.video_id)
            .order_by(desc(VideoHistory.updated_at))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        
        results = self.session.exec(stmt).all()

        # 组合数据
        history_list = []
        for history, video in results:
            history_list.append({
                "id": video.id,
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
        if video_ids:
            # 使用 select 语句删除指定视频的历史记录
            stmt = select(VideoHistory).where(VideoHistory.video_id.in_(video_ids))
            histories = self.session.exec(stmt).all()
            for history in histories:
                self.session.delete(history)
        else:
            # 使用 select 语句删除所有历史记录
            stmt = select(VideoHistory)
            histories = self.session.exec(stmt).all()
            for history in histories:
                self.session.delete(history)
        
        self.session.commit()