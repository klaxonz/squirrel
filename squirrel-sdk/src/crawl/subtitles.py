from __future__ import annotations

from typing import Any, List, Protocol, runtime_checkable, Tuple


@runtime_checkable
class SubtitlesProvider(Protocol):
    """Protocol for subtitles providers."""

    domains: List[str]

    def get_subtitles(self, video: Any, lang: str, fmt: str = "srt") -> Tuple[str, str]:
        """Get subtitles for the given video in the specified language and format.

        Returns:
            Tuple of (subtitle content, format)
        """
        ...

