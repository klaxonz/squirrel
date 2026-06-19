"""跨域共享的搜索语义契约(Shared Kernel)。

产品级搜索语法解析,被 user / subscription / video 等多个限界上下文复用。
本模块定义统一的 `field:value` 查询语法、字段别名表(含中文别名)与
订阅类型归一化规则;变更需各消费方协商。

注意:这是领域语义,不是基础设施。SQL 转义工具(escape_ilike)在
infrastructure/database/query.py,Meilisearch 适配在 infrastructure/search/。
"""

from __future__ import annotations

import re
import shlex
from dataclasses import dataclass, field

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


def normalize_subscription_type_term(value: str | None) -> str | None:
    normalized_value = _normalize_term(value or '')
    if not normalized_value:
        return None
    return SUBSCRIPTION_TYPE_ALIASES.get(normalized_value, normalized_value.upper())
