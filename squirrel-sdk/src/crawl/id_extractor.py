from __future__ import annotations

import re
from typing import List, Optional, Protocol, runtime_checkable


@runtime_checkable
class IdExtractor(Protocol):
    """Protocol for ID extractors.

    Extractors extract video/channel IDs from URLs.
    """

    domains: List[str]
    url: str

    def extract_id(self) -> str:
        """Extract the ID from the URL."""
        ...


class RegexIdExtractor:
    """Base class for regex-based ID extractors.

    Subclasses only need to define `domains` (or `domain`) and `pattern`:

        class PornhubIdExtractor(RegexIdExtractor):
            domains = ['pornhub.com']
            pattern = r"viewkey=([^&]+)"

    For more complex patterns, override `group_index` (default 1) or
    implement `extract_id()` directly.
    """

    domains: List[str] = []
    domain: Optional[str] = None
    pattern: Optional[str] = None
    group_index: int = 1

    def __init__(self, url: str):
        self.url = url

    def extract_id(self) -> str:
        if not self.pattern:
            raise NotImplementedError(
                f"{self.__class__.__name__} must define 'pattern' attribute"
            )
        match = re.search(self.pattern, self.url)
        if match:
            return match.group(self.group_index)
        raise ValueError(f"Cannot extract ID from URL: {self.url}")

