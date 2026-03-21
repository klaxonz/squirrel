# 同步中心统一口径与恢复工具化设计

## 目标

在现有同步中心 V2 基础上，统一首页、历史、趋势的状态口径，并把状态恢复能力做成同步中心内可见、可解释、可手动触发的能力，减少“旧状态残留”和“页面口径不一致”。

## 范围

本轮不扩展新的大页面结构，只聚焦两件事：

- 统一展示口径
- 恢复能力工具化

## 设计结论

### 1. 状态来源统一

同步中心不再把 `subscription_sync_state` 直接作为前端展示主来源。

统一规则：

- `subscription_sync_state`
  仅负责调度、锁、下一次执行时间、恢复判断
- `subscription_sync_subscription_projection`
  负责首页概览与订阅当前状态
- `subscription_sync_run_projection`
  负责运行列表、运行中、排队中、最近失败、最近成功
- `subscription_sync_event`
  负责时间线与审计
- `subscription_sync_trend_projection`
  负责趋势图

### 2. 恢复能力工具化

恢复逻辑不再只静默发生在后台任务里，而是要能被同步中心解释和触发。

至少补齐：

- 最近一次恢复摘要
- 恢复事件写入事件流
- 手动触发状态对账接口
- 恢复原因分类

## 统一后的页面口径

### 概览页

概览页所有卡片和右侧面板统一读 projection：

- 运行中：`run_projection.status = running`
- 排队中：`run_projection.status = queued`
- 最近失败：`run_projection.status = failed`
- 最近成功：`run_projection.status = success`
- 当前订阅状态：`subscription_projection.current_status`

不再用 `subscription_sync_state.sync_status` 直接驱动页面。

### 历史页

维持：

- 列表读 `run_projection`
- 详情读 `run_projection + event`

### 趋势页

维持：

- 趋势读 `trend_projection`

## 恢复事件

新增或规范以下事件类型：

- `stale_queued_recovered`
- `stale_running_recovered`
- `queue_state_mismatch_recovered`
- `manual_reconcile_triggered`

这些事件必须写入 `subscription_sync_event`，并同步更新对应 projection。

## 恢复摘要

建议新增一个轻量 projection 或统计接口，提供：

- `last_reconcile_at`
- `stale_queued_recovered_count`
- `stale_running_recovered_count`
- `queue_state_mismatch_count`

这组数据用于首页顶部的小状态卡或摘要条。

## 手动触发接口

建议新增：

- `POST /api/subscription/sync-center/reconcile`

返回：

- 扫描到的 `queued/running` 状态数
- 实际恢复数
- 分类统计
- 执行时间

## 恢复分类

建议统一恢复原因常量：

- `stale_queued_missing_message`
- `stale_running_timeout`
- `queue_state_mismatch`

页面展示时按更友好的文案映射。

## 页面交互

### 概览页

新增一个恢复状态面板，展示：

- 最近一次恢复时间
- 最近一次恢复数量
- 手动执行状态对账按钮

### 历史页

在事件时间线中明确显示：

- 这是正常完成
- 这是失败
- 这是系统恢复改写

### 趋势页

可选增加一组恢复趋势：

- 每小时/每天恢复次数

但如果本轮范围要控制，可以先不加图，只在事件和摘要中体现。

## 实施边界

包含：

- 首页切换到 projection 主读
- 恢复接口
- 恢复事件落库
- 恢复摘要展示

不包含：

- 新的独立运维后台
- 多租户恢复审计导出
- 自动补偿重试策略

## 风险

- 首页从 `subscription_sync_state` 切到 projection 后，必须确保 projection 刷新足够实时
- 恢复接口如果直接改状态但不写事件，会再次造成口径分裂
- 手动恢复操作需要有明确用户反馈，避免用户误以为没生效
