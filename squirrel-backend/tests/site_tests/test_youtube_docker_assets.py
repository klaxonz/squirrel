from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_dockerignore_keeps_youtube_worker_build_assets():
    dockerignore = (ROOT / '.dockerignore').read_text(encoding='utf-8')
    gitignore = (ROOT / '.gitignore').read_text(encoding='utf-8')

    assert 'squirrel-backend/sites/squirrel_youtube/node/build' not in dockerignore
    assert '!squirrel-backend/sites/squirrel_youtube/node/build/' in gitignore
    assert '!squirrel-backend/sites/squirrel_youtube/node/build/*.js' in gitignore
