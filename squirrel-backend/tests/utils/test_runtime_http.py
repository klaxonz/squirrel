from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from utils import runtime_http


class DummyClient:
    pass


def test_get_cloudflare_bypass_client_defaults_to_none():
    runtime_http.reset_runtime_http_state()

    assert runtime_http.get_cloudflare_bypass_client() is None


def test_set_and_get_cloudflare_bypass_client():
    runtime_http.reset_runtime_http_state()
    client = DummyClient()

    runtime_http.set_cloudflare_bypass_client(client)

    assert runtime_http.get_cloudflare_bypass_client() is client
