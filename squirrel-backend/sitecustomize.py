from __future__ import annotations

import sys
from pathlib import Path

_runtime_shared = Path(__file__).resolve().parents[1] / 'squirrel-site-runtimes' / 'shared'
if _runtime_shared.is_dir():
    sys.path.insert(0, str(_runtime_shared))
