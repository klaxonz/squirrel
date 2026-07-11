---
name: Squirrel Design System
description: UI design standards for Squirrel (归仓) — Surface, color, states, visual system
source_of_truth:
  standards: docs/design/principles.md
  product: ../../README.md
  foundations: src/shared/styles/layout.css, src/shared/styles/themes/dark.css
  components: src/shared/ui/**
  patterns: src/shared/components/layout/**
  docs: docs/design/**
---

# Squirrel Design System

**必须执行的界面规格。** 实现与评审以标准条款为准；冲突时先让代码与文档对齐，再合入。

| 文档 | 管什么 |
|------|--------|
| [README](../README.md)（仓库根） | **产品**：是什么、主链、怎么部署 |
| 本文 + [Standards](./docs/design/principles.md) | **设计**：界面必须用什么规格做 |

结构：**Standards → Foundations → Components → Patterns → Content → Governance**。

## 标准入口（必读）

完整条款 → **[Standards](./docs/design/principles.md)**（S1–S4）

| 编号 | 标准 | 一句话 |
|------|------|--------|
| S1 | Surface | 每页 Consume / Organize / Operate 三选一规格 |
| S2 | 色意映射 | 意图 → 固定 token；每视图 primary ≤ 1 |
| S3 | 状态完整性 | 加载 / 空 / 错可感知且可操作 |
| S4 | 视觉系统 | 字体、圆角、网格、焦点、色温、z/motion 统一 |

产品是什么（订阅中枢 / 归仓）只作上下文，**不**在本页展开路径表。页面 → Surface 对照见 [Shell](./docs/design/patterns/shell.md)。

## 意图 → Token（S2 速查）

| 意图 | Token |
|------|-------|
| 主行动 / 播放 / 焦点环 / 徽章 | `--primary` / `--ring` |
| 导航当前 / 列表选中 / 筛选开启 | `--app-selection-*` |
| 健康 / 成功 | `--success` + 文案 |
| 警告 | `--warning` + 文案 |
| 危险 | `--destructive` |
| Consume scrim | `--background` 或 `--overlay` 的 alpha |

细则 → [Color](./docs/design/foundations/color.md)

## 源

| 层 | 管什么 | 代码 | 文档 |
|----|--------|------|------|
| Standards | 必须执行的条款与验收 | — | [principles.md](./docs/design/principles.md) |
| Foundations | 色、字、间距、层级、动效 | `layout.css` / `themes/dark.css` | [foundations/](./docs/design/foundations/) |
| Components | 单控件 | `shared/ui/**` | [components/](./docs/design/components/) |
| Patterns | 多控件组合 | `shared/components/layout/**` | [patterns/](./docs/design/patterns/) |
| Content / A11y | 文案、无障碍 | — | [content](./docs/design/content.md) · [a11y](./docs/design/accessibility.md) |
| Governance | 如何扩展与合入 | — | [governance](./docs/design/governance.md) |

## 导航

| 页 | 内容 |
|----|------|
| [Standards](./docs/design/principles.md) | S1–S4 与验收清单 |
| [决策表](./docs/design/decisions.md) | 意图 → 标准实现 |
| [Shell](./docs/design/patterns/shell.md) | 壳结构与页面 → Surface |
| [Color](./docs/design/foundations/color.md) | 色意映射全文 |
| [Typography](./docs/design/foundations/typography.md) | 字体与字阶 |
| [Spacing](./docs/design/foundations/spacing.md) | 间距、圆角、密度 |
| [Elevation](./docs/design/foundations/elevation.md) | 阴影、z-index、单画布 |
| [Motion](./docs/design/foundations/motion.md) | 时长与 easing |
| [Components](./docs/design/components/README.md) | 按钮、表单、导航、浮层… |
| [Patterns](./docs/design/patterns/README.md) | 壳、筛选、网格、卡片、状态 |
| [Token 地图](./docs/design/tokens.md) | token → 文件速查 |
