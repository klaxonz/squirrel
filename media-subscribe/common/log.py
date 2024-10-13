# 定义日志配置字典
import logging.config
import os

current_dir = os.path.dirname(os.getcwd())
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
            'level': 'DEBUG',  # 控制台日志级别
        },
        'file': {
            'class': 'logging.FileHandler',  # 如果需要记录到文件
            'filename': os.path.join(LOG_DIR, 'app.log.py'),  # 日志文件名
            'formatter': 'default',
            'level': 'INFO',  # 文件日志级别
        },
    },
    'root': {  # 全局日志配置
        'handlers': ['console', 'file'],  # 同时输出到控制台和文件
        'level': 'DEBUG',  # 应用默认日志级别
    },
}


def init_logging():
    logging.config.dictConfig(LOGGING_CONFIG)
