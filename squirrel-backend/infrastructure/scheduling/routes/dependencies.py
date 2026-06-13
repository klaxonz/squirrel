from infrastructure.scheduling.service import ScheduledTaskService
from shared_kernel.system.config import SystemConfigService


def get_system_config_service():
    return SystemConfigService()


def get_scheduled_task_service():
    return ScheduledTaskService()
