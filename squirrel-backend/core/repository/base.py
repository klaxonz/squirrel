from typing import Generic, TypeVar, Type, Optional, List, Any

from sqlalchemy import select, delete as sa_delete
from sqlalchemy.orm import Session

from core.database import get_session

T = TypeVar("T")


class BaseRepository(Generic[T]):
    model: Type[T]

    def __init__(self, session: Optional[Session] = None):
        self._external_session = session

    def _get_session(self):
        if self._external_session:
            return self._external_session
        return get_session()

    def get_by_id(self, id: int) -> Optional[T]:
        with self._get_session() as session:
            return session.get(self.model, id)

    def get_by_ids(self, ids: List[int]) -> List[T]:
        if not ids:
            return []
        with self._get_session() as session:
            return list(session.scalars(
                select(self.model).where(self.model.id.in_(ids))
            ).all())

    def get_all(self) -> List[T]:
        with self._get_session() as session:
            return list(session.scalars(select(self.model)).all())

    def create(self, entity: T) -> T:
        with self._get_session() as session:
            session.add(entity)
            session.commit()
            session.refresh(entity)
            return entity

    def update(self, entity: T) -> T:
        with self._get_session() as session:
            merged = session.merge(entity)
            session.commit()
            session.refresh(merged)
            return merged

    def delete(self, id: int) -> bool:
        with self._get_session() as session:
            result = session.execute(
                sa_delete(self.model).where(self.model.id == id)
            )
            session.commit()
            return result.rowcount > 0

    def delete_by_ids(self, ids: List[int]) -> int:
        if not ids:
            return 0
        with self._get_session() as session:
            result = session.execute(
                sa_delete(self.model).where(self.model.id.in_(ids))
            )
            session.commit()
            return result.rowcount

    def exists(self, id: int) -> bool:
        with self._get_session() as session:
            return session.get(self.model, id) is not None
