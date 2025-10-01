from pathlib import Path
from typing import Optional

from core.config import settings


def get_cookies_file_path() -> Path:
    return settings.config_dir / 'cookies.txt'


def get_cookies_http_file_path() -> Path:
    return settings.config_dir / 'cookies_http.txt'


def get_cookies_file_path_for_thread(queue_thread_name: Optional[str] = None) -> Path:
    if not queue_thread_name:
        return get_cookies_file_path()
    
    safe_thread_name = queue_thread_name.replace(':', '-')
    return settings.config_dir / f'cookies-{safe_thread_name}.txt'


def copy_cookies_for_thread(queue_thread_name: str) -> Path:
    """
    为特定线程创建 cookies 文件副本
    注意：此函数有副作用（文件 I/O 操作）
    """
    target_path = get_cookies_file_path_for_thread(queue_thread_name)
    source_path = get_cookies_file_path()
    
    target_path.write_text(source_path.read_text())
    
    return target_path

