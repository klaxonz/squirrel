from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class MqMessage:
    """统一的消息封装

    存储于 Redis Streams 的字段为:
    - key: "body" -> JSON 字符串
    - 可扩展：headers_xxx
    """

    body: Dict[str, Any]

    def to_stream_fields(self) -> Dict[str, str]:
        return {"body": json.dumps(self.body, ensure_ascii=False)}

    @classmethod
    def from_stream_fields(cls, fields: Dict[bytes, bytes]) -> "MqMessage":
        def _b2s(b: bytes) -> str:
            return b.decode("utf-8") if isinstance(b, (bytes, bytearray)) else str(b)

        mapped = { _b2s(k): _b2s(v) for k, v in fields.items() }
        body_raw = mapped.get("body", "{}")
        try:
            body = json.loads(body_raw)
        except Exception:
            body = {"_raw": body_raw}
        return cls(body=body)


