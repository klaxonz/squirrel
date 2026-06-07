---
title: 性能 — 多处 N+1 查询 + 无界内存读取 + 冗余 deepcopy
status: open
severity: high
category: performance
location: squirrel-backend/services/（跨多文件）
---

## 问题描述

### N+1 查询模式（5 处）

1. **`playlist_service.py:50-55`** — 循环内对每个播放列表执行独立 `COUNT` 查询，未使用 `GROUP BY`
2. **`subscription_update/scheduler.py:599-604`** — 循环内为每个 subscription_id 调用 `schedule_one` + `_get_subscription_url`（后者开独立 session），可预取批量数据
3. **`subscription_update/scheduler.py:771-783`** — 循环内每行调用 `get_sync_state` 开独立 session+query，应单次 WHERE IN 批量获取
4. **`video_extraction_center_service.py:364`** — `_build_item` 内 `_resolve_projection_sync_mode` 每项一次 DB 查询，50 页即 50+ 查询
5. **`video_extraction_center_service.py:65-80`** — `_resolve_site_icon_url` 双线性扫描 catalog，应建 domain→slug 缓存索引

### 无界内存读取（2 处）

6. **`log_service.py:63`** — `read_log_lines` 读取日志文件全部行到 `all_lines` 列表，即使只返回过滤后的子集。大日志文件（数百 MB）造成内存 OOM
7. **`video_extraction_projection_service.py:289-296`** — `_projection_requires_group_key_rebuild` 加载 `所有` CrawlTask 无 limit/pagination，数百万任务时 OOM

### 冗余 deepcopy（2 处）

8. **`core/site_config_manager.py:24-25,40-42`** — `get_effective_site_catalog` 每次调用 deepcopy 整个站点目录（嵌套 dict），应缓存或就地修改
9. **`services/site_catalog_service.py:349`** — 同模式 deepcopy base dict 每次 merge

## 影响

- 播放列表/订阅较多的用户触发数百次额外查询
- 日志查看功能可能 OOM 进程
- deepcopy 每次配置变更时浪费 CPU+内存

## 建议方向

1. 所有 N+1 模式改为批量查询（`WHERE IN` / `GROUP BY` / 子查询）
2. `log_service.py` 改为流式读取（只保留匹配行）
3. 爬取任务查询添加分页
4. `deepcopy` 改为 `copy`（浅拷贝）或缓存 + 引用计数
