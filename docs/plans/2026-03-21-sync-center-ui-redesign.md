# Sync Center UI Redesign Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Rebuild Sync Center into a high-density monitoring and analysis workspace that prioritizes global health judgment and fast drill-down into run and event evidence.

**Architecture:** Keep the existing Sync Center APIs and composables as the data backbone, but replace the current tabbed page with a single workbench driven by shared page state. The new page is composed of a compact control bar, a dense signal matrix, a focus board, and a reusable analysis workspace that reuses run, trend, item, and event detail capabilities in embedded mode.

**Tech Stack:** Vue 3 `<script setup>`, existing sync-center composables, Tailwind utility classes, Vite, vue-tsc

---

> 当前仓库状态：`squirrel-frontend/src/views/SyncCenter.vue` 等同步中心文件已有未提交改动。执行本计划前先在独立 worktree 中开始，避免把现有改动和本轮实现混在一起。
>
> 仓库约束：本计划不新增单元测试，验证以 `npm run typecheck` 和 `npm run build:check` 为主。
>
> 执行时的视觉收束参考 `@frontend-design`，完成前使用 `@verification-before-completion` 做最终校验。

### Task 1: 建立单页工作台状态模型

**Files:**
- Create: `squirrel-frontend/src/composables/useSyncCenterWorkbench.ts`
- Modify: `squirrel-frontend/src/views/SyncCenter.vue`
- Modify: `squirrel-frontend/src/composables/useSyncHistory.ts`
- Modify: `squirrel-frontend/src/composables/useSyncTrends.ts`

**Step 1: 新建页面级 workbench composable**

在 `useSyncCenterWorkbench.ts` 中定义单页工作台状态，至少包含：

```ts
export type SyncTimeLens = 'now' | '24h' | '7d'
export type SyncFocusKind = 'overview' | 'site' | 'failed-runs' | 'slow-runs' | 'recovery'

interface SyncWorkbenchState {
  lens: SyncTimeLens
  focus: SyncFocusKind
  site: string
  selectedRunId: string
  selectedSubscriptionId: number | null
}
```

需要暴露：

- `setLens`
- `setFocus`
- `setSite`
- `selectRun`
- `selectSubscription`
- `resetAnalysis`

要求：所有首页点击和分析层切换都通过这一处状态驱动。

**Step 2: 让历史和趋势 composable 支持外部驱动**

在 `useSyncHistory.ts` 中补显式方法，例如：

```ts
const setFilters = (patch: Partial<typeof filters>) => { ... }
const setDateRange = (dateFrom: string, dateTo: string) => { ... }
const refreshSelectedRun = async () => { ... }
```

在 `useSyncTrends.ts` 中补显式方法，例如：

```ts
const setRange = (value: string) => { ... }
const setFilters = (patch: Partial<typeof filters>) => { ... }
```

要求：`SyncCenter.vue` 可以统一控制时间透镜、站点条件和刷新行为，不再由旧 tab 各自维护一套入口状态。

**Step 3: 把 `SyncCenter.vue` 改成单页骨架**

删除 `activeTab`、`history/trends` 平权切换逻辑，改成单页结构：

```vue
<SyncControlBar />
<SyncSignalMatrix />
<SyncFocusBoard />
<SyncAnalysisWorkspace />
<SyncRunDetailDrawer />
<SyncDetailDrawer />
```

要求：

- 首屏默认同时加载 overview、history、trends 所需数据
- 保留现有 `retry`、`reconcile`、`refresh` 行为
- 抽屉打开状态由 workbench 的选中对象统一驱动

**Step 4: 运行类型检查**

Run:

```powershell
Set-Location 'D:\Code\init\squirrel\squirrel-frontend'
npm run typecheck
```

Expected: `vue-tsc --noEmit` 通过

**Step 5: Commit**

```powershell
git add squirrel-frontend/src/composables/useSyncCenterWorkbench.ts squirrel-frontend/src/views/SyncCenter.vue squirrel-frontend/src/composables/useSyncHistory.ts squirrel-frontend/src/composables/useSyncTrends.ts
git commit -m "refactor: turn sync center into a single workbench"
```

### Task 2: 实现高密度首屏态势层和焦点层

**Files:**
- Create: `squirrel-frontend/src/components/sync-center/SyncControlBar.vue`
- Create: `squirrel-frontend/src/components/sync-center/SyncSignalMatrix.vue`
- Create: `squirrel-frontend/src/components/sync-center/SyncFocusBoard.vue`
- Modify: `squirrel-frontend/src/views/SyncCenter.vue`

**Step 1: 实现紧凑控制栏**

`SyncControlBar.vue` 至少接收以下 props：

```ts
defineProps<{
  summary: string
  lens: SyncTimeLens
  autoRefresh: boolean
  refreshing: boolean
  reconciling: boolean
  lastUpdatedAt: string
}>()
```

需要提供：

- 时间透镜切换
- 自动刷新开关
- 手动刷新
- 状态对账

要求：一行完成，不写长说明，不做大标题区。

**Step 2: 实现首屏信号矩阵**

`SyncSignalMatrix.vue` 拆成两组紧凑指标：

- 当前态势：运行中、排队中、失败、延后、队列压力、待处理视频
- 最近变化：成功率、失败运行、最新 P95、恢复次数、波动站点数

建议 props 形状：

```ts
interface SyncSignalItem {
  key: string
  label: string
  value: string | number
  tone: 'neutral' | 'info' | 'warning' | 'error' | 'success'
  delta?: string
}
```

要求：用矩阵和状态条表达，不沿用旧的大卡片排版。

**Step 3: 实现焦点板**

`SyncFocusBoard.vue` 展示四组入口：

- 异常站点
- 失败批次
- 高延迟批次
- 恢复摘要

数据来源约束：

- 异常站点：`trendSiteBreakdown`
- 失败批次：`historyRuns` 中的失败项
- 高延迟批次：`historyRuns` 按 `duration_ms` 排序
- 恢复摘要：`recoverySummary`

要求：默认就是紧凑列表，不写解释性段落；点击后通过 workbench 进入分析层。

**Step 4: 接回 `SyncCenter.vue`**

在页面内补齐这些计算数据：

- 全局摘要文案
- 当前态势矩阵 items
- 最近变化矩阵 items
- 四组焦点列表

要求：所有点击都转成 `setFocus`、`setSite`、`selectRun`，不能直接回退成旧 tab 跳转。

**Step 5: 运行类型检查**

Run:

```powershell
Set-Location 'D:\Code\init\squirrel\squirrel-frontend'
npm run typecheck
```

Expected: 通过

**Step 6: Commit**

```powershell
git add squirrel-frontend/src/components/sync-center/SyncControlBar.vue squirrel-frontend/src/components/sync-center/SyncSignalMatrix.vue squirrel-frontend/src/components/sync-center/SyncFocusBoard.vue squirrel-frontend/src/views/SyncCenter.vue
git commit -m "feat: add dense sync center dashboard surfaces"
```

### Task 3: 把历史、趋势、订阅影响面收敛到分析工作区

**Files:**
- Create: `squirrel-frontend/src/components/sync-center/SyncAnalysisWorkspace.vue`
- Modify: `squirrel-frontend/src/components/sync-center/SyncRunHistoryPanel.vue`
- Modify: `squirrel-frontend/src/components/sync-center/SyncTrendCharts.vue`
- Modify: `squirrel-frontend/src/components/sync-center/SyncItemsPanel.vue`
- Modify: `squirrel-frontend/src/views/SyncCenter.vue`

**Step 1: 新建分析工作区骨架**

`SyncAnalysisWorkspace.vue` 负责固定三栏布局：

- 左侧对象流
- 中间运行/趋势切片
- 右侧详情摘要

建议 props：

```ts
defineProps<{
  focus: SyncFocusKind
  site: string
  runs: SyncRunItem[]
  trendSeries: SyncTrendPoint[]
  siteBreakdown: SyncTrendSiteBreakdown[]
  items: SyncCenterItem[]
  selectedRunId: string
  selectedSubscriptionId: number | null
}>()
```

**Step 2: 给历史、趋势、订阅列表增加嵌入模式**

分别给这三个组件加 `compact` 或 `embedded` 入口，要求：

- `SyncRunHistoryPanel.vue` 在嵌入模式下隐藏旧的整页标题和多余筛选头
- `SyncTrendCharts.vue` 在嵌入模式下优先展示趋势切片和站点摘要，不先展示大表格
- `SyncItemsPanel.vue` 在嵌入模式下去掉“首页主列表”语义，改成订阅影响面列表

不要再把它们当独立 tab 页面内容。

**Step 3: 建立四种分析视图**

在 `SyncAnalysisWorkspace.vue` 中按 focus 分支：

- `site`：站点剖面 + 关联运行
- `failed-runs`：失败运行流 + 相关订阅影响面
- `slow-runs`：慢运行流 + 趋势切片
- `recovery`：恢复摘要 + 相关运行与订阅影响面

要求：所有视图都能继续选中 run 或订阅，不出现分析断层。

**Step 4: 在 `SyncCenter.vue` 中接入工作区**

要求：

- 首页焦点点击后展开工作区
- 工作区和顶部时间透镜共享同一套筛选上下文
- 分析层默认优先展示与焦点匹配的对象，不手动切回旧视图

**Step 5: 运行类型检查**

Run:

```powershell
Set-Location 'D:\Code\init\squirrel\squirrel-frontend'
npm run typecheck
```

Expected: 通过

**Step 6: Commit**

```powershell
git add squirrel-frontend/src/components/sync-center/SyncAnalysisWorkspace.vue squirrel-frontend/src/components/sync-center/SyncRunHistoryPanel.vue squirrel-frontend/src/components/sync-center/SyncTrendCharts.vue squirrel-frontend/src/components/sync-center/SyncItemsPanel.vue squirrel-frontend/src/views/SyncCenter.vue
git commit -m "feat: unify sync center analysis workspace"
```

### Task 4: 压缩证据层细节并完成最终集成

**Files:**
- Modify: `squirrel-frontend/src/components/sync-center/SyncRunDetailDrawer.vue`
- Modify: `squirrel-frontend/src/components/sync-center/SyncEventTimeline.vue`
- Modify: `squirrel-frontend/src/components/sync-center/SyncDetailDrawer.vue`
- Modify: `squirrel-frontend/src/views/SyncCenter.vue`

**Step 1: 压缩 run 详情抽屉**

`SyncRunDetailDrawer.vue` 改成更高密度的证据抽屉：

- 缩小头部高度
- 把关键指标改成紧凑指标行
- 降低卡片数量
- 把 `request_id`、`trace_id`、阶段信息压成信息表

要求：它看起来是分析面板，不是大卡片详情页。

**Step 2: 压缩事件时间线**

`SyncEventTimeline.vue` 改成更适合排查的时间线：

- 时间、事件类型、阶段、状态放在同一行
- payload 默认弱化显示，不再占据过高空间
- 恢复类事件继续保留明确标签

要求：用户能快速扫完一条 run 的事件序列。

**Step 3: 压缩订阅详情抽屉**

`SyncDetailDrawer.vue` 改成订阅影响面的辅助面板：

- 保留失败次数、待处理视频、关键时间字段、错误摘要
- 压缩当前双列大卡片布局
- 保留“打开订阅”和“立即重试”

要求：它服务于分析层，不再像独立详情页。

**Step 4: 做最终联调和构建校验**

Run:

```powershell
Set-Location 'D:\Code\init\squirrel\squirrel-frontend'
npm run build:check
```

Expected: `vue-tsc --noEmit` 和 `vite build` 都通过

**Step 5: Commit**

```powershell
git add squirrel-frontend/src/components/sync-center/SyncRunDetailDrawer.vue squirrel-frontend/src/components/sync-center/SyncEventTimeline.vue squirrel-frontend/src/components/sync-center/SyncDetailDrawer.vue squirrel-frontend/src/views/SyncCenter.vue
git commit -m "refactor: tighten sync center evidence panels"
```
