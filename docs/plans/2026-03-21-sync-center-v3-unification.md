# Sync Center V3 Unification Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Unify Sync Center overview state rendering onto V2 projections and make recovery actions visible, explainable, and manually triggerable inside the Sync Center.

**Architecture:** Stop reading `subscription_sync_state` as the primary UI source for overview state and instead derive overview and list cards from `subscription_sync_subscription_projection` and `subscription_sync_run_projection`. Extend the existing queued/running recovery work by emitting recovery events, exposing a reconcile API, and adding recovery summary UI on the Sync Center overview tab.

**Tech Stack:** FastAPI, SQLAlchemy, existing sync event/projector chain, Vue 3, existing sync-center composables and components

---

> 当前仓库约束：本计划不新增单元测试，验证以 Python 编译检查、前端 `typecheck` 和 `build:check` 为主。

### Task 1: 用 projection 重构概览查询

**Files:**
- Modify: `squirrel-backend/services/subscription_sync_center_service.py`

**Step 1: 将 overview 聚合切到 projection**

把 `get_sync_center_overview()` 从基于 `subscription_sync_state` 的汇总改为基于：

- `subscription_sync_run_projection`
- `subscription_sync_subscription_projection`

要求：

- 运行中、排队中、失败待处理优先读 `run_projection`
- 当前订阅状态摘要读 `subscription_projection`
- 不再依赖“每订阅选一个 preferred sync_state”作为主来源

**Step 2: 将 items 查询切到 projection**

把 `list_sync_center_items()` 的主数据源切到：

- `subscription_sync_run_projection` for `running/queued/recent/failed`
- `subscription_sync_subscription_projection` only when needed for current state补充

要求：

- 保持当前前端接口结构不变
- 避免继续把陈旧 `subscription_sync_state.queued` 直接显示成当前队列状态

**Step 3: 编译检查**

Run:

```powershell
Set-Location 'D:\Code\init\squirrel\squirrel-backend'
python -m compileall services
```

Expected: compile 成功

**Step 4: Commit**

```powershell
git add squirrel-backend/services/subscription_sync_center_service.py
git commit -m "refactor: drive sync center overview from projections"
```

### Task 2: 恢复动作事件化

**Files:**
- Modify: `squirrel-backend/services/subscription_sync_state_service.py`
- Modify: `squirrel-backend/services/subscription_sync_event_service.py`
- Modify: `squirrel-backend/services/subscription_sync_projection_service.py`

**Step 1: 新增恢复事件类型**

在运行服务常量中补齐：

- `stale_queued_recovered`
- `stale_running_recovered`
- `manual_reconcile_triggered`

**Step 2: stale queued 恢复写事件**

在 `recover_stale_queued_sync_states()` 中，不只改状态，还要写事件：

- `event_type=stale_queued_recovered`
- payload 包含 `reason=stale_queued_missing_message`

**Step 3: stale running 恢复写事件**

在 stale running 恢复路径里补：

- `event_type=stale_running_recovered`

**Step 4: projector 接受恢复事件**

在 `subscription_sync_projection_service.py` 中，把恢复事件映射到：

- `run_projection.status`
- `subscription_projection.current_status`
- 以及必要的失败原因字段

**Step 5: 编译检查**

Run:

```powershell
Set-Location 'D:\Code\init\squirrel\squirrel-backend'
python -m compileall services
```

Expected: compile 成功

**Step 6: Commit**

```powershell
git add squirrel-backend/services/subscription_sync_state_service.py squirrel-backend/services/subscription_sync_event_service.py squirrel-backend/services/subscription_sync_projection_service.py
git commit -m "feat: emit recovery events for sync state repairs"
```

### Task 3: 增加手动 reconcile 接口

**Files:**
- Modify: `squirrel-backend/routes/subscription.py`

**Step 1: 新增 reconcile 接口**

新增：

```python
@router.post('/api/subscription/sync-center/reconcile')
def reconcile_sync_center(...):
    ...
```

返回：

- `recovered`
- `queued_states`
- `running_states`
- `reconcile_at`

**Step 2: 接口里触发恢复**

调用：

- `recover_stale_queued_sync_states()`
- `recover_stale_sync_state(...)` 或对应批量 stale running 扫描

要求：

- 返回结构稳定
- 错误时返回可读消息

**Step 3: 编译检查**

Run:

```powershell
Set-Location 'D:\Code\init\squirrel\squirrel-backend'
python -m compileall routes
```

Expected: compile 成功

**Step 4: Commit**

```powershell
git add squirrel-backend/routes/subscription.py
git commit -m "feat: add sync center reconcile endpoint"
```

### Task 4: 前端概览切到统一口径并展示恢复面板

**Files:**
- Modify: `squirrel-frontend/src/composables/useSyncCenter.ts`
- Modify: `squirrel-frontend/src/views/SyncCenter.vue`
- Create: `squirrel-frontend/src/api/subscriptionSyncRecovery.ts`
- Modify: `squirrel-frontend/src/api/index.ts`

**Step 1: 新增 recovery API**

增加：

- `getSyncRecoverySummary`
- `reconcileSyncCenter`

**Step 2: composable 接入恢复摘要**

在 `useSyncCenter.ts` 中管理：

- `recoverySummary`
- `reconciling`

**Step 3: 概览页增加恢复面板**

在 overview tab 顶部或右侧卡片区增加：

- 最近恢复时间
- 恢复数量
- 手动执行状态对账按钮

**Step 4: 手动 reconcile 后刷新当前页**

按钮执行后：

- 刷新 overview
- 刷新当前列表
- 更新 recovery summary

**Step 5: 前端类型检查**

Run:

```powershell
Set-Location 'D:\Code\init\squirrel\squirrel-frontend'
npm run typecheck
```

Expected: typecheck 通过

**Step 6: Commit**

```powershell
git add squirrel-frontend/src/api squirrel-frontend/src/composables/useSyncCenter.ts squirrel-frontend/src/views/SyncCenter.vue
git commit -m "feat: add sync recovery controls to overview"
```

### Task 5: 历史页解释恢复动作

**Files:**
- Modify: `squirrel-frontend/src/components/sync-center/SyncEventTimeline.vue`
- Modify: `squirrel-frontend/src/components/sync-center/SyncRunDetailDrawer.vue`

**Step 1: 给恢复事件特殊展示**

在事件时间线中对以下事件做特殊文案：

- `stale_queued_recovered`
- `stale_running_recovered`
- `manual_reconcile_triggered`

**Step 2: 在详情页展示恢复原因**

如果运行实例最终是恢复导致的状态变化，详情页要能直接看到：

- 恢复类型
- 恢复原因

**Step 3: 前端构建检查**

Run:

```powershell
Set-Location 'D:\Code\init\squirrel\squirrel-frontend'
npm run build:check
```

Expected: build 和 typecheck 通过

**Step 4: Commit**

```powershell
git add squirrel-frontend/src/components/sync-center
git commit -m "feat: visualize sync recovery events"
```
