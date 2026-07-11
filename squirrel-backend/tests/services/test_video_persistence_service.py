from contextlib import contextmanager

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from domains.subscription.domain.models.subscription import Subscription
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
