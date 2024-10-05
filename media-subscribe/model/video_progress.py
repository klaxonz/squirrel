from sqlalchemy import Column, Integer, String, Float

from common.database import Base, BaseMixin


class VideoProgress(Base, BaseMixin):
    __tablename__ = 'video_progress'

    id = Column(Integer, primary_key=True, autoincrement=True)
    channel_id = Column(String(255), nullable=False)
    video_id = Column(String(255), nullable=False)
    progress = Column(Float, default=0)

    def __repr__(self):
        return f"<VideoProgress(id={self.id}, channel_id='{self.channel_id}', video_id='{self.video_id}', progress={self.progress})>"
