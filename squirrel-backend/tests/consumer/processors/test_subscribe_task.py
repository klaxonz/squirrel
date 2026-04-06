import json
from types import SimpleNamespace
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from consumer.processors import subscribe_task


def test_process_subscribe_message_propagates_handler_failure(monkeypatch):
    message = {'body': json.dumps({'url': 'https://www.youporn.com/amateur/ghomestory/', 'user_id': 1})}

    monkeypatch.setattr(subscribe_task.Message, 'from_dict', classmethod(lambda cls, raw: SimpleNamespace(body=raw['body'])))
    monkeypatch.setattr(subscribe_task.SiteCatalog, 'is_site_enabled', classmethod(lambda cls, domain=None: True))
    monkeypatch.setattr(subscribe_task, 'extract_top_level_domain', lambda _url: 'youporn.com')

    def _raise(*_args, **_kwargs):
        raise ValueError('plugin not ready')

    monkeypatch.setattr(subscribe_task.subscription_service, 'handle_subscribe_request', _raise)

    with pytest.raises(ValueError, match='plugin not ready'):
        subscribe_task.process_subscribe_message(message)


def test_process_subscribe_message_skips_invalid_payload_without_raising(monkeypatch):
    message = {'body': json.dumps({'user_id': 1})}

    monkeypatch.setattr(subscribe_task.Message, 'from_dict', classmethod(lambda cls, raw: SimpleNamespace(body=raw['body'])))

    subscribe_task.process_subscribe_message(message)
