import re
from pathlib import Path

MAIN_SOURCE = Path(__file__).resolve().parents[1] / "main.py"


def test_main_disables_uvicorn_default_log_config():
    source = MAIN_SOURCE.read_text(encoding="utf-8")

    assert re.search(
        r'uvicorn\.run\(\s*create_application\(\),[\s\S]*?log_config=None,[\s\S]*?access_log=False',
        source,
    )
