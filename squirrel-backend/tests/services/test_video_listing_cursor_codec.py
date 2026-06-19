"""Tests for video listing cursor codec (keyed namespace).

游标按排序/语义命名空间编码,decode 时校验 key:
- 新格式 `{key}:{ts}:{id}`(key ∈ p/c/h/i),encode/decode 往返一致
- 老格式 `{ts}:{id}`(2 段)decode → None(自然失效回首页)
- key 与预期不符 → None(切排序/串用游标时回首页)

设计动机:前端"抓取日期"排序(sort_by=created_at)与"上传日期"(publish_date)
共用同一个 cursor 字段,但排序键不同。游标内嵌 key 标识命名空间,
decode 时校验,避免老游标/串用游标导致 keyset 跳页/重复/漏行。
"""

import base64

from domains.video.application.services.search.meili_indexer import (
    _CURSOR_KEY_CREATED,
    _CURSOR_KEY_HISTORY,
    _CURSOR_KEY_INTERACTION,
    _CURSOR_KEY_PUBLISH,
    decode_cursor,
    decode_cursor_for_key,
    encode_cursor,
)


def test_encode_decode_roundtrip_preserves_key_and_values():
    """新格式 3 段往返:key/ts/id 全部还原。"""
    for key in (_CURSOR_KEY_PUBLISH, _CURSOR_KEY_CREATED, _CURSOR_KEY_HISTORY, _CURSOR_KEY_INTERACTION):
        token = encode_cursor(key, 1700000000, 42)
        assert decode_cursor(token) == (key, 1700000000, 42)


def test_decode_cursor_for_key_matches_returns_tuple():
    """key 匹配预期 → 返回 (ts, id)。"""
    token = encode_cursor(_CURSOR_KEY_CREATED, 1700000000, 42)
    assert decode_cursor_for_key(token, _CURSOR_KEY_CREATED) == (1700000000, 42)


def test_decode_cursor_for_key_mismatch_returns_none():
    """key 与预期不符(publish 游标用于 created 排序)→ None,调用方据此回首页。"""
    token = encode_cursor(_CURSOR_KEY_PUBLISH, 1700000000, 42)
    assert decode_cursor_for_key(token, _CURSOR_KEY_CREATED) is None


def test_decode_cursor_for_key_empty_cursor_returns_none():
    """None/空游标 → None。"""
    assert decode_cursor_for_key(None, _CURSOR_KEY_PUBLISH) is None
    assert decode_cursor_for_key('', _CURSOR_KEY_PUBLISH) is None


def test_decode_legacy_two_segment_cursor_returns_none():
    """老格式 `{ts}:{id}`(2 段)→ split 出 2 段而非 3 段 → None。

    老游标自然失效,等价回首页。这是无版本字段情况下的兼容策略:
    前端切排序会清游标,正常使用不受影响;URL 直连残留老游标时回首页兜底。
    """
    legacy_raw = f'{1700000000}:{42}'.encode()
    legacy_token = base64.urlsafe_b64encode(legacy_raw).decode('ascii').rstrip('=')
    assert decode_cursor(legacy_token) is None
    assert decode_cursor_for_key(legacy_token, _CURSOR_KEY_PUBLISH) is None


def test_decode_cursor_unknown_key_returns_none():
    """key 不在已知集合(如 'x')→ None。防注入/手造游标。"""
    raw = b'x:1700000000:42'
    token = base64.urlsafe_b64encode(raw).decode('ascii').rstrip('=')
    assert decode_cursor(token) is None


def test_decode_cursor_garbage_returns_none():
    """非法 base64 / 非数字段 → None,不抛异常。"""
    assert decode_cursor('!!!not-base64!!!') is None
    assert decode_cursor('not_a_token') is None


def test_decode_cursor_non_numeric_segments_returns_none():
    """3 段但 ts/id 非数字 → None。"""
    raw = b'p:abc:def'
    token = base64.urlsafe_b64encode(raw).decode('ascii').rstrip('=')
    assert decode_cursor(token) is None


def test_different_keys_produce_distinct_tokens():
    """不同 key 的游标 token 不同(命名空间隔离可见)。"""
    t_publish = encode_cursor(_CURSOR_KEY_PUBLISH, 1700000000, 42)
    t_created = encode_cursor(_CURSOR_KEY_CREATED, 1700000000, 42)
    assert t_publish != t_created
