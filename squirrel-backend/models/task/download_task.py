from datetime import datetime
from typing import Optional, List

from sqlalchemy import BigInteger, Integer, Text
from sqlalchemy.dialects.mysql import VARCHAR
from sqlalchemy.orm import Mapped, mapped_column

from models import Base
from models.mixins.serializer import SerializerMixin
from models.task.task_state import TaskStateTransition


class DownloadTask(Base, SerializerMixin):
    __tablename__ = 'download_task'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    video_id: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(VARCHAR(32), nullable=False, default='PENDING')
    downloaded_size: Mapped[int] = mapped_column(BigInteger, nullable=True, default=0)
    total_size: Mapped[int] = mapped_column(BigInteger, nullable=True, default=0)
    speed: Mapped[Optional[str]] = mapped_column(VARCHAR(255), nullable=True)
    eta: Mapped[Optional[str]] = mapped_column(VARCHAR(32), nullable=True)
    percent: Mapped[Optional[str]] = mapped_column(VARCHAR(32), nullable=True)
    retry: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(),
        onupdate=lambda: datetime.now()
    )

    def transition_to(self, new_state: str) -> bool:
        """
        将任务转换到新状态
        返回是否转换成功
        """
        if TaskStateTransition.can_transition(self.status, new_state):
            self.status = new_state
            return True
        return False

    @property
    def allowed_transitions(self) -> List[str]:
        """
        获取当前允许的状态转换列表
        """
        return TaskStateTransition.get_allowed_transitions(self.status)

