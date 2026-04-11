"""Helpers for rewriting proxied playlist content."""
from __future__ import annotations

import re
from typing import Iterable, Sequence
from urllib.parse import urlencode, urljoin


DEFAULT_PLAYLIST_EXTENSIONS: Sequence[str] = ('ts', 'm4s', 'mp4', 'jpeg', 'jpg', 'm3u8', 'vtt')
_ABSOLUTE_URL_RE = re.compile(r'^[a-z][a-z0-9+.-]*://', re.IGNORECASE)
_SCHEME_LIKE_PREFIX_RE = re.compile(r'^[a-z][a-z0-9+.-]*:', re.IGNORECASE)


def rewrite_playlist_for_proxy(
    url: str,
    content: str | bytes,
    *,
    site_domain: str,
    referer: str | None = None,
    extensions: Iterable[str] = DEFAULT_PLAYLIST_EXTENSIONS,
) -> dict[str, object]:
    content_text = content.decode(errors='ignore') if isinstance(content, (bytes, bytearray)) else str(content)
    base_url = url.rsplit('/', 1)[0]
    uri_pattern = re.compile(r'URI="([^"]+)"')

    def should_proxy_target(path: str) -> bool:
        if not path:
            return False
        if path.startswith('/api/video/proxy?'):
            return False
        if path.startswith(('data:', 'blob:')):
            return False
        return True

    def build_proxy_url(path: str) -> str:
        normalized_path = path.strip()
        if not should_proxy_target(normalized_path):
            return normalized_path

        if _ABSOLUTE_URL_RE.match(normalized_path):
            full_url = normalized_path
        else:
            join_target = normalized_path
            if _SCHEME_LIKE_PREFIX_RE.match(normalized_path) and not normalized_path.startswith('/'):
                # Some HLS providers emit colon-delimited relative segment ids such as
                # "vts:504?...". Treat them as relative playlist entries instead of URLs
                # with a custom scheme so they resolve against the upstream playlist path.
                join_target = f'./{normalized_path}'
            full_url = urljoin(base_url + '/', join_target)

        query = {
            'domain': site_domain,
            'url': full_url,
        }
        if referer:
            query['referer'] = referer
        return f'/api/video/proxy?{urlencode(query)}'

    def rewrite_line(line: str) -> str:
        uri_match = uri_pattern.search(line)
        if uri_match:
            original_uri = uri_match.group(1).strip()
            rewritten_uri = build_proxy_url(original_uri)
            if rewritten_uri != original_uri:
                return line.replace(original_uri, rewritten_uri, 1)
            return line

        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            return line
        rewritten_line = build_proxy_url(stripped)
        return rewritten_line if rewritten_line != stripped else line

    rewritten = '\n'.join(rewrite_line(line) for line in content_text.splitlines())
    if content_text.endswith('\n'):
        rewritten += '\n'

    return {
        'content': rewritten,
        'media_type': 'application/vnd.apple.mpegurl',
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Cache-Control': 'no-cache',
        },
    }


def rewrite_proxy_playlist_content(
    url: str,
    content: str | bytes,
    *,
    site_domain: str,
    referer: str | None = None,
    extensions: Iterable[str] = DEFAULT_PLAYLIST_EXTENSIONS,
) -> dict[str, object]:
    return rewrite_playlist_for_proxy(
        url=url,
        content=content,
        site_domain=site_domain,
        referer=referer,
        extensions=extensions,
    )
