import re
from pathlib import Path

MAIN_SOURCE = Path(__file__).resolve().parents[1] / "main.py"


def test_main_disables_uvicorn_default_log_config_in_dev():
    source = MAIN_SOURCE.read_text(encoding="utf-8")

    assert re.search(
        r'uvicorn\.run\(\s*"main:create_application",[\s\S]*?factory=True,[\s\S]*?log_config=None,[\s\S]*?access_log=False',
        source,
    )


def test_main_disables_uvicorn_default_log_config_in_prod():
    source = MAIN_SOURCE.read_text(encoding="utf-8")

    assert re.search(
        r'uvicorn\.run\(app,\s*host="0\.0\.0\.0",\s*port=settings\.PORT,\s*log_config=None,\s*access_log=False\)',
        source,
    )
