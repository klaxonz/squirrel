from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
from sqlalchemy import Column, BigInteger, Text, Integer
from sqlalchemy.dialects.mysql import VARCHAR
from common.database import Base, BaseMixin


class DownloadTask(Base, BaseMixin):
    __tablename__ = 'download_task'

    task_id = Column(Integer, primary_key=True)
    url = Column(VARCHAR(2048), nullable=False)
    thumbnail = Column(VARCHAR(2048), nullable=True)
    domain = Column(VARCHAR(255), nullable=False)
    video_id = Column(VARCHAR(64), nullable=False)
    channel_id = Column(VARCHAR(255), nullable=True)
    channel_name = Column(VARCHAR(255), nullable=True)
    channel_url = Column(VARCHAR(2048), nullable=True)
    channel_avatar = Column(VARCHAR(2048), nullable=True)
    title = Column(VARCHAR(255), nullable=True)
    status = Column(VARCHAR(32), nullable=False, default='PENDING')
    downloaded_size = Column(BigInteger, nullable=True, default=0)
    total_size = Column(BigInteger, nullable=True, default=0)
    speed = Column(VARCHAR(255), nullable=True)
    eta = Column(VARCHAR(32), nullable=True)
    percent = Column(VARCHAR(32), nullable=True)
    retry = Column(Integer, nullable=False, default=0)
    error_message = Column(Text, nullable=True)


class DownloadTaskSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = DownloadTask
        load_instance = True
