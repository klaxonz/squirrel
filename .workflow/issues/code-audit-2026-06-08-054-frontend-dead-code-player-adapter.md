---
title: BackendPlayerAdapter 未使用的 syncTimer 字段和空 catch-rethrow
status: fixed
fixed_by: code-fix workflow
resolved_at: 2026-06-09
severity: low
category: dead-code
location: squirrel-frontend/src/components/video-player/core/BackendPlayerAdapter.ts:6,242-244
---

## 问题描述

两处死代码：
1. **L6**: `private syncTimer: ReturnType<typeof setInterval> | null = null` 声明但从未使用。实际定时器是 `syncTimerHandle`（L30）
2. **L242-244**: `catch (err) { throw err }` 捕获后原封不动重新抛出，无任何上下文添加

## 影响

- 混入阅读：开发者需要花时间理解为什么 `syncTimer` 存在
- 空 catch-rethrow 增加文件长度无任何收益

## 建议方向

1. 移除未使用的 `syncTimer` 字段
2. 移除 `catch (err) { throw err }` 或将有意义上下文 wrap 后重新抛出
