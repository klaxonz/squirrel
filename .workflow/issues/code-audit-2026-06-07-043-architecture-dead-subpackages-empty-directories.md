---
title: 架构 — 多处废弃子包 + 空目录 + 搁置抽象
status: fixed
fixed_by: squirrel-backend/core/ (目录结构), squirrel-backend/consumer/__init__.py, squirrel-backend/sql/__init__.py
severity: low
category: dead-code
location: squirrel-backend/core/（跨文件）
---

## 问题描述

### 1. 废弃子包/空目录

| 路径 | 内容 | 状态 |
|---|---|---|
| `core/exceptions/` | 空 `__init__.py`，无模块 | 废弃包裹 |
| `core/repository/` | 仅有 `BaseRepository`，零实现 | 搁置抽象 |
| `models/task/` | 空目录 | 废弃占位 |
| `common/types/` | 空目录 | 废弃占位 |
| `frontend/src/plugins/` | 空目录 | 废弃 |

### 2. 名称不一致的消费者包

`consumer/` 缺少 `__init__.py`（不是合法包），`sql/` 缺少 `__init__.py`，包含原始 SQL 字符串模块，与主流 ORM 模式不一致

### 3. 进程目录有崩溃残留文件

`processes/` 目录有 10 个 `.tmp` 文件（crash 残留），应清理

## 影响

- 废弃子包误导新开发者以为有现成抽象可用
- 空目录增加项目杂乱感
- 残缺包可能通过 Alembic 或扫描无意中被发现

## 建议方向

1. 确认 `core/exceptions/` 是否需删除，或将提取异常移至此处
2. `core/repository/` 如有计划则实现，否则标注废弃
3. 删除 `models/task/`、`common/types/`、`frontend/src/plugins/` 空目录
4. `consumer/` 和 `sql/` 添加 `__init__.py` 或按规范重组
5. 清理 `processes/*.tmp` 崩溃残留
