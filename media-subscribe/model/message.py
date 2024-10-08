from datetime import datetime

from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
from sqlalchemy import Integer, Column, Text, VARCHAR, DateTime

from common.database import ModelBase


class Message(ModelBase):
    __tablename__ = 'message'

    message_id = Column(Integer, primary_key=True)
    body = Column(Text, nullable=False)
    send_status = Column(VARCHAR(32), nullable=False, default='PENDING')
    retry_count = Column(Integer, nullable=False, default=0)
    next_retry_time = Column(DateTime, nullable=True, default=datetime.now)


class MessageSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Message
        load_instance = True
