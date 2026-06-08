# 修复方案：trace_id 覆盖后台任务/队列/SDK

## 根因
后端 trace_id 基础设施（`utils/trace.py` + `RequestContextMiddleware`）仅覆盖 HTTP 请求链路，后台调度任务、SDK 子进程、前端/桌面请求未接入 trace context。

## 实地调研结果

| 子项 | 现状 | 结论 |
|------|------|------|
| 调度任务 | `Scheduler._run_job_with_trace()` 已自动包裹 `TraceContext()`，但非调度路径（`execute_task_now`）缺失 | 部分已覆盖，补充 `@with_trace` 做防御性加固 |
| 队列消费者 | `consumer.py:poll_once()` 已通过 `set_trace_id(msg.trace_id)` 恢复 trace_id | **无需修改** |
| SDK | `SiteRuntimeInvokeRequest` 无 `trace_id` 字段，子进程无法接收父进程 trace | 需新增字段 |
| Frontend | `axios.ts` 未注入 `X-Trace-Id` 请求头 | 需添加拦截器 |
| Desktop | 无 trace_id 概念，IPC handler 不与后端直连 | **本次不修**（播放器 provider 独立，不与后端 trace 关联） |
| 子进程 | `runtime_bridge.py` `/invoke` 端点未从请求中提取 trace_id | 需从 request 参数读取 trace_id |

## 修复范围

1. **`schedule/tasks/*.py`** — 9 个任务文件，在 `run()` 上添加 `@with_trace()` 防御性装饰
2. **`squirrel-sdk/src/crawl/runtime_models.py`** — `SiteRuntimeInvokeRequest` 新增 `trace_id: str | None = None` 字段
3. **`site_runtimes/runtime_bridge.py`** — `/invoke` 端点从 request 中提取 trace_id 并 `set_trace_id()`
4. **`site_runtimes/process_launcher.py`** — 子进程 env 注入 `SQUIRREL_TRACE_ID`
5. **`site_runtimes/runtime_bridge.py`** — `main()` 入口从环境变量读取 trace_id 并设置
6. **`squirrel-frontend/src/utils/axios.ts`** — 请求拦截器注入 `X-Trace-Id` 头

## 潜在风险
- SDK 新增字段为可选（`None`），向后兼容
- 子进程 trace_id 传播基于环境变量 + HTTP body，不影响现有传输协议
- 不碰红线文件（`site_runtimes/*.py` 属于本次修复范围，不是红线）
