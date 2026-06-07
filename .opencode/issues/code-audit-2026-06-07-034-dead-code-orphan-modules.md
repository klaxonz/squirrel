---
title: 死代码 — 后端 1700+ 行孤立模块 + 未使用依赖
status: open
severity: high
category: dead-code
location: squirrel-backend/utils/, models/, queues/, core/, Pipfile, package.json（跨项目）
---

## 问题描述

### 完全孤立的工具模块（从未被任何模块导入）

| 文件 | 行数 | 内容 |
|------|------|------|
| `utils/cloudflare_bypass.py` | 147 | CloudflareMirrorClient（cloudscraper + httpx） |
| `utils/rate_limiter.py` | 100+ | DomainRateLimiter，按域名限速 |
| `utils/metrics.py` | 535 | MetricsCollector 完整监控框架 |
| `utils/trace.py` | 141 | TraceContext + get_trace_id（另有 middleware trace 独立运行） |
| `utils/sql_parser.py` | 50+ | format_sql / parse_sql |
| `utils/site_icons.py` | — | 站点图标工具 |
| `queues/queue_monitor.py` | 73 | QueueBackpressureMonitor |
| `core/cache.py` | — | Redis 连接池（redis_lock） |
| `processes/managers/crawl_worker_runtime.py` | — | CrawlWorkerRuntime 完整运行态 |

### 孤立模型（ORM 定义但应用代码未引用）

`models/crawl_job.py`、`models/message.py`、`models/creator.py`、`models/request_log.py`、`models/mixins/serializer.py`

### 未使用的依赖

**Pipfile（backend）：** `pytubefix`, `js2py`, `pipdeptree`, `bilibili-api-python`, `cloudscraper`, `sse-starlette`, `concurrent-log-handler`, `phub`

**package.json（desktop）：** `axios`, `bgutils-js`, `jsdom`, `proxy-agent`

**package.json（frontend）：** `lodash`, `lodash-es`, `mitt`（均未在源码中 import）

## 影响

- ~1700 行代码无主，误导开发者以为功能存在
- 幽灵依赖增加镜像体积和安全攻击面
- 新人不确定这些模块是否应使用还是已废弃
- 迁移/维护成本持续增加

## 建议方向

1. 对每个孤立模块确认用途：删除、或加导入使其有用、或标 `@deprecated`
2. 清理 Pipfile / package.json 未使用依赖
3. 孤立模型如确实不用则删除（注意 Alembic 迁移兼容）
