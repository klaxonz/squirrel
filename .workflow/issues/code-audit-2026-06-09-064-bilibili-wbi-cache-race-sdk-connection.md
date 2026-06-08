---
title: Bilibili WBI 缓存竞态 + SDK request_without_limit 无连接复用
status: open
severity: medium
category: architecture
location: squirrel-site-runtimes/bilibili/sign.py:42-65(WBI); squirrel-sdk/src/crawl/http.py:251-293(connection)
---

## 问题描述

**1. Bilibili WBI Key 缓存竞态** (`sign.py:42-65`)

`get_wbi_keys()` 检查并设置 `_WBI_KEY_CACHE` / `_WBI_KEY_CACHE_TS` 时无锁保护。多线程并发调用时，多个线程可能同时发现缓存过期，各自发起冗余的 `/x/web-interface/nav` 请求。虽然不会导致数据损坏，但会产生不必要的 API 调用。

```python
if _WBI_KEY_CACHE is None or (time.time() - _WBI_KEY_CACHE_TS) > 3600:
    # 多线程可能同时进入此分支
    result = await client.get(...)  # 冗余请求
    _WBI_KEY_CACHE = ...
    _WBI_KEY_CACHE_TS = time.time()
```

**2. SDK `request_without_limit` 每次调用创建新 Session** (`http.py:251-293`)

`request_without_limit()` 在不走 bypass 时每次创建全新 `requests.Session` + `HTTPAdapter` + `Retry` 配置。与 `get_http_session()` 使用的共享会话池不同，此路径完全无法复用 TCP 连接。对批量导入等频繁调用场景性能影响显著。

## 影响

WBI 竞态导致偶发冗余 API 请求；`request_without_limit` 导致频繁 TCP 握手。

## 建议方向

- WBI 缓存添加 `threading.Lock`（类似 `youtubei_resolver.py` 的做法）
- `request_without_limit` 改为复用或懒初始化连接池