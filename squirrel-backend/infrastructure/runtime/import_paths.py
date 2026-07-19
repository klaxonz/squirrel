from __future__ import annotations

import sys
from pathlib import Path

_RUNTIME_PACKAGES = ('bilibili', 'youtube')


def install_runtime_import_paths() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    runtimes_root = repo_root / 'squirrel-site-runtimes'
    paths = [runtimes_root / 'shared']
    paths.extend(runtimes_root / package / 'src' for package in _RUNTIME_PACKAGES)

    for path in reversed(paths):
        text = str(path)
        if text not in sys.path:
            sys.path.insert(0, text)
