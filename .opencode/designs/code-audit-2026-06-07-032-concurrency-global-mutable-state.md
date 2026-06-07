# 032 — 并发全局可变状态修复方案

## 根因
全局可变状态（`_shared_http_client`、`_config_cache`、`Scheduler.jobs`、`Promise.all`）在多线程/异步环境下无锁/无错误隔离，导致竞争条件或单点失败。

## 修复思路

### 1. `thumbnail_refresh_task.py:_get_shared_http_client()` — 加 `threading.Lock`
在模块级别添加 `_http_client_lock`，保护 `_shared_http_client` 的读写和重建逻辑。

### 2. `user_config_service.py:_config_cache` — 加 `threading.Lock`
在模块级别添加 `_cache_lock`，保护 `get_config` 的缓存检查/写入和 `update_config` 的缓存失效。

### 3. `schedule.py:Scheduler.jobs` — 加 `threading.Lock`
在 `__init__` 添加 `self._lock`，保护 `add_job`、`remove_job` 和 `_run_jobs` 中 jobs 列表的读写。

### 4. `youtubei_core.mjs` — `Promise.allSettled` 替换 `Promise.all`
避免单个 format 解析失败导致整个收集流程崩溃。

### 5. `bilibili.mjs` — `Promise.allSettled` 替换 `Promise.all`
避免单个搜索结果的 `loadUploaderProfile` 失败导致整个搜索结果丢失。

## 涉及文件
- `squirrel-backend/schedule/tasks/thumbnail_refresh_task.py`
- `squirrel-backend/services/user_config_service.py`
- `squirrel-backend/schedule/schedule.py`
- `squirrel-desktop/src/playback/providers/youtube/youtubei_core.mjs`
- `squirrel-desktop/src/search/providers/bilibili.mjs`

## 潜在风险
- Lock 粒度：所有锁只在临界区持有，不跨越 IO 操作，避免死锁
- Promise.allSettled 会改变异常处理语义（静默吞错误），但后续逻辑已有 filter/null 保护
