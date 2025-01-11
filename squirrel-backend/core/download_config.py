import os
from pathlib import Path

from pathvalidate import sanitize_filename

from core import config

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_download_root_path():
    download_path = Path(os.path.join(base_dir, '..', 'downloads'))
    return os.getenv('MEDIA_DOWNLOAD_PATH', download_path)


def get_cookies_file_path_thread(queue_thread_name: str):
    queue_thread_name = queue_thread_name.replace(':', '-')
    cookie_path = Path(os.path.join(base_dir, '..', 'config', f'cookies-{queue_thread_name}.txt'))
    with open(cookie_path, 'w') as wf:
        with open(config.get_cookies_file_path(), 'r') as rf:
            wf.write(rf.read())
    return os.path.normpath(cookie_path)


def get_cookies_http_file_path():
    http_cookie_path = Path(os.path.join(base_dir, '..', 'config', 'cookies_http.txt'))
    return os.path.normpath(http_cookie_path)


def get_tv_show_root_path(subscription_name: str):
    root_path = get_download_root_path()
    subscription_name = get_valid_uploader_name(subscription_name)
    return os.path.join(root_path, subscription_name)


def get_download_full_path(subscription_name: str, season: int):
    root_path = get_download_root_path()
    uploader_name = get_valid_uploader_name(subscription_name)
    return os.path.join(root_path, uploader_name, f"Season {season}")


def get_valid_uploader_name(subscription_name: str):
    return sanitize_filename(subscription_name)


def get_valid_filename(title):
    return sanitize_filename(title)
