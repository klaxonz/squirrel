import importlib
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[3]

for plugin_name in ('bilibili', 'javdb', 'pornhub', 'youtube'):
    sys.path.insert(0, str(ROOT / 'squirrel-plugins' / plugin_name / 'src'))


@pytest.mark.parametrize(
    ('module_name', 'plugin_name', 'plugin_description'),
    [
        ('squirrel_bilibili', 'bilibili', 'Bilibili crawl integration'),
        ('squirrel_javdb', 'javdb', 'JavDB crawl integration'),
        ('squirrel_pornhub', 'pornhub', 'Pornhub crawl integration'),
        ('squirrel_youtube', 'youtube', 'YouTube crawl integration'),
    ],
)
def test_workspace_plugin_imports_are_runtime_only(module_name, plugin_name, plugin_description):
    module = importlib.import_module(module_name)

    assert module.PLUGIN_NAME == plugin_name
    assert module.PLUGIN_VERSION == '0.1.0'
    assert module.PLUGIN_DESCRIPTION == plugin_description
    assert callable(module.get_plugin_runtime)
    assert set(module.__all__) == {
        'PLUGIN_NAME',
        'PLUGIN_VERSION',
        'PLUGIN_DESCRIPTION',
        'get_plugin_runtime',
    }
