---
name: Squirrel Design System
description: Desktop-first media operations UI — foundations, components, patterns
source_of_truth:
  foundations: src/shared/styles/layout.css, src/shared/styles/themes/dark.css
  components: src/shared/ui/**
  patterns: src/shared/components/layout/**
  docs: docs/design/**
---

# Squirrel Design System

可执行规格。冲突时以**代码**为准，并回写对应文档页。

结构对齐业界五层：**Foundations → Components → Patterns → Content → Governance**。  
详细内容在 [`docs/design/`](./docs/design/)；本页是入口与导航。

## 源

| 层 | 管什么 | 代码 | 文档 |
|----|--------|------|------|
| Foundations | 色、字、间距、层级、动效 | `layout.css` / `themes/dark.css` | [foundations/](./docs/design/foundations/) |
| Components | 单控件：何时用、变体 | `shared/ui/**` | [components/](./docs/design/components/) |
| Patterns | 多控件组合 | `shared/components/layout/**` | [patterns/](./docs/design/patterns/) |
| Content / A11y | 文案、无障碍 | — | [content](./docs/design/content.md) · [a11y](./docs/design/accessibility.md) |
| Governance | 扩展与禁止 | — | [governance](./docs/design/governance.md) |

## 导航

| 页 | 内容 |
|----|------|
| [决策表](./docs/design/decisions.md) | 30 秒「我要…用…」 |
| [原则](./docs/design/principles.md) | 四条可落地原则 |
| [Color](./docs/design/foundations/color.md) | 语义色、选中 vs 品牌 |
| [Typography](./docs/design/foundations/typography.md) | 字体与字阶 |
| [Spacing](./docs/design/foundations/spacing.md) | 间距、圆角、密度 |
| [Elevation](./docs/design/foundations/elevation.md) | 阴影、z-index、单画布 |
| [Motion](./docs/design/foundations/motion.md) | 时长与 easing |
| [Components](./docs/design/components/README.md) | 按钮、表单、导航、浮层… |
| [Patterns](./docs/design/patterns/README.md) | 壳、筛选、网格、状态 |
| [Token 地图](./docs/design/tokens.md) | token → 文件速查 |

## 最重要的一条

```
品牌 / 主行动     →  primary
选中 / 开启 / 当前 →  --app-selection-*   （中性 ink）
运维语义          →  success | warning | destructive | info
```

**选中 ≠ 品牌。** 详见 [Color](./docs/design/foundations/color.md)。
