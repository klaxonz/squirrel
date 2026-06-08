---
title: 命名 — `result`/`data`/`info` 泛滥 + 缩写/风格不一致
status: fixed
fixed_by: 50 files across squirrel-backend/, squirrel-frontend/, squirrel-desktop/, squirrel-sdk/
severity: low
category: naming
location: 全项目跨子项目（~200+ 处）
---

## 问题描述

### 1. `result` 作为变量名（150+ 处）
整个项目将 `result` 用作各类函数返回值的变量名，不传达任何语义。典型分布：
- backend services/（scheduler.py 中 10+ 处）、routes/（subscription.py 中 8+ 处）
- frontend composables/（useUser.ts 中 5 处、useRssFeeds.ts 中 6 处）
- desktop tests/（remote-search-providers.test.mjs 中 15+ 处）
- site-runtimes tests/

### 2. `data` 作为函数参数（50+ 处）
后端 `jwt_helper.py:32`、SDK `core.py:60~418` 密集使用 `data`；路由层多个 `data: XxxRequest` 参数名。

### 3. `info` 作为变量名（30+ 处）
site-runtimes（youtube/subscription.py 中 10+ 处）、desktop（youtubei_core.mjs 中多处）

### 4. 缩写不一致
- `routes/middleware/auth.py`: `AuthenticationError`（全称）vs `AuthMiddleware`（缩写）同一文件
- `common/response.py` 使用 `msg`，但 `music/user.py:143` 同时处理 `message` 和 `msg`

### 5. Frontend `.ts` / `.js` 混用
`src/utils/` 下有 `.ts`（request.ts）也有 `.js`（site-runtime-login-status.js）。video-player runtime 同样混用。

## 影响

- 降低代码可读性，新开发者需反复跳转确定变量的实际意义
- `result` 让搜索和 grep 困难（几乎每页都有）
- 维护者难以区分"这个 result 是列表还是单个对象"

## 建议方向

1. `result` → 具体名词：`users`、`configs`、`items` 等
2. `data` → 具体参数名：`payload`、`body`、`record` 等
3. `info` → 具体化：`video_info`、`account_info`、`metadata`
4. 统一 `msg` → `message`（前端可见场景）
5. 前端 `.js` 文件逐步迁移为 `.ts`
