---
title: 中间件注册顺序导致 AccessLog 中无 trace_id
status: not_a_bug
resolution: false_positive — current middleware ordering is correct; Starlette LIFO ensures AccessLogMiddleware's finally block runs before RequestContextMiddleware's finally, so trace_id is always available.
severity: medium
category: architecture
location: squirrel-backend/routes/base.py:78-98
---

## 问题描述

中间件注册顺序为：`AuthMiddleware` → `ExceptionMiddleware` → `AccessLogMiddleware` → `RequestContextMiddleware`。由于 Starlette 中间件是 LIFO 执行，`RequestContextMiddleware`（绑定 trace_id）作为最内层（最后注册）执行，而 `AccessLogMiddleware`（记录日志）在其外层先执行。因此访问日志无法包含 trace_id。

## 影响

- 访问日志与追踪 ID 脱钩，无法按请求追溯
- 运维排障时需要额外关联请求时间等其他维度

## 建议方向

将 `RequestContextMiddleware` 改为最外层（最先注册）：`RequestContextMiddleware` → `AuthMiddleware` → `ExceptionMiddleware` → `AccessLogMiddleware`。确保 trace_id 在整个请求生命周期都可用。
