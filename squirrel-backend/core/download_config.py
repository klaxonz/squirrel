import os
from pathlib import Path

from pathvalidate import sanitize_filename


base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_download_root_path():
    download_path = Path(os.path.join(base_dir, '..', 'downloads'))
    return os.getenv('MEDIA_DOWNLOAD_PATH', download_path)


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
