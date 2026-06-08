---
title: 并发 — 全局可变状态无锁竞争条件
status: fixed
fixed_by: |
  thumbnail_refresh_task.py:44 — _get_shared_http_client 加 threading.Lock
  user_config_service.py:10 — _config_cache 加 threading.Lock
  schedule.py:12 — Scheduler.jobs 加 threading.Lock
  youtubei_core.mjs:257,266 — Promise.all → Promise.allSettled
  bilibili.mjs:67 — Promise.all → Promise.allSettled
severity: high
category: concurrency
location: squirrel-backend/（跨多文件）
---

## 问题描述

### 1. 无锁全局 HTTP 客户端（高影响）

**`schedule/tasks/thumbnail_refresh_task.py:40-64`** — `_get_shared_http_client()` 中 `_shared_http_client`（`httpx.Client`）被 `ThreadPoolExecutor` 多线程同时读写，无锁保护。可能导致：
- 两线程同时发现客户端过期 → 同时关闭 → 第一个创建的客户端丢失
- 一线程使用客户端的另一线程将其关闭 → 连接错误 / 段错误

### 2. 无锁配置缓存

**`services/user_config_service.py:7,14,29,63`** — `_config_cache` 字典被 FastAPI 线程池多线程读写无 `threading.Lock`：
- 读-改-写非原子，GIL 不保证 `dict[key]=value` 线程安全
- `pop()` 和赋值并发时字典可能损坏

### 3. 调度器作业列表无保护

**`schedule/schedule.py:10,69,75`** — `self.jobs` 列表被调度器线程（`_run_jobs`）和主线程（`add_job` / `remove_job`）同时访问无锁。虽然切片迭代 `self.jobs[:]` 避免了运行时错误，但无锁修改仍有丢失更新风险

### 4. Promise.all 无错误隔离（Desktop）

**`squirrel-desktop/src/playback/providers/youtube/youtubei_core.mjs:260`** — `Promise.all` 中一个格式解析失败取消整个视频播放流程
**`squirrel-desktop/src/search/providers/bilibili.mjs:67`** — 同模式，一条格式错误记录破坏整个搜索结果

## 影响

- 并发缩略图刷新时高概率触发 httpx 连接错误/崩溃
- 极端条件下配置缓存读取损坏值
- 调度器作业列表丢失
- 桌面端播放降级

## 建议方向

1. `_get_shared_http_client` 添加 `threading.Lock` 保护读写，或改为 `ThreadLocal` 模式
2. `_config_cache` 添加读写锁，或使用 `functools.lru_cache` + `cachetools`
3. `Scheduler.jobs` 添加锁或改为 `queue.Queue`
4. Desktop Promise.all 使用 `.catch()` 隔离单个失败
