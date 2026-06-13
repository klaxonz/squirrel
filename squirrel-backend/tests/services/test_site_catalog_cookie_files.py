import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import shared.site_catalog.cookie_files as cookie_files


def test_write_cookie_text_file_replaces_existing_content(tmp_path):
    target = tmp_path / "site_cookies" / "youtube.txt"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("old-value", encoding="utf-8")

    cookie_files.write_cookie_text_file(target, "new-value\n")

    assert target.read_text(encoding="utf-8") == "new-value\n"
    assert list(target.parent.glob("youtube*.tmp")) == []


def test_write_cookie_text_file_keeps_original_content_when_replace_fails(tmp_path, monkeypatch):
    target = tmp_path / "site_cookies" / "youtube.txt"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("old-value", encoding="utf-8")

    original_replace = os.replace

    def _raise_replace(src, dst):
        raise OSError("replace failed")

    monkeypatch.setattr(cookie_files.os, "replace", _raise_replace)

    with pytest.raises(OSError, match="replace failed"):
        cookie_files.write_cookie_text_file(target, "new-value\n")

    monkeypatch.setattr(cookie_files.os, "replace", original_replace)

    assert target.read_text(encoding="utf-8") == "old-value"
    assert list(target.parent.glob("youtube*.tmp")) == []
