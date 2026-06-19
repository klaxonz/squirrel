import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts import backfill_thumbnail_local_index


def test_backfill_thumbnail_local_index_scans_batches_and_upserts_in_chunks(monkeypatch, tmp_path):
    batch_001 = tmp_path / 'batch_001'
    batch_002 = tmp_path / 'batch_002'
    batch_001.mkdir()
    batch_002.mkdir()

    (batch_001 / '101.jpg').write_bytes(b'a')
    (batch_001 / '102.webp').write_bytes(b'd')
    (batch_001 / 'ignore.txt').write_text('skip')
    (batch_001 / 'bad-name.webp').write_bytes(b'b')
    (batch_002 / '202.png').write_bytes(b'c')

    captured_batches = []
    monkeypatch.setattr(
        backfill_thumbnail_local_index,
        'load_existing_batch_records',
        lambda batch_name: set(),
        raising=False,
    )

    monkeypatch.setattr(
        backfill_thumbnail_local_index,
        'upsert_thumbnail_records',
        lambda records: captured_batches.append(list(records)) or len(records),
    )

    processed = backfill_thumbnail_local_index.backfill_thumbnail_local_index(
        thumbnails_dir=tmp_path,
    )

    assert processed == 3
    assert captured_batches == [
        [(101, 'batch_001', '101.jpg'), (102, 'batch_001', '102.webp')],
        [(202, 'batch_002', '202.png')],
    ]


def test_backfill_thumbnail_local_index_skips_completed_batches(monkeypatch, tmp_path):
    batch_001 = tmp_path / 'batch_001'
    batch_002 = tmp_path / 'batch_002'
    batch_001.mkdir()
    batch_002.mkdir()

    (batch_001 / '101.jpg').write_bytes(b'a')
    (batch_002 / '202.png').write_bytes(b'c')

    monkeypatch.setattr(
        backfill_thumbnail_local_index,
        'load_existing_batch_records',
        lambda batch_name: {'101.jpg'} if batch_name == 'batch_001' else {},
        raising=False,
    )

    captured_batches = []
    monkeypatch.setattr(
        backfill_thumbnail_local_index,
        'upsert_thumbnail_records',
        lambda records: captured_batches.append(list(records)) or len(records),
    )

    processed = backfill_thumbnail_local_index.backfill_thumbnail_local_index(
        thumbnails_dir=tmp_path,
    )

    assert processed == 1
    assert captured_batches == [
        [(202, 'batch_002', '202.png')],
    ]


def test_backfill_thumbnail_local_index_resumes_from_checkpoint(monkeypatch, tmp_path):
    batch_001 = tmp_path / 'batch_001'
    batch_002 = tmp_path / 'batch_002'
    batch_001.mkdir()
    batch_002.mkdir()

    (batch_001 / '101.jpg').write_bytes(b'a')
    (batch_002 / '202.png').write_bytes(b'c')

    checkpoint_file = tmp_path / '.thumbnail-index-backfill.state'
    checkpoint_file.write_text('batch_001', encoding='utf-8')
    scanned_batches = []

    monkeypatch.setattr(
        backfill_thumbnail_local_index,
        'load_existing_batch_records',
        lambda batch_name: {},
        raising=False,
    )
    original_collect_batch_records = backfill_thumbnail_local_index.collect_batch_records
    monkeypatch.setattr(
        backfill_thumbnail_local_index,
        'collect_batch_records',
        lambda batch_dir: scanned_batches.append(batch_dir.name) or original_collect_batch_records(batch_dir),
    )

    captured_batches = []
    monkeypatch.setattr(
        backfill_thumbnail_local_index,
        'upsert_thumbnail_records',
        lambda records: captured_batches.append(list(records)) or len(records),
    )

    processed = backfill_thumbnail_local_index.backfill_thumbnail_local_index(
        thumbnails_dir=tmp_path,
        checkpoint_file=checkpoint_file,
    )

    assert processed == 1
    assert captured_batches == [
        [(202, 'batch_002', '202.png')],
    ]
    assert scanned_batches == ['batch_002']
    checkpoint_data = json.loads(checkpoint_file.read_text(encoding='utf-8'))
    assert checkpoint_data == {
        'completed': ['batch_001', 'batch_002'],
    }


def test_backfill_thumbnail_local_index_script_runs_from_backend_root():
    backend_root = Path(__file__).resolve().parents[2]

    result = subprocess.run(
        [sys.executable, 'scripts/backfill_thumbnail_local_index.py', '--help'],
        cwd=backend_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert 'Backfill thumbnail local index' in result.stdout
    assert '--workers' in result.stdout
