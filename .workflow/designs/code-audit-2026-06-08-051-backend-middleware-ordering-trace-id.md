---
title: '中间件注册顺序导致 AccessLog 中无 trace_id — 分析'
status: draft
---

## 根因分析

Issue 的分析存在方向性错误。Starlette 的 `add_middleware` 采用**后注册 = 外层包裹**（LIFO 包裹，但请求路径上先执行）：

```
app.add_middleware(AuthMiddleware)            # 1 — innermost
app.add_middleware(ExceptionMiddleware, ...)   # 2
app.add_middleware(AccessLogMiddleware)        # 3
app.add_middleware(RequestContextMiddleware)   # 4 — outermost (last registered)
```

执行顺序（请求路径）：
```
RequestContext → AccessLog → Exception → Auth → handler
```

执行顺序（响应路径）：
```
handler → Auth → Exception → AccessLog (finally logs) → RequestContext (finally resets)
```

**关键点：** `AccessLogMiddleware` 在 `finally` 中记录日志，此时 `RequestContextMiddleware` 的 `finally` 尚未执行（因为 AccessLog 在 RequestContext 内层），因此 `trace_id` 的 ContextVar **仍然可用**。

现有测试 `test_trace_access_log_middleware.py:54` 使用相同的注册顺序（AccessLog → RequestContext），也验证了 `record.trace_id` 正确写入。

## 修复思路

当前中间件注册顺序**正确**，无需改动。Issue 建议的「将 RequestContextMiddleware 移到最先注册」反而会破坏功能：
- 若 RequestContext 变成最内层，其 `finally` 会先于 AccessLog 执行，导致 AccessLog 读到的 trace_id 为 None。

## 涉及文件

无。当前代码正确，无需修改。

## 潜在风险

无。

## 建议

关闭该 issue，标记为 `not_a_bug` / `false_positive`。
