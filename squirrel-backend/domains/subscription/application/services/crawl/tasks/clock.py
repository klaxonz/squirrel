from datetime import datetime

from sqlalchemy import DateTime, func, select
from sqlalchemy.orm import Session


def database_local_now_expression(session: Session):
    if session.get_bind().dialect.name == 'sqlite':
        return func.datetime('now', 'localtime', type_=DateTime())
    return func.localtimestamp(type_=DateTime())


def database_local_now(session: Session) -> datetime:
    return session.execute(select(database_local_now_expression(session))).scalar_one()
