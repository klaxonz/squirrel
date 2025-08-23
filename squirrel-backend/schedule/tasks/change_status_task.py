import json
import logging
from core.database import get_session
from models.task.download_task import DownloadTask
from models.task.task_state import TaskState
from schedule.task import TaskRegistry, BaseTask

logger = logging.getLogger(__name__)


@TaskRegistry.register(interval=1, unit='minutes')
class ChangeStatusTask(BaseTask):
    @classmethod
    def run(cls):
        try:
            with get_session() as session:
                session.query(DownloadTask).filter(DownloadTask.status == TaskState.PENDING.value,
                                                   DownloadTask.retry >= 5).update({
                    DownloadTask.status: TaskState.FAILED.value
                })
                session.commit()

        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}", exc_info=True)
