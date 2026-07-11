---
name: Squirrel Design System
description: Self-hosted multi-site video subscription hub (归仓) — mandatory design standards
source_of_truth:
  standards: docs/design/principles.md
  product: ../../README.md
  foundations: src/shared/styles/layout.css, src/shared/styles/themes/dark.css
  components: src/shared/ui/**
  patterns: src/shared/components/layout/**
  docs: docs/design/**
---

# Squirrel Design System

**必须执行的规格。** 实现与评审以标准条款为准；冲突时先让代码与文档对齐，再合入。

产品身份与仓库根目录 [README](../README.md) 一致：自托管多站视频订阅中枢（归仓）。

结构：**Standards → Foundations → Components → Patterns → Content → Governance**。  
详细条款在 [`docs/design/`](./docs/design/)。

## 标准入口（必读）

完整五条 → **[Standards](./docs/design/principles.md)**（S1–S5）

| 编号 | 标准 | 一句话 |
|------|------|--------|
| S1 | 产品身份 | 归仓：订阅 → 同步入库 → 浏览/处理 → 播放；站点/任务/日志为支撑 |
| S2 | Surface | 每页 Consume / Organize / Operate 三选一规格 |
| S3 | 色意映射 | 意图 → 固定 token 表；主行动每视图至多 1 个 primary |
| S4 | 状态完整性 | 加载 / 空 / 错可感知；同步与鉴权失败可恢复 |
| S5 | 视觉系统 | 字体、圆角、网格、焦点、色温、z/motion 全站统一 |

## 主链（S1）

```
多站订阅 / 导入 → 同步入库 → 浏览 · 未读 · 稍后看 → 播放
```

| 路径 | 页面 | 目标 |
|------|------|------|
| 主 | 订阅、首页、视频库、播放 | 进得来、扫得清、播得了 |
| 辅 | 筛选、历史、播放列表 | 可筛可标 |
| 支撑 | 站点、定时、日志、设置 | 管道可修 |
| 附属 | RSS、音乐 | 同壳，不定义气质 |

## 意图 → Token（S3 速查）

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
| [Standards](./docs/design/principles.md) | S1–S5 与验收清单 |
| [决策表](./docs/design/decisions.md) | 意图 → 标准实现 |
| [Color](./docs/design/foundations/color.md) | 色意映射全文 |
| [Typography](./docs/design/foundations/typography.md) | 字体与字阶 |
| [Spacing](./docs/design/foundations/spacing.md) | 间距、圆角、密度 |
| [Elevation](./docs/design/foundations/elevation.md) | 阴影、z-index、单画布 |
| [Motion](./docs/design/foundations/motion.md) | 时长与 easing |
| [Components](./docs/design/components/README.md) | 按钮、表单、导航、浮层… |
| [Patterns](./docs/design/patterns/README.md) | 壳、筛选、网格、卡片、状态 |
| [Token 地图](./docs/design/tokens.md) | token → 文件速查 |
