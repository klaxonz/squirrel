---
title: Backend 上帝模块 v2 — scheduler(917行) / routes/music(712行) / thumbnail_downloader(726行)
status: fixed
severity: high
category: architecture
location: squirrel-backend/services/subscription_update/scheduler.py, routes/music.py, core/extraction/services/thumbnail_downloader.py
---

## 问题描述

14 个后端源文件超过 400 行（前次报告约 6 个），核心问题：

**1. services/subscription_update/scheduler.py (917 行)** — 混合调度、内联执行、批量分发、到期枚举、模式解析、优先级解析、事件发射。`run_one_inline()` (248行) 和 `_schedule_one_direct()` (264行) 共享几乎相同的 50 行 site-disabled 检查块

**2. routes/music.py (712 行)** — 路由层代码过长，混合业务逻辑。前次审查已标记但未拆解

**3. core/extraction/services/thumbnail_downloader.py (726 行)** — `download_thumbnail()` 150 行含嵌套函数，`_extract_thumbnail_url_from_html()` 深度嵌套 6 层

**4. services/subscription_sync_center_service.py (696 行)** + **video_extraction_center_service.py (417 行)** — 两个文件有相同的 `_get_cached_site_catalog()` 双检锁缓存模式，以及相同的 `_format_datetime()`、`_summarize_error()`、`_resolve_site_icon_url()` 辅助函数

## 影响

- 维护困难，修改一处需理解 900 行文件
- 重复代码意味着 bug 修复需在多处同步
- 路由层膨胀违反分层架构

## 建议方向

1. scheduler.py: 提取共享 guard 逻辑，拆分为 scheduler/enqueue.py / direct_run.py / batch.py
2. routes/music.py: 业务逻辑下沉到 services/music_service.py
3. thumbnail_downloader.py: 提取 LD-JSON 解析、下载逻辑到独立方法
4. 合并 site catalog 缓存到共享 services/site_catalog_cache.py
