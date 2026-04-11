from pathlib import Path
import re
import sys
import types
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'squirrel-backend'))
sys.path.insert(0, str(ROOT / 'squirrel-sdk' / 'src'))


class _AlembicConfig:
    def __init__(self, *_args, **_kwargs):
        self.attributes = {}

    def set_main_option(self, *_args, **_kwargs):
        return None


alembic_module = types.ModuleType('alembic')
alembic_module.command = SimpleNamespace(upgrade=lambda *_args, **_kwargs: None)
alembic_config_module = types.ModuleType('alembic.config')
alembic_config_module.Config = _AlembicConfig
bs4_module = types.ModuleType('bs4')
bs4_module.BeautifulSoup = object
sys.modules.setdefault('alembic', alembic_module)
sys.modules.setdefault('alembic.config', alembic_config_module)
sys.modules.setdefault('bs4', bs4_module)

import main as app_main


BASE_SOURCE = Path(__file__).resolve().parents[1] / 'routes' / 'base.py'


def test_main_uses_factory_mode_without_prebuilding_app_in_dev(monkeypatch):
    calls: list[str] = []
    uvicorn_calls: list[tuple[tuple, dict]] = []

    monkeypatch.setattr(app_main, 'upgrade_database', lambda: calls.append('upgrade_database'))
    monkeypatch.setattr(app_main, 'init_logging', lambda: calls.append('init_logging'))
    monkeypatch.setattr(app_main, 'create_application', lambda: calls.append('create_application') or object())
    monkeypatch.setattr(app_main.uvicorn, 'run', lambda *args, **kwargs: uvicorn_calls.append((args, kwargs)))
    monkeypatch.setattr(app_main, 'settings', SimpleNamespace(is_dev=True, PORT=8001))

    app_main.main()

    assert calls == ['upgrade_database', 'init_logging']
    assert uvicorn_calls == [
        (
            ('main:create_application',),
            {
                'host': '0.0.0.0',
                'port': 8001,
                'reload': False,
                'factory': True,
                'log_config': None,
                'access_log': False,
            },
        )
    ]


def test_main_prebuilds_app_once_in_prod(monkeypatch):
    calls: list[str] = []
    uvicorn_calls: list[tuple[tuple, dict]] = []
    app = object()

    monkeypatch.setattr(app_main, 'upgrade_database', lambda: calls.append('upgrade_database'))
    monkeypatch.setattr(app_main, 'init_logging', lambda: calls.append('init_logging'))
    monkeypatch.setattr(app_main, 'create_application', lambda: calls.append('create_application') or app)
    monkeypatch.setattr(app_main.uvicorn, 'run', lambda *args, **kwargs: uvicorn_calls.append((args, kwargs)))
    monkeypatch.setattr(app_main, 'settings', SimpleNamespace(is_dev=False, PORT=9000))

    app_main.main()

    assert calls == ['upgrade_database', 'init_logging', 'create_application']
    assert uvicorn_calls == [
        (
            (app,),
            {
                'host': '0.0.0.0',
                'port': 9000,
                'log_config': None,
                'access_log': False,
            },
        )
    ]


def test_routes_base_does_not_eagerly_create_app_on_import():
    source = BASE_SOURCE.read_text(encoding='utf-8')

    assert re.search(r'^\s*app\s*=\s*create_app\(\)\s*$', source, re.MULTILINE) is None
