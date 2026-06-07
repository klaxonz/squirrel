---
title: 架构 — Backend services/ 57 个顶层文件 + 缺少 src/ 布局 + 空白 API 契约
status: open
severity: medium
category: architecture
location: squirrel-backend/services/, squirrel-backend/（项目根目录）
---

## 问题描述

### 1. services/ 57 个顶层文件，需领域命名空间

订阅领域占 17 个 `subscription_*.py` 顶层文件；视频领域占 13 个 `video_*.py`。这些应归入 `subscription/` 和 `video/` 命名空间包，类似已存在的 `music/`（12 文件）和 `crawl_tasks/`（5 文件）。

没有一致的命名策略：部分领域已被提取为子包（music/, crawl_*），另一些仍为扁平顶层文件。

### 2. Backend 缺少 src/ 布局

其他 Python 子项目都使用 `src/` 布局（`squirrel-sdk/src/`、`squirrel-cf-bypass/src/`），但 backend 直接在根目录：
- 所有导入为裸名 `from services import video_service`（而非 `from squirrel_backend.services import video_service`）
- 无法被其他项目 `pip install -e .` 安装
- `main.py` 处于根模块级别，依赖工作路径即可工作

### 3. 主要包缺少 `__init__.py` 契约

| 包 | `__init__.py` | 问题 |
|---|---|---|
| `services/` | 空 | 64 个文件全部隐式公开，无公共 API 契约 |
| `routes/` | 空 | 同上 |
| `utils/` | 空 | 同上 |
| `schemas/` | 空 | 同上 |
| `consumer/` | 不存在 | 不是合法的 Python 包 |
| `sql/` | 不存在 | 不是合法的 Python 包 |

同时，`subscription_sync_state_service/__init__.py` 导出 40+ 符号（包括 `_` 前缀私有模块），恰好相反地过度暴露。

## 影响

- 新开发者难以找到特定领域的服务（需滚动 57 个文件）
- Backend 不可安装，无法被 CI 或测试工具作为库引用
- 无 API 契约使重构困难（无法区分公共/私有接口）

## 建议方向

1. 将 `services/` 下扁平文件按领域分组：`subscription/`, `video/`, `rss/`, `site/`，类似已有的 `music/`
2. 迁移 backend 到 `src/squirrel_backend/` 布局以匹配其他 Python 子项目
3. 给主要包添加有意义的 `__init__.py`（带 `__all__` 或至少 docstring）
4. 修复 `consumer/` 和 `sql/` 的包结构
5. `subscription_sync_state_service/__init__.py` 精简导出，隐藏内部模块
