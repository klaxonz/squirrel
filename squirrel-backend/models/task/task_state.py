from enum import Enum
from typing import Dict, List


class TaskState(Enum):
    PENDING = "pending"  # 等待下载
    DOWNLOADING = "downloading"  # 下载中
    PAUSED = "paused"  # 已暂停
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 下载失败
    DELETED = "deleted"  # 已删除


class TaskStateTransition:
    _transitions: Dict[TaskState, List[TaskState]] = {
        TaskState.PENDING: [TaskState.DOWNLOADING, TaskState.DELETED],
        TaskState.DOWNLOADING: [TaskState.PAUSED, TaskState.COMPLETED, TaskState.FAILED],
        TaskState.PAUSED: [TaskState.DOWNLOADING, TaskState.DELETED],
        TaskState.COMPLETED: [TaskState.DELETED],
        TaskState.FAILED: [TaskState.PENDING, TaskState.DELETED],
        TaskState.DELETED: []
    }

    @classmethod
    def can_transition(cls, from_state: str, to_state: str) -> bool:
        """
        检查状态转换是否允许
        """
        try:
            from_enum = TaskState(from_state)
            to_enum = TaskState(to_state)
            return to_enum in cls._transitions[from_enum]
        except (ValueError, KeyError):
            return False

    @classmethod
    def get_allowed_transitions(cls, current_state: str) -> List[str]:
        """
        获取当前状态允许转换的所有目标状态
        """
        try:
            state_enum = TaskState(current_state)
            return [state.value for state in cls._transitions[state_enum]]
        except (ValueError, KeyError):
            return []
