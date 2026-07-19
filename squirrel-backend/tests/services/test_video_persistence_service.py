from contextlib import contextmanager
from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from domains.subscription.application.services.crawl.tasks.errors import CrawlTaskStateError
from domains.subscription.domain.models.crawl_job import CrawlJob
from domains.subscription.domain.models.crawl_task import CrawlTask
from domains.subscription.domain.models.subscription import Subscription
from domains.subscription.domain.models.subscription_sync_state import SubscriptionSyncState
from domains.video.application.services.extraction.video_persistence import VideoPersistenceService
from domains.video.domain.junctions.subscription_video import SubscriptionVideo
from domains.video.domain.junctions.video_creator import VideoCreator
from domains.video.domain.models.creator import Creator
from domains.video.domain.models.video import Video
from infrastructure.database.base import Base
from infrastructure.extraction.dto.actor_dto import ActorDTO


@pytest.fixture
def engine():
    test_engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(
        test_engine,
        tables=[
            Subscription.__table__,
            SubscriptionSyncState.__table__,
            CrawlJob.__table__,
            CrawlTask.__table__,
            Video.__table__,
            SubscriptionVideo.__table__,
            Creator.__table__,
            VideoCreator.__table__,
        ],
    )
    return test_engine


@pytest.fixture
def session_factory(engine):
    @contextmanager
    def _factory():
        session = Session(engine, expire_on_commit=False)
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    return _factory


def test_create_or_update_persists_video_subscription_and_creator_links(engine, session_factory):
    with Session(engine, expire_on_commit=False) as session:
        session.add(Subscription(id=1, type='CHANNEL', name='demo', url='https://www.youtube.com/channel/demo'))
        session.commit()

    service = VideoPersistenceService(session_factory=session_factory)

    video, is_new = service.create_or_update(
        url='https://www.youtube.com/watch?v=demo',
        title='Demo video',
        subscription_id=1,
        subscription_sync_mode='incremental',
        actors=[
            ActorDTO(
                url='https://www.youtube.com/@creator',
                name='Creator',
                avatar='https://example.com/avatar.jpg',
            ),
        ],
    )

    assert is_new is True

    with Session(engine, expire_on_commit=False) as session:
        assert session.get(Video, video.id).title == 'Demo video'
        assert session.get(SubscriptionVideo, {'subscription_id': 1, 'video_id': video.id}) is not None
        creator = session.scalars(select(Creator).where(Creator.url == 'https://www.youtube.com/@creator')).one()
        assert creator.name == 'Creator'
        assert session.get(VideoCreator, {'video_id': video.id, 'creator_id': creator.id}) is not None


def test_create_or_update_rolls_back_video_and_subscription_link_when_actor_link_fails(
    engine,
    session_factory,
):
    with Session(engine, expire_on_commit=False) as session:
        session.add(Subscription(id=1, type='CHANNEL', name='demo', url='https://www.youtube.com/channel/demo'))
        session.commit()

    class FailingVideoPersistenceService(VideoPersistenceService):
        def process_actors_in_session(self, session, video_id, actors):
            raise ValueError('actor_link_failed')

    service = FailingVideoPersistenceService(session_factory=session_factory)

    with pytest.raises(ValueError, match='actor_link_failed'):
        service.create_or_update(
            url='https://www.youtube.com/watch?v=demo',
            title='Demo video',
            subscription_id=1,
            subscription_sync_mode='incremental',
            actors=[ActorDTO(url='https://www.youtube.com/@creator', name='Creator')],
        )

    with Session(engine, expire_on_commit=False) as session:
        assert session.scalars(select(Video)).all() == []
        assert session.scalars(select(SubscriptionVideo)).all() == []
        assert session.scalars(select(Creator)).all() == []
        assert session.scalars(select(VideoCreator)).all() == []


def test_link_existing_video_adds_missing_subscription_association(engine, session_factory):
    with Session(engine, expire_on_commit=False) as session:
        session.add_all(
            [
                Subscription(id=1, type='CHANNEL', name='first', url='https://example.com/first'),
                Subscription(id=2, type='CHANNEL', name='second', url='https://example.com/second'),
            ],
        )
        video = Video(url='https://example.com/video', domain='example.com', title='shared')
        session.add(video)
        session.flush()
        session.add(SubscriptionVideo(subscription_id=1, video_id=video.id))
        session.commit()
        video_id = video.id

    service = VideoPersistenceService(session_factory=session_factory)
    assert service.link_existing_videos(2, [video_id, video_id]) == 1
    assert service.link_existing_videos(2, [video_id]) == 0

    with Session(engine, expire_on_commit=False) as session:
        links = session.scalars(
            select(SubscriptionVideo).where(SubscriptionVideo.video_id == video_id),
        ).all()
    assert {link.subscription_id for link in links} == {1, 2}


def test_link_existing_video_rejects_stale_parent_execution(engine, session_factory):
    with Session(engine, expire_on_commit=False) as session:
        session.add(Subscription(id=1, type='CHANNEL', name='demo', url='https://example.com/demo'))
        session.add(
            SubscriptionSyncState(
                id=10,
                subscription_id=1,
                site='example.com',
                sync_mode='incremental',
                sync_status='running',
                current_run_id='run-10',
                execution_token='direct:run-10',
            ),
        )
        video = Video(url='https://example.com/existing', domain='example.com', title='existing')
        session.add(video)
        session.commit()
        video_id = video.id

    service = VideoPersistenceService(session_factory=session_factory)
    with pytest.raises(CrawlTaskStateError, match='Stale video persistence execution'):
        service.link_existing_videos(
            1,
            [video_id],
            sync_state_id=10,
            run_id='run-10',
            execution_token='direct:stale-run',
        )

    with Session(engine, expire_on_commit=False) as session:
        assert session.get(SubscriptionVideo, {'subscription_id': 1, 'video_id': video_id}) is None


def test_video_persistence_requires_live_child_task_lease(engine, session_factory):
    now = datetime.now()
    with Session(engine, expire_on_commit=False) as session:
        session.add(Subscription(id=1, type='CHANNEL', name='demo', url='https://example.com/demo'))
        session.add(
            SubscriptionSyncState(
                id=11,
                subscription_id=1,
                site='example.com',
                sync_mode='incremental',
                sync_status='running',
                current_run_id='run-11',
            ),
        )
        job = CrawlJob(job_type='video_extract', source_type='scheduled', site='example.com')
        session.add(job)
        session.flush()
        task = CrawlTask(
            job_id=job.id,
            task_type='video_extract',
            site='example.com',
            subscription_id=1,
            sync_state_id=11,
            run_id='run-11',
            status='running',
            worker_id='video-worker',
            lease_token='child-token',
            lease_until=now + timedelta(minutes=1),
        )
        session.add(task)
        session.commit()
        task_id = task.id

    service = VideoPersistenceService(session_factory=session_factory)
    video, created = service.create_or_update(
        url='https://example.com/live-child',
        title='live child',
        subscription_id=1,
        sync_state_id=11,
        run_id='run-11',
        execution_token='child-token',
        crawl_task_id=task_id,
    )
    assert created is True

    with Session(engine, expire_on_commit=False) as session:
        task = session.get(CrawlTask, task_id)
        task.lease_token = 'replacement-token'
        session.commit()

    with pytest.raises(CrawlTaskStateError, match='Stale video persistence execution'):
        service.create_or_update(
            url='https://example.com/stale-child',
            title='stale child',
            subscription_id=1,
            sync_state_id=11,
            run_id='run-11',
            execution_token='child-token',
            crawl_task_id=task_id,
        )

    with Session(engine, expire_on_commit=False) as session:
        assert session.get(Video, video.id) is not None
        assert session.scalars(select(Video).where(Video.url == 'https://example.com/stale-child')).first() is None
