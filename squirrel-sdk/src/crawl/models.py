from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Subscription:
    id: int
    url: str
    name: str
    avatar: str | None = None


@dataclass
class DownloadTask:
    id: int
    video_id: int
    status: str


class TaskState:
    DOWNLOADING = "downloading"
