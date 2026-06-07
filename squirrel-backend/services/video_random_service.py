
from sqlalchemy import func

from core.database import get_session
from models.video import Video
from services import user_config_service
from services.video_query import build_base_video_query, category_predicate


def get_random_video(
        user_id: int,
        category: str | None = None,
        subscription_id: int | None = None,
        nsfw: str = 'all',
        domains: list[str] | None = None,
        query: str | None = None,
        time_range: str = 'all',
        duration: str = 'all',
        content_type: str = 'all',
) -> Video | None:
    user_config = user_config_service.get_config(user_id)
    show_nsfw = user_config.get('showNsfw', False)

    base = build_base_video_query(
        user_id, show_nsfw, subscription_id, query, nsfw, domains,
        time_range, duration, content_type,
    )
    base = base.where(category_predicate(user_id, category))

    with get_session() as session:
        bind = session.get_bind()
        dialect_name = getattr(getattr(bind, 'dialect', None), 'name', '') or ''

        if dialect_name in ('postgresql', 'sqlite'):
            order_random = func.random()
        elif dialect_name in ('mysql', 'mariadb'):
            order_random = func.rand()
        else:
            order_random = func.random()

        random_row = session.execute(
            base.order_by(order_random).limit(1)
        ).first()
        return random_row[0] if random_row else None
