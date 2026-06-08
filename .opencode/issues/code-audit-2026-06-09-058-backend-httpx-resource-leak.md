---
title: Backend httpx AsyncClient 资源泄漏 — MusicClient 和 ThumbnailDownloader 未关闭
status: open
severity: medium
category: architecture
location: squirrel-backend/services/music/_client.py:28-29; squirrel-backend/services/extraction/thumbnail_downloader.py:76-82; squirrel-backend/services/metrics_service.py:43-68
---

## 问题描述

1. **`MusicClient`** (`_client.py:28-29`) — `httpx.AsyncClient` 在 `__init__` 中创建，但没有 `aclose()` 方法或上下文管理器，连接永远不会被关闭。

2. **`ThumbnailDownloaderService`** (`thumbnail_downloader.py:76-82`) — 同步 `httpx.Client` 懒初始化但仅在 `_reset_http_client()` 或出错时关闭，无 `__del__` 或上下文管理器保障清理。

3. **`MetricsService`** (`metrics_service.py:43-68`) — 使用 `next(get_db())` 而非 `with get_session()` 上下文管理器，绕过会话生命周期管理。

对比 `connectivity_service.py:131-136` 正确使用了 `async with httpx.AsyncClient(...)` 模式。

## 影响

长期运行导致连接池泄漏，尤其在 `MusicClient` 场景下每次初始化创建新客户端但从不释放。

## 建议方向

- `MusicClient` / `ThumbnailDownloaderService` 添加 `aclose()` / `close()` 方法，或实现 `__aenter__`/`__aexit__`
- `MetricsService` 改用 `with get_session()` 上下文管理器
- 考虑将 httpx 客户端绑定到应用生命周期（`lifespan` 事件）