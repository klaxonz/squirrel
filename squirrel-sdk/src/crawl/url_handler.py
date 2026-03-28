from __future__ import annotations

from typing import Any, Dict, List, Protocol, runtime_checkable


@runtime_checkable
class VideoUrlHandler(Protocol):
    """Protocol for video URL handlers.

    Handlers convert video objects into serializable dictionaries for VideoUrlDto construction.
    """

    domains: List[str]

    def get_video_url(self, video: Any) -> Dict[str, Any]:
        """Return a serializable dict for VideoUrlDto construction by backend."""
        ...

