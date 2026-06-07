from __future__ import annotations

import hashlib
from typing import Optional


def fingerprint_head_sample(urls: Optional[list[str]]) -> Optional[str]:
    normalized = [str(url).strip() for url in (urls or []) if str(url).strip()]
    if not normalized:
        return None
    payload = '\n'.join(normalized[:20]).encode('utf-8')
    return hashlib.sha1(payload).hexdigest()


def calculate_head_overlap(previous_urls: Optional[list[str]], current_urls: Optional[list[str]]) -> Optional[float]:
    previous = {str(url).strip() for url in (previous_urls or []) if str(url).strip()}
    current = {str(url).strip() for url in (current_urls or []) if str(url).strip()}
    if not previous or not current:
        return None
    overlap = len(previous & current)
    return overlap / max(1, min(len(previous), len(current)))
