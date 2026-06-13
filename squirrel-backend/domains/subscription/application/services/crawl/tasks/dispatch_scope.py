from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from domains.subscription.domain.models.crawl_dispatch_scope import CrawlDispatchScope


def ensure_dispatch_scope(session: Session, *, scope_type: str, scope_key: str) -> CrawlDispatchScope:
    scope = session.execute(
        select(CrawlDispatchScope).where(
            CrawlDispatchScope.scope_type == scope_type,
            CrawlDispatchScope.scope_key == scope_key,
        ),
    ).scalar_one_or_none()
    if scope:
        return scope

    with session.begin_nested():
        scope = CrawlDispatchScope(scope_type=scope_type, scope_key=scope_key)
        session.add(scope)
        try:
            session.flush()
            return scope
        except IntegrityError:
            pass

    return session.execute(
        select(CrawlDispatchScope).where(
            CrawlDispatchScope.scope_type == scope_type,
            CrawlDispatchScope.scope_key == scope_key,
        ),
    ).scalar_one()

