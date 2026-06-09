---
title: Backend SQL ILIKE 通配符注入 — 7 处未转义用户输入
status: fixed
fixed_by: squirrel-backend
severity: medium
category: security
location: squirrel-backend/services/video_query.py:33; squirrel-backend/services/video_list_query_service.py:42; squirrel-backend/services/subscription_list_service.py:34; squirrel-backend/services/subscription_sync_center_service.py:585; squirrel-backend/services/video_extraction_center_service.py:220; squirrel-backend/services/subscription_sync_center_queries.py:108; squirrel-backend/services/scheduled_task_service.py:38-39
---

## 问题描述

7 处使用 `.ilike(f"%{term}%")` 模式，`term` 来自用户搜索输入，其中 `%` 和 `_` 是 SQL LIKE 通配符。用户输入 `%` 会匹配所有记录，输入 `_` 匹配任意单字符。`SearchQueryParser._normalize_term()` 仅做 `.strip().lower()` 而未转义这些字符。

## 影响

非预期搜索行为，可被用于信息探测（构造特定 LIKE 模式推断数据模式）。不属于数据泄露风险，但破坏搜索功能的预期语义。

## 建议方向

添加统一转义函数：
```python
def escape_ilike(term: str) -> str:
    return term.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
```
在所有 `.ilike()` 调用前应用 `escape_ilike()`。