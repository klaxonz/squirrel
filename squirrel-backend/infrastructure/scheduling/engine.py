import logging
import time
from threading import Lock, Thread

logger = logging.getLogger(__name__)


class Scheduler:
    def __init__(self):
        self.jobs = []
        self.running = False
        self._lock = Lock()

    def _resolve_job_name(self, func):
        """Return a readable job name for logging."""
        return getattr(func, "__qualname__", None) or getattr(func, "__name__", repr(func))

    def _run_job_with_trace(self, func, job_name):
        """Execute the job with a trace context."""
        from shared_kernel.infrastructure.trace import TraceContext

        with TraceContext():
            logger.info("Scheduled job started: %s", job_name)
            try:
                func()
            except Exception as e:  # task boundary -- prevent single failure from crashing scheduler
                logger.exception("Scheduled job failed: %s, error: %s", job_name, e)

    def _run_jobs(self):
        """Loop through jobs and run any that are due."""
        while self.running:
            current_time = time.time()
            with self._lock:
                jobs_snapshot = self.jobs[:]
            for job in jobs_snapshot:
                if job["next_run"] <= current_time:
                    thread = Thread(target=self._run_job_with_trace, args=(job["func"], job["name"]))
                    thread.start()
                    job["next_run"] += job["interval"]
            time.sleep(1)

    def add_job(self, func, interval, unit="seconds", start_immediately=True, job_name=None):
        """Add a scheduled job.

        Args:
            func: Function to execute
            interval: Interval value
            unit: Time unit, supports 'seconds', 'minutes', 'hours', 'days'
            start_immediately: Whether to execute immediately on first run
            job_name: Job name (optional)

        """
        if unit not in ["seconds", "minutes", "hours", "days"]:
            raise ValueError("unit must be 'seconds', 'minutes', 'hours', or 'days'")

        # Convert to seconds
        multipliers = {
            "seconds": 1,
            "minutes": 60,
            "hours": 3600,
            "days": 86400,
        }
        interval *= multipliers[unit]
        next_run = time.time() if start_immediately else time.time() + interval

        job = {
            "func": func,
            "interval": interval,
            "next_run": next_run,
            "name": job_name or self._resolve_job_name(func),
        }
        with self._lock:
            self.jobs.append(job)
        return job

    def remove_job(self, job) -> bool:
        """Remove a scheduled job."""
        with self._lock:
            try:
                self.jobs.remove(job)
                return True
            except ValueError:
                return False

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
