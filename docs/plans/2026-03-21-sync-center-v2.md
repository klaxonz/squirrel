# Sync Center V2 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build Sync Center V2 with complete execution history, event-sourced sync tracking, projection-backed overview queries, and trend analysis.

**Architecture:** Keep `subscription_sync_state` as the scheduling and locking source, but add `subscription_sync_event` as the fact stream and projection tables for run history, subscription status, and time-bucket trends. Write events at scheduler/state/orchestrator/strategy boundaries, project them synchronously into read models, and extend the frontend Sync Center into overview, history, and trends tabs.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, existing subscription scheduler/orchestrator chain, Vue 3, Vue Router, existing request/composable/component stack

---

> 当前仓库约束：本计划不新增单元测试，验证以数据库迁移可执行、Python 编译检查、前端 `typecheck` 和 `build:check` 为主。

### Task 1: 建立事件表与 Projection 表

**Files:**
- Create: `squirrel-backend/models/subscription_sync_event.py`
- Create: `squirrel-backend/models/subscription_sync_run_projection.py`
- Create: `squirrel-backend/models/subscription_sync_subscription_projection.py`
- Create: `squirrel-backend/models/subscription_sync_trend_projection.py`
- Create: `squirrel-backend/alembic/versions/<timestamp>_add_sync_center_v2_tables.py`

**Step 1: 定义事件表模型**

在 `squirrel-backend/models/subscription_sync_event.py` 定义事件模型，字段至少包括：

```python
id
stream_id
subscription_id
sync_state_id
site
sync_mode
trigger
request_id
trace_id
event_type
event_phase
event_status
seq_no
payload
occurred_at
created_at
```

同时补必要索引：

- `stream_id + seq_no`
- `subscription_id + occurred_at`
- `site + occurred_at`
- `event_type + occurred_at`

**Step 2: 定义运行实例投影**

在 `squirrel-backend/models/subscription_sync_run_projection.py` 定义运行实例快照，字段至少包括：

```python
run_id
subscription_id
sync_state_id
site
sync_mode
trigger
request_id
trace_id
status
current_phase
queued_at
started_at
finished_at
duration_ms
failure_count
error_type
error_message
videos_found
videos_enqueued
videos_extracted
videos_skipped
pending_video_count
last_event_at
created_at
updated_at
```

**Step 3: 定义订阅状态投影**

在 `squirrel-backend/models/subscription_sync_subscription_projection.py` 定义当前订阅视图，字段至少包括：

```python
subscription_id
latest_run_id
current_status
current_phase
last_sync_at
last_success_at
next_sync_at
last_error_message
pending_video_count
failure_streak
updated_at
```

**Step 4: 定义趋势投影**

在 `squirrel-backend/models/subscription_sync_trend_projection.py` 定义时间桶聚合，字段至少包括：

```python
bucket_time
site
sync_mode
trigger
runs_total
runs_success
runs_failed
runs_deferred
videos_found
videos_enqueued
videos_extracted
videos_skipped
avg_duration_ms
p95_duration_ms
updated_at
```

**Step 5: 编写 Alembic 迁移**

在 `squirrel-backend/alembic/versions/<timestamp>_add_sync_center_v2_tables.py` 中创建上述 4 张表与索引。

**Step 6: 本地编译检查**

Run:

```powershell
Set-Location 'D:\Code\init\squirrel\squirrel-backend'
python -m compileall models alembic
```

Expected: compile 成功

**Step 7: Commit**

```powershell
git add squirrel-backend/models squirrel-backend/alembic
git commit -m "feat: add sync event and projection tables"
```

### Task 2: 建立事件写入与 Projection 基础设施

**Files:**
- Create: `squirrel-backend/services/subscription_sync_event_service.py`
- Create: `squirrel-backend/services/subscription_sync_projection_service.py`
- Create: `squirrel-backend/services/subscription_sync_run_service.py`

**Step 1: 创建运行实例服务**

在 `squirrel-backend/services/subscription_sync_run_service.py` 实现：

- `create_run(...)`
- `build_run_id()`
- `append_sequence(...)`

要求：

- 在真正决定入队或生成运行实例时产生稳定 `run_id`
- `stream_id == run_id`
- 维护实例内递增 `seq_no`

**Step 2: 创建事件写入服务**

在 `squirrel-backend/services/subscription_sync_event_service.py` 实现：

- `append_event(...)`
- `append_events(...)`
- `serialize_payload(...)`

要求：

- 输入统一结构，避免业务代码直接操作 event model
- 支持 `payload` 的 dict 序列化
- 自动补 `occurred_at`

**Step 3: 创建同步 projector**

在 `squirrel-backend/services/subscription_sync_projection_service.py` 实现：

- `apply_event(event)`
- `apply_events(events)`
- `project_run(...)`
- `project_subscription(...)`
- `project_trend(...)`

要求：

- 同步更新三张 projection
- `run_projection` 更新当前实例快照
- `subscription_projection` 更新当前订阅最新状态
- `trend_projection` 更新小时/天时间桶指标

**Step 4: 本地编译检查**

Run:

```powershell
Set-Location 'D:\Code\init\squirrel\squirrel-backend'
python -m compileall services
```

Expected: compile 成功

**Step 5: Commit**

```powershell
git add squirrel-backend/services/subscription_sync_event_service.py squirrel-backend/services/subscription_sync_projection_service.py squirrel-backend/services/subscription_sync_run_service.py
git commit -m "feat: add sync event writer and projector"
```

### Task 3: 在调度与状态链路中接入事件写入

**Files:**
- Modify: `squirrel-backend/services/subscription_update/scheduler.py`
- Modify: `squirrel-backend/services/subscription_sync_state_service.py`
- Modify: `squirrel-backend/consumer/processors/subscription_update_task.py`

**Step 1: 在 scheduler 中创建运行实例**

在 `scheduler.schedule_one(...)` 中：

- 生成 `run_id`
- 记录 `run_created`
- 成功排队时记录 `queued`
- `site_disabled / no_subscribers / deferred` 也写事件

并把 `run_id` 放入消息体，向消费者继续传递。

**Step 2: 在 claim 与状态变更处记录事件**

在 `subscription_sync_state_service.py` 中补事件：

- `claim_sync_state(...)` 写 `claimed`
- `mark_sync_success(...)` 写 `completed`
- `mark_sync_failed(...)` 写 `failed`
- `defer_sync_state(...)` 写 `deferred`
- `recover_stale_sync_state(...)` 写 `timeout_recovered`

**Step 3: 在消费者入口补 started 事件**

在 `consumer/processors/subscription_update_task.py` 中：

- 从消息里取 `run_id`
- 进入实际编排前写 `started`

**Step 4: 本地编译检查**

Run:

```powershell
Set-Location 'D:\Code\init\squirrel\squirrel-backend'
python -m compileall services consumer
```

Expected: compile 成功

**Step 5: Commit**

```powershell
git add squirrel-backend/services/subscription_update/scheduler.py squirrel-backend/services/subscription_sync_state_service.py squirrel-backend/consumer/processors/subscription_update_task.py
git commit -m "feat: emit sync lifecycle events from scheduler and state flow"
```

### Task 4: 在编排与策略链路中补齐阶段和统计事件

**Files:**
- Modify: `squirrel-backend/services/subscription_update/orchestrator.py`
- Modify: `squirrel-backend/services/subscription_update/strategies/base.py`
- Modify: `squirrel-backend/services/subscription_update/strategies/default_strategy.py`
- Modify: `squirrel-backend/services/video_extraction/extractor.py`

**Step 1: 固定阶段枚举**

在合适位置新增或复用常量，收敛为：

- `init`
- `queued`
- `claimed`
- `fetching_feed`
- `calculating_delta`
- `extracting`
- `enqueueing`
- `finalizing`
- `completed`
- `failed`
- `deferred`

**Step 2: 在 orchestrator / strategy 中写阶段切换**

在 `orchestrator.py` 和 `default_strategy.py` 中：

- 进入抓取源时写 `phase_changed(fetching_feed)`
- 计算增量时写 `phase_changed(calculating_delta)`
- 入队视频时写 `phase_changed(enqueueing)`
- 收尾时写 `phase_changed(finalizing)`

**Step 3: 在统计变化点写事件**

在 `default_strategy.py` 中：

- 发现视频时写 `video_found`
- 入队视频时写 `video_enqueued`
- 跳过视频时写 `video_skipped`

在 `video_extraction/extractor.py` 中：

- 提取完成时写 `video_extracted`

**Step 4: 本地编译检查**

Run:

```powershell
Set-Location 'D:\Code\init\squirrel\squirrel-backend'
python -m compileall services
```

Expected: compile 成功

**Step 5: Commit**

```powershell
git add squirrel-backend/services/subscription_update/orchestrator.py squirrel-backend/services/subscription_update/strategies squirrel-backend/services/video_extraction/extractor.py
git commit -m "feat: record sync phases and metrics events"
```

### Task 5: 建立历史与趋势查询接口

**Files:**
- Create: `squirrel-backend/services/subscription_sync_history_service.py`
- Create: `squirrel-backend/services/subscription_sync_trend_service.py`
- Modify: `squirrel-backend/routes/subscription.py`

**Step 1: 实现运行历史查询服务**

在 `squirrel-backend/services/subscription_sync_history_service.py` 实现：

- `list_runs(...)`
- `get_run_detail(run_id, user_id)`
- `list_run_events(run_id, user_id)`

要求：

- 读取 `run_projection`
- 详情下钻到 `subscription_sync_event`
- 严格按当前用户有效订阅校验访问范围

**Step 2: 实现趋势查询服务**

在 `squirrel-backend/services/subscription_sync_trend_service.py` 实现：

- `get_trends(range, site, mode, trigger)`
- `get_site_breakdown(...)`

要求：

- 读取 `trend_projection`
- 支持 `24h / 7d / 30d`
- 按小时或按天输出

**Step 3: 新增路由接口**

在 `squirrel-backend/routes/subscription.py` 增加：

- `GET /api/subscription/sync-center/runs`
- `GET /api/subscription/sync-center/runs/{run_id}`
- `GET /api/subscription/sync-center/runs/{run_id}/events`
- `GET /api/subscription/sync-center/trends`

**Step 4: 本地编译检查**

Run:

```powershell
Set-Location 'D:\Code\init\squirrel\squirrel-backend'
python -m compileall routes services
```

Expected: compile 成功

**Step 5: Commit**

```powershell
git add squirrel-backend/services/subscription_sync_history_service.py squirrel-backend/services/subscription_sync_trend_service.py squirrel-backend/routes/subscription.py
git commit -m "feat: add sync history and trend endpoints"
```

### Task 6: 扩展前端同步中心为多 Tab 容器

**Files:**
- Modify: `squirrel-frontend/src/views/SyncCenter.vue`
- Create: `squirrel-frontend/src/composables/useSyncOverview.ts`
- Create: `squirrel-frontend/src/composables/useSyncHistory.ts`
- Create: `squirrel-frontend/src/composables/useSyncTrends.ts`
- Create: `squirrel-frontend/src/api/subscriptionSyncHistory.ts`
- Create: `squirrel-frontend/src/api/subscriptionSyncTrends.ts`
- Modify: `squirrel-frontend/src/api/index.ts`

**Step 1: 拆分 composable**

将现有同步中心逻辑拆分为：

- `useSyncOverview`
- `useSyncHistory`
- `useSyncTrends`

**Step 2: 增加 API 封装**

新增：

- 历史列表接口
- 历史详情接口
- 历史事件接口
- 趋势接口

**Step 3: 改造 SyncCenter 主容器**

在 `SyncCenter.vue` 中增加三个 tab：

- `概览`
- `运行历史`
- `趋势分析`

要求：

- 保留现有 Overview tab
- 其余两个 tab 延迟加载对应数据

**Step 4: 前端类型检查**

Run:

```powershell
Set-Location 'D:\Code\init\squirrel\squirrel-frontend'
npm run typecheck
```

Expected: typecheck 通过

**Step 5: Commit**

```powershell
git add squirrel-frontend/src/views/SyncCenter.vue squirrel-frontend/src/composables squirrel-frontend/src/api
git commit -m "feat: split sync center into overview history and trends"
```

### Task 7: 实现运行历史与事件时间线界面

**Files:**
- Create: `squirrel-frontend/src/components/sync-center/SyncRunHistoryPanel.vue`
- Create: `squirrel-frontend/src/components/sync-center/SyncRunDetailDrawer.vue`
- Create: `squirrel-frontend/src/components/sync-center/SyncEventTimeline.vue`
- Modify: `squirrel-frontend/src/views/SyncCenter.vue`

**Step 1: 实现运行历史列表**

历史列表支持：

- 状态筛选
- 站点筛选
- 模式筛选
- 触发来源筛选
- 时间范围

每行展示：

- 订阅
- 状态
- 模式
- 触发来源
- 开始时间
- 耗时
- 错误摘要

**Step 2: 实现运行详情抽屉**

详情抽屉展示：

- 运行摘要
- request_id / trace_id
- 阶段摘要
- 核心计数

**Step 3: 实现事件时间线**

`SyncEventTimeline.vue` 展示事件流：

- 时间
- 类型
- 阶段
- 状态
- message
- payload 摘要

**Step 4: 前端类型检查**

Run:

```powershell
Set-Location 'D:\Code\init\squirrel\squirrel-frontend'
npm run typecheck
```

Expected: typecheck 通过

**Step 5: Commit**

```powershell
git add squirrel-frontend/src/components/sync-center squirrel-frontend/src/views/SyncCenter.vue
git commit -m "feat: add sync run history and event timeline views"
```

### Task 8: 实现趋势分析界面

**Files:**
- Create: `squirrel-frontend/src/components/sync-center/SyncTrendCharts.vue`
- Modify: `squirrel-frontend/src/views/SyncCenter.vue`

**Step 1: 实现趋势视图**

先用现有组件风格实现 4 组图表区域：

- 运行结果趋势
- 视频吞吐趋势
- 时延趋势
- 站点分布

要求：

- 先实现数据切换和卡片式图表容器
- 图表库如仓库未引入，可先用 SVG/简化折线或条形图实现

**Step 2: 实现时间范围和筛选联动**

支持：

- `24h`
- `7d`
- `30d`
- `site`
- `mode`
- `trigger`

**Step 3: 前端构建检查**

Run:

```powershell
Set-Location 'D:\Code\init\squirrel\squirrel-frontend'
npm run build:check
```

Expected: build 和 typecheck 通过

**Step 4: Commit**

```powershell
git add squirrel-frontend/src/components/sync-center squirrel-frontend/src/views/SyncCenter.vue
git commit -m "feat: add sync trend analysis views"
```

### Task 9: 收口、迁移验证与最终校验

**Files:**
- Modify: `squirrel-backend/routes/subscription.py`
- Modify: `squirrel-backend/services/subscription_sync_center_service.py`
- Modify: `squirrel-frontend/src/views/SyncCenter.vue`

**Step 1: 收口首页到 Projection**

将 Sync Center 概览页中适合直接走 projection 的部分切到 V2 读模型，减少和事件写入链路的口径差异。

**Step 2: 校验迁移兼容性**

确认：

- 旧同步中心 V1 能继续工作
- 没有历史事件的旧数据不会导致页面崩溃
- V2 页面在无历史数据时展示合理空态

**Step 3: 后端全量编译检查**

Run:

```powershell
Set-Location 'D:\Code\init\squirrel\squirrel-backend'
python -m compileall routes services schemas models
```

Expected: compile 成功

**Step 4: 前端全量构建检查**

Run:

```powershell
Set-Location 'D:\Code\init\squirrel\squirrel-frontend'
npm run build:check
```

Expected: build 和 typecheck 通过

**Step 5: Commit**

```powershell
git add squirrel-backend squirrel-frontend
git commit -m "feat: complete sync center v2 event sourcing"
```
