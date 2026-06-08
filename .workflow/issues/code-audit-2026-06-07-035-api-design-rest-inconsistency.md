---
title: API 设计 — 动词 URL / 无版本 / 响应格式不一致
status: open
severity: medium
category: api-design
location: squirrel-backend/routes/（跨16个路由模块）
---

## 问题描述

### 1. 动词在 URL 中（RPC 风格，28+ 端点）

典型问题：`POST /api/subscription/subscribe`、`/unsubscribe`、`/toggle-nsfw`、`/refresh`、`/refresh/direct`；`POST /api/video-interaction/toggle-like`、`/delete`；`POST /api/scheduler/tasks/{id}/enable`、`/execute` 等。应使用标准 HTTP 方法 + 资源路径。

### 2. 无 API 版本前缀

所有路由注册在 `/api/` 下，无 `/api/v1/`。任何破坏性变更（如响应格式变化）无法渐进式推出。

### 3. 响应信封不一致

- **不使用标准 envelope 的端点：** `/health`、`/health/ready`、`/health/live`、`/connectivity/test`、`/system/config` 等 6 组
- **列表响应格式不统一：** `data` 字段内有时是 `{"total": N, "page": N, "data": [...]}`，有时是 `{"items": [...]}`，有时是裸数组，有时是 `{"data": [...]}`（两层嵌套 data）

### 4. 复数/单数命名不一致

`/api/video`（单数）vs `/api/video-clip-markers`（复数）vs `/api/sites`（复数）vs `/api/subscription`（单数）

### 5. POST 端点参数在 Query 而非 Body

`POST /api/music/artist/follow?artist_id=X`、`POST /api/music/auth/login?phone=...` 等

## 影响

- 前后端对接困难：前端需为不同端点适配不同响应格式
- 无版本号 → 无法做 API 兼容策略
- RESTful 约定缺失 → API 难以发现和自文档化

## 建议方向

1. 所有资源路径统一复数，动作通过 HTTP method 表达
2. 添加 `/api/v1/` 前缀，保留对旧路径的兼容重定向
3. 统一响应信封：`{code, msg, data}` + 分页用 `{total, page, pageSize, items}`
4. POST 动作参数全走 body
