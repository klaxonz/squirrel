# SQL ILIKE 通配符注入修复

## 根因

7 处 `.ilike(f"%{term}%")` 调用未转义 SQL LIKE 通配符 `%` 和 `_`，用户输入含有这些字符时会匹配非预期记录。

## 修复思路

1. 在 `search_query.py` 添加 `escape_ilike()` 函数（转义 `\`、`%`、`_`）
2. 在 7 处 `.ilike()` 调用前应用 `escape_ilike()`

## 涉及文件

| 文件 | 行号 |
|------|------|
| `services/search_query.py` | 新增 `escape_ilike` |
| `services/video_query.py` | 33 |
| `services/video_list_query_service.py` | 42 |
| `services/subscription_list_service.py` | 34 |
| `services/subscription_sync_center_service.py` | 585 |
| `services/video_extraction_center_service.py` | 220 |
| `services/subscription_sync_center_queries.py` | 108 |
| `services/scheduled_task_service.py` | 38-39 |

## 潜在风险

- 不影响数据库查询计划（`ilike` 本身不走索引）
- 向后兼容，行为安全（用户输入中的 `%`/`_` 不再具有通配语义，更符合预期）
