import logging.config
import logging.handlers
import os
import sys

from shared_kernel.infrastructure.trace import format_trace_id, get_trace_id

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
    """Add trace_id field to log records"""

    def filter(self, record):
        try:
            trace_id = get_trace_id()
            record.trace_id = format_trace_id(trace_id)
        except (ValueError, TypeError):
            record.trace_id = '-'
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
            '()': 'shared_kernel.infrastructure.log.TraceIdFilter',
        },
    },
    'handlers': {
        'console': {
            'class': 'shared_kernel.infrastructure.log.SafeStreamHandler',
            'formatter': 'default',
            'level': 'INFO',
            'stream': 'ext://sys.stdout',
            'filters': ['trace_id'],
        },
        'file': {
            'class': 'concurrent_log_handler.ConcurrentRotatingFileHandler',
            'filename': os.path.join(LOG_DIR, 'app.log'),
            'formatter': 'default',
            'level': 'INFO',
            'encoding': 'utf-8',
            'filters': ['trace_id'],
            'maxBytes': 50 * 1024 * 1024,
            'backupCount': 10,
        },
        'error_file': {
            'class': 'concurrent_log_handler.ConcurrentRotatingFileHandler',
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
