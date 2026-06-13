from datetime import timedelta

DUE_SOON_WINDOW = timedelta(minutes=30)
FEED_RECENT_PHASES = {'extracting', 'finalizing', 'completed'}
TERMINAL_RUN_STATUSES = {'success', 'failed', 'deferred', 'timeout'}
