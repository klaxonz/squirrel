import argparse
import json
import logging
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Iterator

from sqlalchemy import or_, select
from sqlalchemy.dialects.postgresql import insert

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.config import settings
from core.database import get_session
from core.extraction.services.thumbnail_downloader import SUPPORTED_EXTENSIONS
from models.video_thumbnail_local_index import VideoThumbnailLocalIndex

logger = logging.getLogger(__name__)


def iter_batch_dirs(thumbnails_dir: Path) -> Iterator[Path]:
    for batch_dir in sorted(thumbnails_dir.glob('batch_*')):
        if batch_dir.is_dir():
            yield batch_dir


def collect_batch_records(batch_dir: Path) -> list[tuple[int, str, str]]:
    records: list[tuple[int, str, str]] = []
    batch_name = batch_dir.name

    for file_path in sorted(batch_dir.iterdir()):
        if not file_path.is_file():
            continue
        if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        try:
            video_id = int(file_path.stem)
        except ValueError:
            continue
        records.append((video_id, batch_name, file_path.name))

    return records


def load_existing_batch_records(batch_name: str) -> set[str]:
    with get_session() as session:
        rows = session.execute(
            select(VideoThumbnailLocalIndex.filename)
            .where(
                VideoThumbnailLocalIndex.batch_name == batch_name,
                VideoThumbnailLocalIndex.exists.is_(True),
            )
        ).all()
    return {row.filename for row in rows}


def load_completed_batches(
    checkpoint_file: Path | None,
    batch_names: list[str],
) -> set[str]:
    if checkpoint_file is None or not checkpoint_file.exists():
        return set()

    raw_text = checkpoint_file.read_text(encoding='utf-8').strip()
    if not raw_text:
        return set()

    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError:
        payload = None

    if isinstance(payload, dict):
        completed = payload.get('completed') or []
        return {str(item) for item in completed}

    legacy_cutoff = raw_text
    return {batch_name for batch_name in batch_names if batch_name <= legacy_cutoff}


def write_checkpoint(checkpoint_file: Path | None, completed_batches: set[str]) -> None:
    if checkpoint_file is None:
        return
    checkpoint_file.parent.mkdir(parents=True, exist_ok=True)
    checkpoint_file.write_text(
        json.dumps({'completed': sorted(completed_batches)}, ensure_ascii=True, indent=2),
        encoding='utf-8',
    )


def upsert_thumbnail_records(records: list[tuple[int, str, str]]) -> int:
    if not records:
        return 0

    now = datetime.now()
    values = [
        {
            'video_id': video_id,
            'batch_name': batch_name,
            'filename': filename,
            'exists': True,
            'indexed_at': now,
            'created_at': now,
            'updated_at': now,
        }
        for video_id, batch_name, filename in records
    ]

    with get_session() as session:
        statement = insert(VideoThumbnailLocalIndex).values(values)
        statement = statement.on_conflict_do_update(
            index_elements=['video_id'],
            set_={
                'batch_name': statement.excluded.batch_name,
                'filename': statement.excluded.filename,
                'exists': statement.excluded.exists,
                'indexed_at': statement.excluded.indexed_at,
                'updated_at': statement.excluded.updated_at,
            },
            where=or_(
                VideoThumbnailLocalIndex.batch_name != statement.excluded.batch_name,
                VideoThumbnailLocalIndex.filename != statement.excluded.filename,
                VideoThumbnailLocalIndex.exists.is_(False),
            ),
        )
        session.execute(statement)

    return len(values)


def backfill_thumbnail_local_index(
    thumbnails_dir: Path,
    checkpoint_file: Path | None = None,
    workers: int = 1,
) -> int:
    batch_dirs = list(iter_batch_dirs(thumbnails_dir))
    completed_batches = load_completed_batches(
        checkpoint_file=checkpoint_file,
        batch_names=[batch_dir.name for batch_dir in batch_dirs],
    )
    pending_batch_dirs = [
        batch_dir
        for batch_dir in batch_dirs
        if batch_dir.name not in completed_batches
    ]
    processed = 0
    completed_lock = Lock()

    for batch_name in sorted(completed_batches):
        logger.info('[ThumbnailIndexBackfill] skip batch=%s reason=checkpoint', batch_name)

    def _process_batch(batch_dir: Path) -> tuple[str, int, int, str]:
        batch_name = batch_dir.name
        batch_records = collect_batch_records(batch_dir)
        existing_filenames = load_existing_batch_records(batch_name)
        batch_filenames = {filename for _video_id, _batch_name, filename in batch_records}
        if existing_filenames == batch_filenames:
            return batch_name, 0, len(batch_records), 'already-indexed'

        records_to_upsert = [
            record for record in batch_records
            if record[2] not in existing_filenames
        ]
        if not records_to_upsert:
            return batch_name, 0, len(batch_records), 'no-delta'

        indexed_count = upsert_thumbnail_records(records_to_upsert)
        return batch_name, indexed_count, len(batch_records) - len(records_to_upsert), 'indexed'

    with ThreadPoolExecutor(max_workers=max(workers, 1)) as executor:
        futures = [
            executor.submit(_process_batch, batch_dir)
            for batch_dir in pending_batch_dirs
        ]
        for future in as_completed(futures):
            batch_name, indexed_count, skipped_count, status = future.result()
            with completed_lock:
                processed += indexed_count
                completed_batches.add(batch_name)
                write_checkpoint(checkpoint_file, completed_batches)
                total = processed

            if status == 'already-indexed':
                logger.info('[ThumbnailIndexBackfill] skip batch=%s reason=already-indexed', batch_name)
                continue

            logger.info(
                '[ThumbnailIndexBackfill] batch=%s indexed=%d skipped=%d total=%d',
                batch_name,
                indexed_count,
                skipped_count,
                total,
            )

    return processed


def main() -> None:
    parser = argparse.ArgumentParser(description='Backfill thumbnail local index from existing thumbnail files.')
    parser.add_argument('--path', type=Path, default=settings.thumbnails_dir, help='Thumbnail root directory.')
    parser.add_argument(
        '--checkpoint-file',
        type=Path,
        default=PROJECT_ROOT / '.thumbnail-index-backfill.state',
        help='Checkpoint file used to resume processed batches.',
    )
    parser.add_argument(
        '--workers',
        type=int,
        default=4,
        help='Number of batch directories processed in parallel.',
    )
    args = parser.parse_args()

    total = backfill_thumbnail_local_index(
        thumbnails_dir=args.path,
        checkpoint_file=args.checkpoint_file,
        workers=max(args.workers, 1),
    )
    logger.info(
        '[ThumbnailIndexBackfill] completed processed=%d path=%s checkpoint=%s workers=%d',
        total,
        args.path,
        args.checkpoint_file,
        max(args.workers, 1),
    )


if __name__ == '__main__':
    main()
