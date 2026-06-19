import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import infrastructure.site_catalog.cookie_files as cookie_files


def test_cookie_files_import_does_not_require_backend_settings_env():
    backend_root = Path(__file__).resolve().parents[2]
    allowed_env = {
        key: value
        for key, value in os.environ.items()
        if key.upper() in {'PATH', 'PATHEXT', 'SYSTEMROOT', 'WINDIR', 'TEMP', 'TMP', 'PYTHONIOENCODING'}
    }
    result = subprocess.run(
        [
            sys.executable,
            '-c',
            (
                'import sys; '
                f'sys.path.insert(0, {str(backend_root)!r}); '
                'from infrastructure.site_catalog.cookie_files import get_site_cookies_dir; '
                'print(get_site_cookies_dir())'
            ),
        ],
        cwd=str(backend_root),
        env=allowed_env,
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout.strip().endswith(os.path.join('config', 'site_cookies'))


def test_write_cookie_text_file_replaces_existing_content(tmp_path):
    target = tmp_path / 'site_cookies' / 'youtube.txt'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text('old-value', encoding='utf-8')

    cookie_files.write_cookie_text_file(target, 'new-value\n')

    assert target.read_text(encoding='utf-8') == 'new-value\n'
    assert list(target.parent.glob('youtube*.tmp')) == []


def test_write_cookie_text_file_keeps_original_content_when_replace_fails(tmp_path, monkeypatch):
    target = tmp_path / 'site_cookies' / 'youtube.txt'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text('old-value', encoding='utf-8')

    original_replace = os.replace

    def _raise_replace(src, dst):
        raise OSError('replace failed')

    monkeypatch.setattr(cookie_files.os, 'replace', _raise_replace)

    with pytest.raises(OSError, match='replace failed'):
        cookie_files.write_cookie_text_file(target, 'new-value\n')

    monkeypatch.setattr(cookie_files.os, 'replace', original_replace)

    assert target.read_text(encoding='utf-8') == 'old-value'
    assert list(target.parent.glob('youtube*.tmp')) == []
