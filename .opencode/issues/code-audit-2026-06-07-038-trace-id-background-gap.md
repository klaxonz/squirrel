---
title: 可观测性 — trace_id 未覆盖后台任务/队列/SDK
status: open
severity: medium
category: error-handling
location: squirrel-backend/schedule/, queues/, squirrel-sdk/src/, squirrel-frontend/src/utils/request.ts
---

## 问题描述

后端已有完善的 trace_id 基础设施（`utils/trace.py` + 路由 middleware），但未覆盖以下路径：

### 1. 调度任务无 trace_id
所有 `schedule/tasks/*.py`（metrics_collection、thumbnail_refresh、subscription auto-import 等）未使用 `@with_trace()` 或 `TraceContext`，日志中 trace_id 均为 `[-]`

### 2. 队列消费者无 trace_id
`queues/consumer.py` 消费消息时未创建 `TraceContext`；`queues/message.py` 消息 schema 未携带 trace_id

### 3. SDK 不支持 trace_id
`squirrel-sdk/src/crawl/*.py` 无 trace_id 概念，插件调用不携带关联 ID

### 4. Frontend 不发送 X-Trace-Id
`utils/request.ts` 和 `utils/axios.ts` 无拦截器读取/生成 trace_id 并附加为请求头

### 5. Desktop 不发送 trace 头
Electron 主进程无 correlation ID，所有 IPC/HTTP 请求丢失客户端上下文

### 6. 子进程 site-runtime 未传递 trace context
`runtime_bridge.py` 启动子进程时未传播父进的 trace_id

## 影响

- 无法将后台/队列操作与触发请求关联
- SDK 发起的提取操作与前端请求无关联
- 端到端链路追踪断裂，排查"用户操作→提取→播放"全链路极为困难

## 建议方向

1. 调度任务装饰 `@with_trace()` 或 `async with TraceContext(...)`
2. 消息 schema 添加 `trace_id` 字段，消费者消费时恢复
3. SDK 调用添加可选 `trace_id` 参数
4. Frontend axios 拦截器自动生成/携带 `X-Trace-Id`
5. Desktop 进程生成 correlation UUID 并在所有 HTTP 请求中传递
6. 子进程启动时通过环境变量传递 trace_id
