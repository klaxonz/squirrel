# 同步中心 V2 设计

## 目标

将同步中心从“当前状态工作台”升级为“完整运行分析台”，新增完整执行历史、趋势分析和更细粒度的阶段面板，同时保证首页查询不依赖运行时聚合事件流。

## 设计结论

V2 采用纯事件溯源作为事实来源，但不直接用事件表支撑页面查询。整体架构为：

- `subscription_sync_event`：唯一事实来源
- projection/read model：给首页、历史页、趋势图使用的投影视图
- projector：在事件写入后同步更新 projection
- 现有 `subscription_sync_state` 继续承担调度、锁和下一次执行时间等职责

## 核心原则

- 所有关键同步过程都落成事件，不再只保留最终结果
- 页面查询只读 projection，不在请求时回放事件流
- V2 在现有 V1 同步中心上增量演进，不替换现有调度链路
- 阶段模型和统计口径先统一再扩展，避免后期图表和时间线口径混乱

## 数据模型

### 1. 事件表

表名建议：`subscription_sync_event`

字段建议：

- `id`
- `stream_id`
- `subscription_id`
- `sync_state_id`
- `site`
- `sync_mode`
- `trigger`
- `request_id`
- `trace_id`
- `event_type`
- `event_phase`
- `event_status`
- `seq_no`
- `occurred_at`
- `payload`
- `created_at`

说明：

- `stream_id` 代表一次同步运行实例
- `seq_no` 代表该实例内事件顺序
- `payload` 存放错误详情、阶段统计、视频计数、cursor、queue token 等上下文

### 2. 运行实例投影

表名建议：`subscription_sync_run_projection`

一行代表一次运行实例的当前快照。

字段建议：

- `run_id`
- `subscription_id`
- `sync_state_id`
- `site`
- `sync_mode`
- `trigger`
- `request_id`
- `trace_id`
- `status`
- `current_phase`
- `queued_at`
- `started_at`
- `finished_at`
- `duration_ms`
- `failure_count`
- `error_type`
- `error_message`
- `videos_found`
- `videos_enqueued`
- `videos_extracted`
- `videos_skipped`
- `pending_video_count`
- `last_event_at`
- `created_at`
- `updated_at`

### 3. 订阅状态投影

表名建议：`subscription_sync_subscription_projection`

一行代表某个订阅的当前同步视图。

字段建议：

- `subscription_id`
- `latest_run_id`
- `current_status`
- `current_phase`
- `last_sync_at`
- `last_success_at`
- `next_sync_at`
- `last_error_message`
- `pending_video_count`
- `failure_streak`
- `updated_at`

### 4. 趋势投影

表名建议：`subscription_sync_trend_projection`

按时间桶聚合。

字段建议：

- `bucket_time`
- `site`
- `sync_mode`
- `trigger`
- `runs_total`
- `runs_success`
- `runs_failed`
- `runs_deferred`
- `videos_found`
- `videos_enqueued`
- `videos_extracted`
- `avg_duration_ms`
- `p95_duration_ms`
- `updated_at`

## 运行实例定义

一次同步运行实例从“决定入队”开始，到“完成 / 失败 / 延后 / 超时回收”结束。

约定：

- 在 `scheduler.schedule_one(...)` 决定真正创建本次同步时生成 `run_id`
- 同一个 `run_id` 贯穿排队、claim、阶段推进、统计变化和结束态
- `request_id` 保持请求粒度
- `trace_id` 保持链路粒度

## 事件类型

建议至少支持：

- `run_created`
- `queued`
- `claimed`
- `started`
- `phase_changed`
- `progress_updated`
- `video_found`
- `video_enqueued`
- `video_extracted`
- `video_skipped`
- `deferred`
- `failed`
- `completed`
- `timeout_recovered`

## 阶段模型

建议固定阶段枚举：

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

规则：

- `event_type` 表示发生了什么
- `event_phase` 表示当时所处阶段

## 写入时机

### 调度阶段

在 `scheduler.schedule_one(...)`：

- 写 `run_created`
- 成功排队写 `queued`
- 因 `site_disabled / no_subscribers / deferred` 未入队时也写事件

### 消费阶段

在 `claim_sync_state(...)`：

- 写 `claimed`

### 编排与策略阶段

在 orchestrator / strategy：

- 写 `started`
- 每次阶段切换写 `phase_changed`
- 发现视频写 `video_found`
- 入队视频写 `video_enqueued`
- 跳过视频写 `video_skipped`

### 结束阶段

在 `mark_sync_success(...)`：

- 写 `completed`

在 `mark_sync_failed(...)`：

- 写 `failed`

在 `recover_stale_sync_state(...)`：

- 写 `timeout_recovered`

## Projector 策略

V2 初期采用同步投影。

即：

- 事件写入后，立即调用 projector 更新 projection
- 页面优先读取 projection
- 后续若事件量增大，再考虑拆成异步 projector

## 页面结构

V2 同步中心建议拆成三个主 tab：

### 1. 概览

保留 V1 首页，增强：

- 更细的运行中状态面板
- 更细的排队状态面板
- 当前阶段摘要
- 失败热区

### 2. 运行历史

列表支持：

- 状态筛选
- 站点筛选
- 模式筛选
- 触发来源筛选
- 时间范围筛选

详情展示：

- 运行摘要
- 阶段时间线
- 原始事件流
- 错误与 payload

### 3. 趋势分析

建议先固定 4 组图：

- 运行结果趋势
- 视频吞吐趋势
- 时延趋势
- 站点分布趋势

时间范围建议：

- 24 小时按小时
- 7 天按天
- 30 天按天

## 趋势图口径

建议统一如下：

- `runs_total`
- `runs_success`
- `runs_failed`
- `runs_deferred`
- `videos_found`
- `videos_enqueued`
- `videos_extracted`
- `videos_skipped`
- `avg_duration_ms`
- `p95_duration_ms`

## 迁移策略

V2 采用增量迁移，不替换 V1：

1. 新增事件表和 projection 表
2. 在现有调度 / 同步链路中补事件写入
3. 增量更新 projection
4. 新增历史与趋势接口
5. 前端新增历史与趋势视图
6. 再视情况将更多首页数据切到 projection

## 主要改造点

后端重点：

- `services/subscription_update/scheduler.py`
- `services/subscription_sync_state_service.py`
- `services/subscription_update/orchestrator.py`
- `services/subscription_update/strategies/default_strategy.py`
- 新增事件写入服务
- 新增 projection 服务
- 新增历史和趋势接口

前端重点：

- `src/views/SyncCenter.vue`
- 新增历史视图
- 新增趋势视图
- 拆分 composable 为 overview / history / trends

## 非目标

V2 暂不包含：

- 事件重放修复工具
- 导出审计报表
- 实时图表推送
- 自定义事件 DSL
