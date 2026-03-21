# 同步中心设计

## 目标

为订阅同步提供一个独立工作台，统一展示失败订阅、运行中任务、排队状态、即将执行项和队列积压，减少“监控页、订阅页、悬浮同步面板”之间来回跳转的排查成本。

## 设计范围

- 新增独立页面 `同步中心`
- 保留现有 `系统监控` 页面，继续承担系统健康度和指标看板职责
- 保留现有悬浮 `RefreshCenter`，继续承担轻量实时提醒职责
- 新增订阅域同步中心接口，不直接继续堆叠 `/api/metrics/dashboard`

## 核心原则

- 先解决失败排障，再解决全局可见性
- 复用现有 `subscription_sync_state` 和监控指标，不新增第二套状态来源
- 第一版只做查询、筛选、详情和重试，不引入实时推送和历史事件表
- 页面语义使用业务状态，不让前端拼接底层字段组合

## 信息架构

### 第一屏

顶部总览卡片展示：

- 运行中
- 排队中
- 失败待处理
- 即将执行
- 队列积压

卡片点击后直接联动下方主列表筛选。

### 主体布局

桌面端采用左右布局，移动端上下堆叠。

- 左侧主工作区：失败、运行中、排队中、即将执行、最近活动列表
- 右侧状态面板：当前运行中摘要、队列概览摘要

### 详情层

列表项点击后打开详情抽屉，展示：

- 订阅基础信息
- 当前同步状态
- 时间字段
- 待处理视频数
- 完整错误信息
- 可执行动作

## 后端数据设计

### 数据来源

订阅级状态来源于 `subscription_sync_state`：

- `sync_mode`
- `sync_status`
- `last_sync_at`
- `last_success_at`
- `next_sync_at`
- `queued_at`
- `locked_at`
- `pending_video_count`
- `failure_count`
- `last_error`

全局队列与概览来源于现有 `/api/metrics/dashboard` 聚合逻辑中的：

- `queues.total_depth`
- `queues.total_messages`
- 站点维度队列统计

### 接口建议

- `GET /api/subscription/sync-center/overview`
- `GET /api/subscription/sync-center/items`
- `POST /api/subscription/sync-center/retry-failed`

单订阅重试继续复用：

- `POST /api/subscription/{subscription_id}/refresh`

### 列表项字段

- `subscription_id`
- `subscription_name`
- `subscription_avatar`
- `site`
- `sync_mode`
- `sync_status`
- `display_status`
- `failure_count`
- `last_error`
- `last_error_summary`
- `last_sync_at`
- `last_success_at`
- `next_sync_at`
- `queued_at`
- `locked_at`
- `pending_video_count`
- `is_deferred`
- `defer_reason`

## 状态语义

- `failed`：最近一次同步失败，且当前不在运行或排队
- `running`：已被消费者领取，正在执行
- `queued`：已入队等待消费
- `scheduled`：当前状态正常，但即将在计划时间执行
- `deferred`：由于背压等原因延后执行
- `healthy`：用于详情辅助说明，不作为主筛选标签

其中 `display_status` 由后端统一判定，前端不自行推导。

## 错误展示

- 列表展示错误摘要 `last_error_summary`
- 详情抽屉展示完整 `last_error`

摘要在接口层归一化，不额外持久化。

## 前端页面设计

### 路由与导航

- 新增页面路由：`/sync-center`
- 在桌面侧边栏和移动端导航中增加 `同步中心`

### 页面结构

- 顶部工具栏：刷新、自动刷新、批量重试失败项
- 筛选区：状态、站点、搜索
- 总览卡片区：5 张状态卡
- 主列表区：失败、运行中、排队中、即将执行、最近活动
- 详情抽屉：状态详情和动作入口

### 与现有 RefreshCenter 的关系

悬浮 `RefreshCenter` 继续负责轻量实时提醒，新页面负责集中管理和排障，不替代悬浮提醒。

## 第一版实施边界

包含：

- 新增同步中心查询接口
- 新增批量重试失败项接口
- 新增同步中心前端页面与导航入口
- 基于轮询的页面刷新

不包含：

- WebSocket 或 SSE
- 执行历史事件表
- 趋势图表
- 取消排队、调整优先级
- 多级详情页

## 风险与取舍

- 当前没有独立同步历史表，`最近活动` 只能基于当前状态时间字段排序，适合第一版排障，不适合审计
- 现有悬浮同步面板和新页面存在命名重叠，需要在文案上区分“悬浮同步提醒”和“同步中心页面”
- 批量重试必须限制在当前失败集合，避免误触发全量刷新
