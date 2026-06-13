import os
import tempfile
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

if os.name == "nt":
    import msvcrt
else:
    import fcntl

from core.config import settings

_COOKIE_FILE_LOCKS: dict[str, threading.Lock] = {}
_COOKIE_FILE_LOCKS_GUARD = threading.Lock()


def get_site_cookies_dir() -> Path:
    return settings.config_dir / "site_cookies"


def get_site_cookies_file_path(site_slug: str) -> Path:
    safe_slug = (site_slug or "").strip().lower() or "default"
    cookies_dir = get_site_cookies_dir().resolve()
    candidate = cookies_dir / f"{safe_slug}.txt"
    resolved = candidate.resolve()
    if not resolved.is_relative_to(cookies_dir):
        return cookies_dir / "default.txt"
    return resolved


def _get_cookie_file_thread_lock(lock_path: Path) -> threading.Lock:
    lock_key = str(lock_path.resolve())
    with _COOKIE_FILE_LOCKS_GUARD:
        lock = _COOKIE_FILE_LOCKS.get(lock_key)
        if lock is None:
            lock = threading.Lock()
            _COOKIE_FILE_LOCKS[lock_key] = lock
        return lock


def _lock_file_handle(handle) -> None:
    if os.name == "nt":
        handle.seek(0)
        if handle.tell() == 0 and handle.read(1) == b"":
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        return

    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)


def _unlock_file_handle(handle) -> None:
    if os.name == "nt":
        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        return

    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


@contextmanager
def _site_cookie_file_lock(lock_path: Path, timeout_seconds: float = 30.0) -> Iterator[None]:
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    thread_lock = _get_cookie_file_thread_lock(lock_path)

    with thread_lock, open(lock_path, "a+b") as handle:
        deadline = time.monotonic() + timeout_seconds
        while True:
            try:
                _lock_file_handle(handle)
                break
            except OSError:
                if time.monotonic() >= deadline:
                    raise TimeoutError(f"Failed to acquire cookie file lock: {lock_path}")
                time.sleep(0.05)

        try:
            yield
        finally:
            _unlock_file_handle(handle)


def write_cookie_text_file(target_path: Path, content: str, encoding: str = "utf-8") -> None:
    target = Path(target_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    lock_path = target.with_name(f"{target.name}.lock")

    with _site_cookie_file_lock(lock_path):
        temp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                "w",
                encoding=encoding,
                dir=target.parent,
                delete=False,
                prefix=f"{target.stem}.",
                suffix=".tmp",
            ) as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
                temp_path = Path(handle.name)

            os.replace(temp_path, target)
        except OSError:
            if temp_path is not None:
                try:
                    temp_path.unlink(missing_ok=True)
                except OSError:
                    pass
            raise

