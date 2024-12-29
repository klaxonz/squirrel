# 定义日志配置字典
import logging.config
import os

current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(current_dir, '..', 'logs')
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'default': {
            'format': '%(asctime)s %(levelname)s %(name)s: %(message)s',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'default',
            'level': 'INFO',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': os.path.join(LOG_DIR, 'app.log'),
            'formatter': 'default',
            'level': 'INFO',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
}


def init_logging():
    # 确保在配置之前清除所有已存在的处理器
    for logger_name in ['', 'alembic', 'alembic.runtime.migration', 'uvicorn', 'uvicorn.error', 'uvicorn.access']:
        logger = logging.getLogger(logger_name)
        if logger.handlers:
            for handler in logger.handlers:
                logger.removeHandler(handler)

    logging.config.dictConfig(LOGGING_CONFIG)
