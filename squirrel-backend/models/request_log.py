from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, Float
from models import Base
from models.mixins.serializer import SerializerMixin


class ExternalRequestLog(Base, SerializerMixin):
    """External API request log model"""
    __tablename__ = 'external_request_log'

    id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(Text, nullable=False)
    domain = Column(String(255), nullable=False)
    method = Column(String(10), nullable=False)
    params = Column(Text, nullable=True)
    body = Column(Text, nullable=True)
    size = Column(Integer, nullable=False)
    status_code = Column(Integer, nullable=False)
    duration = Column(Float, nullable=False)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)


