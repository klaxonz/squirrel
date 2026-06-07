from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


def _load_ytdlp_support():
    try:
        from . import ytdlp_support

        return ytdlp_support
    except ImportError:  # pragma: no cover - direct script execution path
        helper_path = Path(__file__).with_name("ytdlp_support.py")
        module_spec = importlib.util.spec_from_file_location("_youtube_playback_worker_ytdlp_support", helper_path)
        module = importlib.util.module_from_spec(module_spec)
        assert module_spec is not None and module_spec.loader is not None
        sys.modules["_youtube_playback_worker_ytdlp_support"] = module
        module_spec.loader.exec_module(module)
        return module


youtube_ytdlp_support = _load_ytdlp_support()


def _read_payload() -> dict[str, Any]:
    raw_payload = sys.stdin.read()
    if not raw_payload:
        raise ValueError("Missing worker payload")
    payload = json.loads(raw_payload)
    if not isinstance(payload, dict):
        raise ValueError("Worker payload must be a JSON object")
    return payload


def _write_payload(payload: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(payload))
    sys.stdout.flush()


def main() -> int:
    try:
        payload = _read_payload()
        info = youtube_ytdlp_support.extract_info_with_player_responses(
            str(payload["url"]),
            dict(payload.get("opts") or {}),
            process=bool(payload.get("process", True)),
        )
        safe_info = youtube_ytdlp_support._sanitize_json_value(info)
        _write_payload({"info": None if safe_info is youtube_ytdlp_support._SKIP_VALUE else safe_info})
        return 0
    except Exception as exc:  # process boundary — subprocess entry point, serialize any error
        _write_payload({
            "error": {
                "type": type(exc).__name__,
                "message": str(exc),
            }
        })
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
