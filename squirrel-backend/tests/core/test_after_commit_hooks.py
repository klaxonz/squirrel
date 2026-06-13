import sys
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from infrastructure.database.session import register_after_commit


def test_register_after_commit_runs_callback_only_after_commit():
    engine = create_engine("sqlite:///:memory:")
    session = Session(engine, expire_on_commit=False)
    calls = []

    register_after_commit(session, lambda: calls.append("committed"))

    assert calls == []

    session.commit()

    assert calls == ["committed"]
    session.close()
