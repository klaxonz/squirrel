"""Helpers for rewriting proxied playlist content."""
from __future__ import annotations

import re
from typing import Iterable, Sequence
from urllib.parse import urlencode, urljoin


DEFAULT_PLAYLIST_EXTENSIONS: Sequence[str] = ('ts', 'm4s', 'mp4', 'jpeg', 'jpg', 'm3u8', 'vtt')


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
    extension_pattern = '|'.join(re.escape(ext.lstrip('.')) for ext in extensions)
    uri_pattern = re.compile(rf'URI="([^"]+\.(?:{extension_pattern})[^"]*)"')
    line_pattern = re.compile(rf'.+\.(?:{extension_pattern})[^\s]*')

    def build_proxy_url(path: str) -> str:
        full_url = path if path.startswith('http') else urljoin(base_url + '/', path)
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
            return line.replace(uri_match.group(1), build_proxy_url(uri_match.group(1).strip()), 1)

        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            return line
        if line_pattern.fullmatch(stripped):
            return build_proxy_url(stripped)
        return line

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
