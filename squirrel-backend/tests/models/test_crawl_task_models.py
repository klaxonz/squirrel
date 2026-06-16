import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from domains.subscription.domain.models.crawl_job import CrawlJob
from domains.subscription.domain.models.crawl_task import CrawlTask
from shared_kernel.domain.base import Base


def test_crawl_task_defaults_to_pending():
    task = CrawlTask(
        job_id=1,
        task_type="video_extract",
        site="youtube",
        priority="normal",
        payload={},
    )

    assert task.status == "pending"
    assert task.attempt == 0
    assert task.max_attempts == 3


def test_crawl_task_dedupe_key_is_unique():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[CrawlJob.__table__, CrawlTask.__table__])

    with Session(engine, expire_on_commit=False) as session:
        job = CrawlJob(
            job_type="subscription_sync",
            source_type="manual",
            site="youtube",
            subscription_id=1,
            priority="manual",
            status="pending",
            payload={},
        )
        session.add(job)
        session.commit()

        session.add(
            CrawlTask(
                job_id=job.id,
                task_type="video_extract",
                site="youtube",
                priority="normal",
                payload={},
                dedupe_key="video_extract:https://example.com/watch?v=1",
            ),
        )
        session.commit()

        session.add(
            CrawlTask(
                job_id=job.id,
                task_type="video_extract",
                site="youtube",
                priority="normal",
                payload={},
                dedupe_key="video_extract:https://example.com/watch?v=1",
            ),
        )

        with pytest.raises(IntegrityError):
            session.commit()


def test_crawl_task_declares_dispatch_indexes():
    index_names = {index.name for index in CrawlTask.__table__.indexes}

    assert "ix_crawl_task_runnable_lookup" in index_names
    assert "ix_crawl_task_lease_until" in index_names
    assert "ix_crawl_task_site_status" in index_names
