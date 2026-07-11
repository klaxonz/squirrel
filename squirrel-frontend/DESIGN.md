---
name: Squirrel Design System
description: Principles, mandatory standards, foundations, components, patterns
source_of_truth:
  principles: docs/design/principles.md
  standards: docs/design/standards.md
  product: ../../README.md
  foundations: src/shared/styles/layout.css, src/shared/styles/themes/dark.css
  components: src/shared/ui/**
  patterns: src/shared/components/layout/**
  docs: docs/design/**
---

# Squirrel Design System

实现与评审以文档 + 代码为准；冲突时先对齐再合入。

| 文档 | 管什么 |
|------|--------|
| [README](../README.md)（仓库根） | **产品** |
| [Principles](./docs/design/principles.md) | **原则**（两难取舍） |
| [Standards](./docs/design/standards.md) | **强制规格** + 验收 |
| Foundations → Components → Patterns | **怎么做** |

## 原则（P1–P5）

| | |
|--|--|
| P1 | 内容与真实状态优先 |
| P2 | 同一意图，同一视觉语言 |
| P3 | 系统先于特例 |
| P4 | 状态闭环 |
| P5 | 一致即可预期 |

全文 → [principles.md](./docs/design/principles.md)

## 强制规格（Spec 1–4）

| | |
|--|--|
| Spec 1 | Surface：Consume / Organize / Operate |
| Spec 2 | 色意映射（意图 → token） |
| Spec 3 | 状态完整性 |
| Spec 4 | 视觉系统一致性 |

全文 → [standards.md](./docs/design/standards.md)  
Surface 明细 → [patterns/surface.md](./docs/design/patterns/surface.md)  
Consume 品质 → [patterns/media-craft.md](./docs/design/patterns/media-craft.md)

## 意图 → Token（Spec 2 速查）

| 意图 | Token |
|------|-------|
| 主行动 / 播放 / 焦点环 | `--primary` / `--ring` |
| 选中 / 列表当前 / 筛选触发器开 | `--app-selection-*` |
| 筛选面板内 segment / tile 当前 | `--app-filter-raised-*` |
| 成功 | `--success` + 文案 |
| 警告 | `--warning` + 文案 |
| 危险 | `--destructive` |
| Consume scrim | `--background` / `--overlay` 的 alpha |

## 结构导航

| 页 | 内容 |
|----|------|
| [Principles](./docs/design/principles.md) | P1–P5 |
| [Standards](./docs/design/standards.md) | Spec 1–4 |
| [决策表](./docs/design/decisions.md) | 意图 → 实现 |
| [Foundations](./docs/design/foundations/) | 色字间距层级动效 · token 分层 |
| [Components](./docs/design/components/) | 单控件 |
| [Patterns](./docs/design/patterns/) | Surface、**Media craft**、壳、筛选、网格、状态 |
| [Content](./docs/design/content.md) / [A11y](./docs/design/accessibility.md) | 文案与无障碍 |
| [Governance](./docs/design/governance.md) | 扩展、新增三步、阻断 |
| [Token 地图](./docs/design/tokens.md) | token → 文件 |
