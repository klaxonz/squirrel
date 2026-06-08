---
title: CF-Bypass Browser Context 内存泄漏 + Lock 字典无界增长
status: open
severity: high
category: architecture
location: squirrel-cf-bypass/src/squirrel_cf_bypass/app/core/browser_solver.py:38-46,360,397,430,440,447-454; squirrel-cf-bypass/src/squirrel_cf_bypass/app/core/session_pool.py:27-29
---

## 问题描述

1. **`_browser_entries` 字典无界增长** — `fetch_html()` 成功后，浏览器上下文存入 `_browser_entries`（行 447-454），但无淘汰策略。`SessionPool` 对 HTTP 会话有 `max_sessions=32` 的容量限制和 LRU 淘汰（行 27-29），但浏览器条目没有类似机制，长期运行将耗尽进程内存。

2. **`_locks` 字典无界增长** — `_lock_for(key)` 方法（行 42-46）为每个 `(hostname, proxy)` 组合创建 `asyncio.Lock` 但从不清理。随时间积累永不释放的锁对象。

3. **TTL 过期会话未关闭** — `SessionPool.get()` 移除过期条目但未调用 `.close()`，仅在 `clear()` 中才正确关闭。

## 影响

长时间运行后 OOM，尤其在高吞吐量场景下浏览器上下文持续累积。

## 建议方向

- 为 `_browser_entries` 添加上限（如 `max_entries=64`）和 TTL 淘汰，淘汰时正确关闭上下文
- 为 `_locks` 添加定期清理（如配合 `_browser_entries` 淘汰时删除对应锁）
- 在 `SessionPool.get()` 中移除过期条目前先调用 `.close()`