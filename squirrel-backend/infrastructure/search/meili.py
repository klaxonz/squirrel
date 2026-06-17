"""Meilisearch 客户端与索引管理。"""
from __future__ import annotations

import logging

import meilisearch

from infrastructure.config.settings import settings

logger = logging.getLogger(__name__)

_client: meilisearch.Client | None = None

# videos 索引字段配置：
# - searchable：中文文本召回的字段（Meilisearch 内置中文分词）
# - filterable：结构化过滤下沉到 Meili 的字段
#   domain/subscription_names/creator_names 用于精确/数组 contains 匹配
#   duration/publish_ts 用于数值范围过滤（时长档位、时间范围）
# 权限/分类(阅读状态)/排序/分页一律回 PG（实时 join），不进 Meilisearch
_VIDEOS_SEARCHABLE_ATTRIBUTES = ['title', 'description', 'subscription_names', 'creator_names']
_VIDEOS_FILTERABLE_ATTRIBUTES = ['domain', 'duration', 'publish_ts', 'id', 'subscription_names', 'creator_names']
# 可排序字段：
#   publish_ts 用于纯浏览场景的 placeholder search 召回排序（最新优先）
#   id 作为 keyset 复合游标的次级排序键（保证 publish_ts 相同时的全序确定）
_VIDEOS_SORTABLE_ATTRIBUTES = ['publish_ts', 'id']


def get_meili_client() -> meilisearch.Client:
    """返回 Meilisearch 客户端单例。"""
    global _client
    if _client is None:
        meili_cfg = settings.meili
        if not meili_cfg.url:
            raise RuntimeError('MEILISEARCH_URL 未配置，无法初始化 Meilisearch 客户端')
        _client = meilisearch.Client(meili_cfg.url, meili_cfg.key or None)
    return _client


def ensure_videos_index() -> None:
    """创建 videos 索引并配置字段（幂等，应用启动或初始化脚本调用）。

    首次 add_documents 也会自动建索引，但显式 create_index 能确保主键为 id、
    并在写入前就把 searchable/filterable 配好。
    """
    client = get_meili_client()
    index_uid = settings.meili.index_videos
    # 显式建索引并指定主键；已存在时 Meilisearch 返回错误，这里忽略
    try:
        client.create_index(index_uid, {'primaryKey': 'id'})
    except Exception as exc:  # noqa: BLE001 — 索引已存在等非致命情况
        logger.debug('create_index %s skipped: %s', index_uid, exc)
    index = client.index(index_uid)
    index.update_searchable_attributes(_VIDEOS_SEARCHABLE_ATTRIBUTES)
    index.update_filterable_attributes(_VIDEOS_FILTERABLE_ATTRIBUTES)
    index.update_sortable_attributes(_VIDEOS_SORTABLE_ATTRIBUTES)
    logger.info('Meilisearch videos 索引就绪: %s', index_uid)
