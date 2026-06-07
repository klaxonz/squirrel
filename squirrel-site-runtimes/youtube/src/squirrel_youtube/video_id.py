from __future__ import annotations

from urllib.parse import parse_qs, urlparse


def extract_youtube_video_id(url: str) -> str | None:
    if not url:
        return None

    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    path = parsed.path.strip("/")

    if host.endswith("youtu.be"):
        return path or None

    query_video_id = parse_qs(parsed.query).get("v")
    if query_video_id and query_video_id[0]:
        return query_video_id[0]

    path_parts = [part for part in path.split("/") if part]
    if len(path_parts) >= 2 and path_parts[0] in {"shorts", "embed", "live"}:
        return path_parts[1]

    return None
