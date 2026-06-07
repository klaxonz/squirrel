---
title: 'Backend: 分层违规 — routes 层混入业务逻辑和直连数据库'
severity: high
category: architecture
location: squirrel-backend/routes/sites.py:24-159, routes/playlist.py:54-74,181-226
---

## 问题描述

多处违反分层架构：

1. **routes/sites.py** 包含 5 个纯业务逻辑函数：`normalize_cookie_domain`、`select_primary_domain`、`merge_site_names`、`merge_site_catalogs`（43 行）、`build_site_info`。这些与 HTTP 无关，应属于 service 层。

2. **routes/playlist.py** 包含直连数据库的 SQLAlchemy 查询：`get_playlist_items` (line 54) 直接 `session.scalars(select(Video)...)`；`play_next_video` (line 181) 包含 32 行的导航算法，完全绕过 service 层。

3. **routes/music.py** (761 lines, ~70 endpoints) 每个 endpoint 都是相同的 try/except/music_service 模式，无任何业务逻辑但仍需 70 个重复的 try/except 块。

## 影响

- 业务逻辑不可与 HTTP 层解耦测试
- 导致潜在循环依赖（routes 引用 services，services 不应引用 routes）
- 70 个重复的 try/except 块使文件膨胀且难以维护

## 建议方向

1. 将 routes/sites.py 中的业务逻辑移到 `services/site_catalog_service.py` 或新的 `core/site_config_manager.py`
2. 将 routes/playlist.py 的 DB 查询移到 `services/playlist_service.py`
3. 为 routes/music.py 创建 `@handle_music_error` 装饰器或 FastAPI 异常处理器消除重复
