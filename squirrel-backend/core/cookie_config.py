from pathlib import Path
from typing import Optional

from core.config import settings


def get_cookies_file_path() -> Path:
    return settings.config_dir / 'cookies.txt'


