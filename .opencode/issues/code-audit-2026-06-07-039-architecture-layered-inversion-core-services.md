---
title: 架构 — 后端分层倒置：core→services、utils→services、routes→routes
status: open
severity: high
category: architecture
location: squirrel-backend/（跨包依赖）
---

## 问题描述

理想依赖方向应为：`routes → services → core → models`（utils/common 为叶节点）

### 1. core/extraction → services（严重）

`core/extraction/services/` 下三个文件从 `services/` 导入，完全倒置了分层：

| core/ 中文件 | 导入 services/ |
|---|---|
| `video_persistence.py` | `services.subscription_video_service`, `services.user_video_feed_service` |
| `actor_processor.py` | `services.creator_service`, `services.video_creator_service` |
| `pipeline/stages/extraction.py` | `services.blocked_video_service` |

### 2. utils → services（中度）

`utils/jwt_helper.py` 从 `services.user_service`, `services.user_config_service` 导入。jwt_helper 是路由层的调用方（auth middleware），本应只依赖数据模型，却反向依赖了 services。

### 3. routes → routes（中度）

`routes/sites.py:9` 从 `routes.connectivity` 导入 `test_site_connectivity`。路由之间不应直接相互导入，应通过共享的服务层调用。

### 4. queues → services（轻度）

`queues/queue_monitor.py` 从 `services.crawl_tasks` 导入，将 MQ 基础设施耦合到特定业务。

## 影响

- `core/extraction/` 被设计为公共子系统，但依赖 services 使其无法独立复用
- `utils/jwt_helper` 的循环依赖风险导致 auth middleware 与 services 紧耦合
- 路由间导入模糊了分层边界，绕过服务层复用逻辑
- 基础设施代码耦合业务领域，违反关注点分离

## 建议方向

1. 将 `core/extraction/` 移出 core/，提升为顶层包，或通过依赖注入反转 services 依赖
2. `jwt_helper` 改为接口注入方式（调用方传入 user_service 依赖），或拆分 token 编解码与用户查询
3. `routes/sites.py` 改为调用服务层共享方法
4. `queue_monitor.py` 改为通过抽象接口引用业务，而非直接导入
