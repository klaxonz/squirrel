from __future__ import annotations

import re
import shlex
from dataclasses import dataclass, field
from urllib.parse import urlparse

FIELD_ALIASES = {
    'title': 'title',
    '标题': 'title',
    'name': 'subscription',
    'channel': 'subscription',
    'subscription': 'subscription',
    '频道': 'subscription',
    'creator': 'creator',
    'actor': 'creator',
    '演员': 'creator',
    'site': 'domain',
    'domain': 'domain',
    '站点': 'domain',
    'desc': 'description',
    'description': 'description',
    '简介': 'description',
    'url': 'url',
    'link': 'url',
    '链接': 'url',
    'type': 'type',
    '类型': 'type',
}

FIELD_TOKEN_PATTERN = re.compile(r'^(?P<key>[^::\s]+)\s*[::]\s*(?P<value>.+)$')


@dataclass
class ParsedSearchQuery:
    text_terms: list[str] = field(default_factory=list)
    title: list[str] = field(default_factory=list)
    subscription: list[str] = field(default_factory=list)
    creator: list[str] = field(default_factory=list)
    domain: list[str] = field(default_factory=list)
    description: list[str] = field(default_factory=list)
    url: list[str] = field(default_factory=list)
    type: list[str] = field(default_factory=list)

    @property
    def has_terms(self) -> bool:
        return any(
            [
                self.text_terms,
                self.title,
                self.subscription,
                self.creator,
                self.domain,
                self.description,
                self.url,
                self.type,
            ]
        )

    def get(self, field: str) -> list[str]:
        return list(getattr(self, field, []) or [])


SUBSCRIPTION_TYPE_ALIASES = {
    'channel': 'CHANNEL',
    '频道': 'CHANNEL',
    'playlist': 'PLAYLIST',
    '播放列表': 'PLAYLIST',
    'actress': 'ACTRESS',
    '女优': 'ACTRESS',
    'movie': 'MOVIE',
    '电影': 'MOVIE',
    'tv_series': 'TV_SERIES',
    'tv-series': 'TV_SERIES',
    'series': 'TV_SERIES',
    '剧集': 'TV_SERIES',
    'actor': 'ACTOR',
    '演员': 'ACTOR',
}


def escape_ilike(term: str) -> str:
    return term.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')


def _normalize_term(value: str | None) -> str:
    return ' '.join(str(value or '').strip().lower().split())


def parse_search_query(query: str | None) -> ParsedSearchQuery:
    parsed = ParsedSearchQuery()
    raw_query = str(query or '').strip()
    if not raw_query:
        return parsed

    try:
        tokens = shlex.split(raw_query)
    except ValueError:
        tokens = raw_query.split()

    for raw_token in tokens:
        token = str(raw_token or '').strip()
        if not token:
            continue

        matched = FIELD_TOKEN_PATTERN.match(token)
        normalized_value = None
        if matched:
            key = _normalize_term(matched.group('key'))
            normalized_value = _normalize_term(matched.group('value'))
            target_field = FIELD_ALIASES.get(key)
            if target_field and normalized_value:
                getattr(parsed, target_field).append(normalized_value)
                continue

        normalized_token = normalized_value or _normalize_term(token)
        if normalized_token:
            parsed.text_terms.append(normalized_token)

    return parsed


def extract_search_domain(url: str | None) -> str:
    raw_url = str(url or '').strip()
    if not raw_url:
        return ''
    parsed = urlparse(raw_url if '://' in raw_url else f'https://{raw_url}')
    host = (parsed.netloc or parsed.path or '').strip().lower()
    host = host.removeprefix('www.')
    return host.split(':')[0]


def normalize_subscription_type_term(value: str | None) -> str | None:
    normalized_value = _normalize_term(value or '')
    if not normalized_value:
        return None
    return SUBSCRIPTION_TYPE_ALIASES.get(normalized_value, normalized_value.upper())
