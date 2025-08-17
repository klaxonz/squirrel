import logging.config
import os
import sys

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
            'class': 'common.log.SafeStreamHandler',
            'formatter': 'default',
            'level': 'INFO',
            'stream': 'ext://sys.stdout',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': os.path.join(LOG_DIR, 'app.log'),
            'formatter': 'default',
            'level': 'INFO',
            'encoding': 'utf-8',
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
    },
    'root': {
        'handlers': ['console', 'file'],
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
    except Exception:
        pass
    logging.config.dictConfig(LOGGING_CONFIG)
