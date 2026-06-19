import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'squirrel-site-runtimes' / 'shared'))

from infrastructure.extraction.adapters.runtime_adapter import RuntimeDataAdapter
from infrastructure.extraction.dto.validators import parse_publish_date
from infrastructure.extraction.runtime_payloads import RuntimeVideoData


def test_parse_publish_date_accepts_iso_datetime_string():
    parsed = parse_publish_date('2026-03-29T15:39:03')

    assert parsed == datetime(2026, 3, 29, 15, 39, 3)


def test_plugin_data_adapter_adapts_iso_publish_date_string():
    adapter = RuntimeDataAdapter()
    video = RuntimeVideoData(
        title='Bilibili runtime video',
        url='https://www.bilibili.com/video/BV1kXXSByESg',
        publish_date='2026-03-29T15:39:03',
    )

    dto = adapter.adapt(video, site_name='bilibili')

    assert dto.publish_date == datetime(2026, 3, 29, 15, 39, 3)
