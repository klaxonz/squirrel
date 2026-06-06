import logging.config
import logging.handlers
import os
import sys

try:
    from concurrent_log_handler import ConcurrentRotatingFileHandler
    USE_CONCURRENT_HANDLER = True
except ImportError:
    USE_CONCURRENT_HANDLER = False

current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(current_dir, '..', 'logs')
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)


class SafeStreamHandler(logging.StreamHandler):
    def emit(self, record):
        try:
            super().emit(record)
        except UnicodeEncodeError:
            msg = self.format(record)
            stream = self.stream
            enc = getattr(stream, 'encoding', None) or 'utf-8'
            safe = msg.encode(enc, errors='replace').decode(enc, errors='replace') + self.terminator
            stream.write(safe)


class TraceIdFilter(logging.Filter):
    """为日志记录添加 trace_id 字段"""
    
    def __init__(self):
        super().__init__()
        self._get_trace_id = None
        self._format_trace_id = None
    
    def _ensure_imports(self):
        """延迟导入，避免循环依赖"""
        if self._get_trace_id is None:
            try:
                from utils.trace import get_trace_id, format_trace_id
                self._get_trace_id = get_trace_id
                self._format_trace_id = format_trace_id
            except ImportError:
                # 如果导入失败，使用默认值
                self._get_trace_id = lambda: None
                self._format_trace_id = lambda x: "-"
    
    def filter(self, record):
        self._ensure_imports()
        try:
            trace_id = self._get_trace_id()
            record.trace_id = self._format_trace_id(trace_id)
        except (ValueError, TypeError):
            # 如果获取失败，使用默认值
            record.trace_id = "-"
        return True


LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'default': {
            'format': '%(asctime)s [%(trace_id)s] %(levelname)s %(name)s: %(message)s',
        },
    },
    'filters': {
        'trace_id': {
            '()': 'common.log.TraceIdFilter',
        },
    },
    'handlers': {
        'console': {
            'class': 'common.log.SafeStreamHandler',
            'formatter': 'default',
            'level': 'INFO',
            'stream': 'ext://sys.stdout',
            'filters': ['trace_id'],
        },
        'file': {
            'class': 'concurrent_log_handler.ConcurrentRotatingFileHandler' if USE_CONCURRENT_HANDLER else 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(LOG_DIR, 'app.log'),
            'formatter': 'default',
            'level': 'INFO',
            'encoding': 'utf-8',
            'filters': ['trace_id'],
            'maxBytes': 50 * 1024 * 1024,
            'backupCount': 10,
        },
        'error_file': {
            'class': 'concurrent_log_handler.ConcurrentRotatingFileHandler' if USE_CONCURRENT_HANDLER else 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(LOG_DIR, 'error.log'),
            'formatter': 'default',
            'level': 'ERROR',
            'encoding': 'utf-8',
            'filters': ['trace_id'],
            'maxBytes': 20 * 1024 * 1024,
            'backupCount': 5,
        },
    },
    'loggers': {
        'httpx': {
            'level': 'WARNING',
            'propagate': True,
        },
        'httpcore': {
            'level': 'WARNING',
            'propagate': True,
        },
        'redis_lock': {
            'level': 'WARNING',
            'propagate': True,
        },
        'squirrel.access': {
            'level': 'INFO',
            'propagate': True,
        },
    },
    'root': {
        'handlers': ['console', 'file', 'error_file'],
        'level': 'INFO',
    },
}


def init_logging():
    for logger_name in ['', 'alembic', 'alembic.runtime.migration', 'uvicorn', 'uvicorn.error', 'uvicorn.access']:
        logger = logging.getLogger(logger_name)
        if logger.handlers:
            for handler in logger.handlers:
                logger.removeHandler(handler)
    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        if hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except (OSError, ValueError, TypeError):
        pass
    logging.config.dictConfig(LOGGING_CONFIG)
