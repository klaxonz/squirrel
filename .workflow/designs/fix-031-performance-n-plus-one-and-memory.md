## 根因

9 个独立性能问题，跨越 7 个后端文件。

## 修复思路

| # | 文件:行 | 问题 | 修复 |
|---|---------|------|------|
| 1 | `playlist_service.py:50-55` | 循环内独立 COUNT 查询 | GROUP BY 单次查询 |
| 2 | `scheduler.py:599-604` | 循环内 `_get_subscription_url` 独立 session | 批量预取 URL |
| 3 | `scheduler.py:771-783` | 循环内 `get_sync_state` 独立 session+query | WHERE IN 批量获取 |
| 4 | `video_extraction_center_service.py:364` | `_resolve_projection_sync_mode` 每项一次 DB 查询 | 批量加载 CrawlTask + dict 查找 |
| 5 | `video_extraction_center_service.py:65-80` | 双线性扫描 catalog | 构建 domain→slug 索引 |
| 6 | `log_service.py:63` | `all_lines` 存所有行 | 删除无用 `all_lines` |
| 7 | `video_extraction_projection_service.py:289-296` | 加载所有 CrawlTask 无 limit | 加 LIMIT + EXISTS 提前短路 |
| 8 | `core/site_config_manager.py:24-25,40-42` | `deepcopy` 整个嵌套 dict | `copy()` 代替 `deepcopy()` |
| 9 | `services/site_catalog_service.py:349` | `deepcopy` base dict | `copy()` 代替 `deepcopy()` |

## 涉及文件

- `squirrel-backend/services/playlist_service.py`
- `squirrel-backend/services/subscription_update/scheduler.py`
- `squirrel-backend/services/video_extraction_center_service.py`
- `squirrel-backend/services/log_service.py`
- `squirrel-backend/services/video_extraction_projection_service.py`
- `squirrel-backend/core/site_config_manager.py`
- `squirrel-backend/services/site_catalog_service.py`

## 潜在风险

- 无，均为纯性能优化，不改逻辑语义
