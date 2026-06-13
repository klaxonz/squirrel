import html as html_lib
import json
import re

LDJSON_THUMBNAIL_RE = re.compile(
    r'<script\s+type=["\']application/ld\+json["\']>(.*?)</script>',
    re.IGNORECASE | re.DOTALL,
)
META_THUMBNAIL_PATTERNS = (
    re.compile(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', re.IGNORECASE),
    re.compile(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']', re.IGNORECASE),
    re.compile(r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']', re.IGNORECASE),
    re.compile(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']twitter:image["\']', re.IGNORECASE),
)


def looks_like_expiring_preview_thumbnail(url: str | None) -> bool:
    normalized = str(url or '').strip().lower()
    if not normalized:
        return False
    if 'phncdn.com/videos/' in normalized:
        return True
    return '/plain/' in normalized and ('validto=' in normalized or 'hdnea=' in normalized)


def thumbnail_expiry_score(url: str) -> float:
    normalized = str(url or '').strip().lower()
    if not normalized:
        return -1
    if not any(token in normalized for token in ('validto=', 'hdnea=', 'hmac=', 'hash=')):
        return float('inf')

    validto_match = re.search(r'[?&]validto=(\d+)', normalized)
    if validto_match:
        return float(validto_match.group(1))

    hdnea_exp_match = re.search(r'(?:^|[~&])exp=(\d+)', normalized)
    if hdnea_exp_match:
        return float(hdnea_exp_match.group(1))

    return 0


def pick_best_thumbnail_url(thumbnail_urls: list[str]) -> str | None:
    unique_urls = []
    for thumbnail_url in thumbnail_urls:
        normalized = html_lib.unescape(str(thumbnail_url or '').strip())
        if normalized and normalized not in unique_urls:
            unique_urls.append(normalized)

    if not unique_urls:
        return None

    return max(unique_urls, key=thumbnail_expiry_score)


def extract_thumbnail_url_from_html(html_text: str) -> str | None:
    thumbnail_urls: list[str] = []
    for match in LDJSON_THUMBNAIL_RE.finditer(str(html_text or '')):
        try:
            payload = json.loads(match.group(1).strip())
        except (json.JSONDecodeError, TypeError):
            continue

        pending = payload if isinstance(payload, list) else [payload]
        while pending:
            item = pending.pop(0)
            if isinstance(item, list):
                pending.extend(item)
                continue
            if not isinstance(item, dict):
                continue

            graph = item.get('@graph')
            if isinstance(graph, list):
                pending.extend(graph)
            elif isinstance(graph, dict):
                pending.append(graph)

            for key in ('thumbnailUrl', 'thumbnail', 'contentUrl'):
                value = item.get(key)
                if isinstance(value, str) and value.strip():
                    thumbnail_urls.append(value.strip())
                if isinstance(value, list):
                    for candidate in value:
                        if isinstance(candidate, str) and candidate.strip():
                            thumbnail_urls.append(candidate.strip())

    for pattern in META_THUMBNAIL_PATTERNS:
        for match in pattern.finditer(str(html_text or '')):
            thumbnail_url = html_lib.unescape(match.group(1).strip())
            if thumbnail_url:
                thumbnail_urls.append(thumbnail_url)

    return pick_best_thumbnail_url(thumbnail_urls)

