import logging
import time
from threading import Event, Lock, Thread

from infrastructure.concurrency.thread_manager import thread_manager

logger = logging.getLogger(__name__)

# How long the run-loop blocks between ticks. Using an Event with this timeout
# keeps stop() responsive (no waiting out a full sleep) while bounding polling.
_POLL_INTERVAL_SECONDS = 1


class Scheduler:
    def __init__(self):
        self.jobs = []
        self._lock = Lock()
        self._stop_event = Event()

    @property
    def running(self) -> bool:
        """True while the scheduler loop is active (read under lock semantics)."""
        return not self._stop_event.is_set()

    def _resolve_job_name(self, func):
        """Return a readable job name for logging."""
        return getattr(func, '__qualname__', None) or getattr(func, '__name__', repr(func))

    def _run_job_with_trace(self, func, job_name):
        """Execute the job with a trace context."""
        from shared_kernel.infrastructure.trace import TraceContext

        with TraceContext():
            logger.info('Scheduled job started: %s', job_name)
            try:
                func()
            except Exception as e:  # task boundary -- prevent single failure from crashing scheduler
                logger.exception('Scheduled job failed: %s, error: %s', job_name, e)

    def _run_jobs(self):
        """Loop through jobs and run any that are due.

        Uses ``_stop_event.wait`` instead of ``time.sleep`` so ``stop()`` is
        responded to within the poll interval rather than blocking up to it.
        """
        while not self._stop_event.is_set():
            current_time = time.time()
            with self._lock:
                jobs_snapshot = self.jobs[:]
            for job in jobs_snapshot:
                if job['next_run'] <= current_time:
                    thread = Thread(target=self._run_job_with_trace, args=(job['func'], job['name']))
                    thread.start()
                    job['next_run'] += job['interval']
            # Interruptible wait: returns immediately when stop() sets the event.
            self._stop_event.wait(timeout=_POLL_INTERVAL_SECONDS)

    def add_job(self, func, interval, unit='seconds', start_immediately=True, job_name=None):
        """Add a scheduled job.

        Args:
            func: Function to execute
            interval: Interval value
            unit: Time unit, supports 'seconds', 'minutes', 'hours', 'days'
            start_immediately: Whether to execute immediately on first run
            job_name: Job name (optional)

        """
        if unit not in ['seconds', 'minutes', 'hours', 'days']:
            raise ValueError("unit must be 'seconds', 'minutes', 'hours', or 'days'")

        # Convert to seconds
        multipliers = {
            'seconds': 1,
            'minutes': 60,
            'hours': 3600,
            'days': 86400,
        }
        interval *= multipliers[unit]
        next_run = time.time() if start_immediately else time.time() + interval

        job = {
            'func': func,
            'interval': interval,
            'next_run': next_run,
            'name': job_name or self._resolve_job_name(func),
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
        if self._stop_event.is_set():
            self._stop_event.clear()
            thread = Thread(target=self._run_jobs, name='scheduler-run-loop', daemon=True)
            thread.start()
            thread_manager.register(thread)

    def stop(self):
        """Stop the scheduler.

        Signals the run loop via the event so the next ``wait()`` returns
        immediately instead of sleeping through the poll interval.
        """
        self._stop_event.set()
