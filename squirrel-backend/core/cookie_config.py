from pathlib import Path
from typing import Optional

from core.config import settings



def get_site_cookies_dir() -> Path:
    return settings.config_dir / "site_cookies"


def get_site_cookies_file_path(site_slug: str) -> Path:
    safe_slug = (site_slug or "").strip().lower() or "default"
    return get_site_cookies_dir() / f"{safe_slug}.txt"


