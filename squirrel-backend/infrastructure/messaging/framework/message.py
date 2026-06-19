from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


@dataclass
class MqMessage:
    """Unified message wrapper

    Fields stored in Redis Streams:
    - key: "body" -> JSON string
    - key: "trace_id" -> trace_id string (for trace tracking)
    - Extensible: headers_xxx
    """

    body: dict[str, Any]
    trace_id: str | None = field(default=None)

    def to_stream_fields(self) -> dict[str, str]:
        fields = {'body': json.dumps(self.body, ensure_ascii=False)}
        if self.trace_id:
            fields['trace_id'] = self.trace_id
        return fields

    @classmethod
    def from_stream_fields(cls, fields: dict[bytes, bytes]) -> MqMessage:
        def _b2s(b: bytes) -> str:
            return b.decode('utf-8') if isinstance(b, (bytes, bytearray)) else str(b)

        mapped = {_b2s(k): _b2s(v) for k, v in fields.items()}
        body_raw = mapped.get('body', '{}')
        try:
            body = json.loads(body_raw)
        except (ValueError, TypeError):
            body = {'_raw': body_raw}

        trace_id = mapped.get('trace_id')
        return cls(body=body, trace_id=trace_id)
