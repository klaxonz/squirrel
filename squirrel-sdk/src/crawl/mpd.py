from __future__ import annotations

from typing import Any, List, Protocol, runtime_checkable


@runtime_checkable
class MpdBuilder(Protocol):
    """Protocol for MPD (Media Presentation Description) builders."""

    domains: List[str]

    def build_mpd(self, video: Any) -> str:
        """Build MPD content for the given video."""
        ...

