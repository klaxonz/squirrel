#!/usr/bin/env python3
"""Final pass to update remaining imports."""

import os
import re
from pathlib import Path

# Additional mappings for patterns not caught by the first pass
ADDITIONAL_MAPPINGS = [
    # shared.kernel imports (without specific module)
    (r'from shared\.kernel import response', 'from shared_kernel.application import response'),
    (r'from shared\.kernel import module_discovery', 'from shared_kernel.infrastructure import module_discovery'),

    # shared.kernel.system
    (r'from shared\.kernel\.system\.', 'from shared_kernel.system.'),

    # Old core imports that might remain
    (r'from core\.config import settings', 'from infrastructure.config.settings import settings'),
    (r'from core\.database import', 'from infrastructure.database.session import'),
    (r'from core\.cache import', 'from infrastructure.cache.redis_client import'),
]


def update_file(file_path: Path) -> bool:
    """Update imports in a single file. Returns True if file was modified."""
    try:
        content = file_path.read_text(encoding='utf-8')
    except Exception:
        return False

    original = content

    for pattern, replacement in ADDITIONAL_MAPPINGS:
        content = re.sub(pattern, replacement, content)

    if content != original:
        file_path.write_text(content, encoding='utf-8')
        return True
    return False


def main():
    # Process all Python files in the project
    count = 0
    for py_file in Path('.').rglob('*.py'):
        # Skip old directories that will be deleted
        if any(part in py_file.parts for part in ['core', 'shared', 'video', 'subscription', 'user', 'playlist', 'rss', 'music', 'routes', 'runtime', 'site_runtimes', 'extraction', 'messaging', 'scheduling']):
            continue
        if 'update_imports.py' in str(py_file):
            continue
        if update_file(py_file):
            count += 1
            print(f"Updated: {py_file}")

    print(f"\nTotal files updated: {count}")


if __name__ == '__main__':
    main()
