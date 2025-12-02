import logging
import time
from threading import Thread

logger = logging.getLogger()


class Scheduler:
    def __init__(self):
        self.jobs = []
        self.running = False

    def _run_job_with_trace(self, func):
        """Execute the job with a trace context."""
        from utils.trace import TraceContext
        
        with TraceContext():
            logger.info(f"Scheduled job started: {func.__name__}")
            try:
                func()
            except Exception as e:
                logger.exception(f"Scheduled job failed: {func.__name__}, error: {e}")

    def _run_jobs(self):
        """Loop through jobs and run any that are due."""
        while self.running:
            current_time = time.time()
            for job in self.jobs[:]:
                if job['next_run'] <= current_time:
                    thread = Thread(target=self._run_job_with_trace, args=(job['func'],))
                    thread.start()
                    job['next_run'] += job['interval']
            time.sleep(1)

    def add_job(self, func, interval, unit='seconds', start_immediately=True):
        """Add a scheduled job."""
        if unit not in ['seconds', 'minutes']:
            raise ValueError("unit must be 'seconds' or 'minutes'")

        interval *= 60 if unit == 'minutes' else 1
        next_run = time.time() if start_immediately else time.time() + interval

        self.jobs.append({
            'func': func,
            'interval': interval,
            'next_run': next_run,
        })

    def start(self):
        """Start the scheduler."""
        if not self.running:
            self.running = True
            thread = Thread(target=self._run_jobs)
            thread.daemon = True
            thread.start()

    def stop(self):
        """Stop the scheduler."""
        self.running = False
