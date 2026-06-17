from domains.system.application.services.config_service import SystemConfigService
from infrastructure.scheduling.service import ScheduledTaskService


def get_system_config_service():
    return SystemConfigService()


def get_scheduled_task_service():
    return ScheduledTaskService()
