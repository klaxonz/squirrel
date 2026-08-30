import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def test_main_initializes_logging_before_database_upgrade(monkeypatch: pytest.MonkeyPatch):
    import main

    events: list[str] = []
    monkeypatch.setattr(main, 'init_logging', lambda: events.append('logging'))
    monkeypatch.setattr(main, 'upgrade_database', lambda: events.append('migration'))
    monkeypatch.setattr(main, 'uvicorn', SimpleNamespace(run=lambda *args, **kwargs: events.append('server')))

    application = ModuleType('application.app')
    application.create_app = lambda: events.append('app') or object()
    monkeypatch.setitem(sys.modules, 'application.app', application)

    main.main()

    assert events == ['logging', 'migration', 'app', 'server']
