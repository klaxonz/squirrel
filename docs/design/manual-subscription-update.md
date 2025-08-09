# 手动发起订阅源更新（Manual Subscription Refresh）设计文档

## 背景与目标
- 现状：订阅更新由定时任务批量投递到 `subscription_update_queue`，消费者执行 `SubscriptionUpdateService.update_subscription_videos`，且已有分布式锁，避免并发冲突。
- 目标：支持“手动对单一订阅源发起更新”，并在端到端链路中保持更高优先级，避免与定时任务相互阻塞；提供可观测的进度反馈；保持前端交互与 UI 一致性。

## 范围
- 后端：新增手动更新队列与 API、完善进度跟踪、授权/限流/幂等/并发安全。
- 前端：在订阅列表/详情提供统一入口与状态展示；对齐现有视觉与交互规范；支持进度反馈与错误提示。

## 队列与优先级设计
为确保“手动触发”在端到端链路中的优先级高于“定时任务”，将“订阅更新”和“视频解析”均拆分出手动专用队列。

- 新增常量（建议）：
  - `constants.QUEUE_SUBSCRIPTION_UPDATE_MANUAL = 'subscription_update_manual_queue'`
  - `constants.QUEUE_VIDEO_EXTRACT_MANUAL = 'video_extract_manual_queue'`
  - 如需站点隔离：`video_extract_{site}_manual_queue` （需要站点隔离）

- 消费者：
  - 订阅更新（manual）：复用 `process_subscription_update` 的业务逻辑（或轻度包装增加 `source=manual`），注册到 `subscription_update_manual_queue`。
  - 视频解析（manual）：复用现有解析处理器（或统一处理器按队列名/消息 `source` 区分），注册到 `video_extract_manual_queue`（或站点队列）。

- 端到端链路：
  - 手动：`subscription_update_manual_queue → (产出) video_extract_manual_queue`
  - 定时：`subscription_update_queue → (产出) video_extract_queue`

## 后端 API 设计
1) 触发更新（手动）
- `POST /api/subscription/{id}/refresh`
- 行为：将指定订阅加入手动更新队列。
- 授权：仅允许已订阅该频道的用户（`UserSubscription` 未删除）或具备相应角色的用户。
- 幂等：若该订阅已有更新在进行（分布式锁 `lock:subscription:update:{id}`），返回 `202 Accepted`，`status=in_progress`。
- 速率限制：按用户与订阅粒度限流（例如同一订阅 60s 触发不超过一次；用户全局每分钟不超过 N 次）。
- 响应：
  ```json
  { "status": "queued", "requestId": "...", "inProgress": false }
  ```
  或
  ```json
  { "status": "in_progress", "requestId": "...", "inProgress": true }
  ```

2) 查询进度
- `GET /api/subscription/{id}/refresh/status`
- 响应示例：
  ```json
  {
    "status": "in_progress",              // queued | in_progress | completed | failed
    "phase": "extracting",                 // init | fetching_feed | calculating_delta | extracting | finalizing
    "processed": 12,
    "total": 37,
    "source": "manual",                    // manual | scheduled
    "startedAt": "2025-08-09T10:00:00Z",
    "updatedAt": "2025-08-09T10:02:33Z",
    "finishedAt": null,
    "requestId": "...",
    "lastError": null
  }
  ```

（可选）取消更新：预留 `POST /api/subscription/{id}/refresh/cancel`，如后续支持可实现。

## 进度跟踪设计
- 存储：Redis（推荐）或表。Key 建议：`subscription:update:progress:{subscription_id}`。
- 字段：
  - `status`: queued | in_progress | completed | failed
  - `phase`: init | fetching_feed | calculating_delta | extracting | finalizing
  - `processed`, `total`
  - `source`（manual/scheduled），`requestId`
  - `startedAt`, `updatedAt`, `finishedAt`
  - `lastError`
- 写入时机：
  - 入队：`status=queued`
  - 获取锁：`status=in_progress, phase=init`
  - 拉取列表：`phase=fetching_feed`（完成后写入 `total`）
  - 解析阶段：`phase=extracting`，解析完成或计划解析成功的条目使 `processed++`
  - 完成：`phase=finalizing, status=completed`
  - 异常：`status=failed, lastError=...`
- 清理：completed/failed 进度设置过期（如 24h）。
- 与视频级进度的关系：
  - 解析消费者在完成/失败时，通过轻量写入回报 `processed++`（按 `subscription_id` 聚合），无需前端汇总所有视频的细粒度状态。

## 前端交互与 UI 一致性
- 入口：
  - 订阅列表卡片“更多操作”添加“更新”项。
  - 订阅详情页提供显著“更新”按钮。
- 状态与反馈：
  - 触发后立即切换按钮为 loading/禁用态；Toast “已加入更新队列”。
  - 若正在更新中，Toast “更新进行中”。
  - 失败显示错误摘要与“重试”按钮（带节流）。
- 进度展示：
  - 列表卡片：小徽标显示 “更新中 x/y”。
  - 详情页：显示进度条、阶段标签、起止时间等。
- 刷新策略：
  - 轮询 `GET /api/subscription/{id}/refresh/status`，每 2–5s。
  - 后续可演进至 SSE/WebSocket（项目中已有 SSE 用例可参考）。
- 一致性：
  - 图标采用现有库（如 `material-symbols:refresh`）。
  - 按钮尺寸/色彩/禁用与 Hover 状态对齐项目样式体系。
  - 点击节流（如 3s 内重复点击直接短路）。

## 并发安全与幂等
- 同一订阅互斥（强约束）：任一更新（手动/定时）开始时获取分布式锁 `lock:subscription:update:{id}`；同一时刻同一订阅仅允许一个更新在执行。
  - 手动触发：若锁被定时占用，API 返回 `202 Accepted` 且 `status=in_progress`，前端展示“更新进行中”。
  - 定时触发：若锁被手动占用，消费者拿不到锁则跳过或延迟重试，不阻塞队列。
- 可选优化（减少无效争抢）：`manual_pending` 标记，`subscription:update:manual_pending:{id}`（短 TTL 如 120s）。
  - 手动触发设置该标记；定时消费者在尝试加锁前先检查，存在则跳过或重入队；完成/失败时清理或等待 TTL 到期。
- 解析阶段避免冲突：手动/定时解析任务分别进入各自解析队列；继续依赖视频维度的“已存在/进行中”去重，避免同一视频重复解析。
- 幂等：正在更新 → 返回 `in_progress`，不重复入队。
- 访问控制：仅允许拥有该订阅的用户触发（或由角色权限控制）。

## 可观测性与运维
- 日志：统一打印 `source`（manual/scheduled）、`requestId`、`subscription_id`、阶段耗时与失败原因。
- 指标：
  - 手动与定时的成功率、平均等待时间、执行耗时分布、队列长度。
  - 解析成功/失败比、重试次数分布。
- 告警：
  - manual 队列积压超过阈值。
  - 连续失败次数超阈。

## 配置建议（初始值，可按环境调整）
- 并发：不做配比要求；为手动与定时分别提供独立消费者（即使各自仅 1 并发也可并行处理不同订阅）。如需优化手动延迟，可按需提高手动侧并发数。
- 限流：同一订阅 60s 只允许手动触发一次；用户全局每分钟 <= 5 次。
- 进度过期：24h。

## 开放问题
- 是否按站点拆分手动解析队列（`video_extract_{site}_manual_queue`）？若拆分，需配齐 per-site 并发配额与限流。
- 普通用户与管理员在限流与可见信息上是否差异化？
- 是否需要对“已最新”场景做快速返回（无需入队）？

## 实施计划（概览）
1) 后端
   - 新增常量与队列注册（manual 队列）。
   - 新增 `POST /api/subscription/{id}/refresh`、`GET /api/subscription/{id}/refresh/status`。
   - 订阅更新与解析处理器支持 manual 队列，并在关键节点写入进度。
   - 限流、授权、幂等与锁校验；日志与指标补充。
2) 前端
   - 列表与详情页入口接入；按钮状态与 Toast。
   - 进度 UI 与轮询逻辑；错误与重试。
   - 与现有样式与图标系统一致。
3) 运维
   - 为 manual 队列配置独立消费者与并发；仪表盘/告警项。

## 验收标准
- 手动触发在 1s 内入队并返回结果。
- 在常见负载下，manual 任务平均启动时间显著优于 scheduled。
- 进度状态在前端可见，阶段与数值更新准确；失败可见并可重试。
- 对并发触发、重复触发、限流命中与异常情况有清晰反馈与日志。
