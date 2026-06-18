from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class SubtitlesProvider(Protocol):
    """Protocol for subtitles providers."""

    domains: list[str]

    def get_subtitles(self, video: Any, lang: str, fmt: str = "srt") -> tuple[str, str]:
        """Get subtitles for the given video in the specified language and format.

        Returns:
            Tuple of (subtitle content, format)
        """
        ...

