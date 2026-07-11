# Elevation · Z-index

← [Foundations](./README.md)

**代码：** `src/shared/styles/layout.css`  
**条款：** [S4](../principles.md#s4--视觉系统一致性) · [S1 Consume 层次](../principles.md#s1--surface-规格)

## 单画布

| 区域 | 标准 |
|------|------|
| 顶栏 / 工作区 / 工具栏 | `--background` 或透明叠于画布 |
| 主侧栏 | `--sidebar` 轻抬 |
| Workbench 次栏 | 透明 + 竖线 hairline |
| Shell 分区 | `--app-hairline` / border |

## 深度阶（何时用哪一级）

| 层级 | Token / 手段 | 场景 |
|------|----------------|------|
| 画布 | `--background` | 默认 |
| 轻表面 | `--app-surface-shadow` | 需要微弱抬起的块 |
| 媒体卡静止 | 封面 + 字阶为主；可选 surface shadow |
| 媒体卡 hover / 焦点 | `--shadow-card-hover` + `transform` | Consume |
| 中等面板 | `--app-panel-shadow` | 固定面板 |
| 浮层 | `--app-floating-shadow` / `shadow-popover` | 菜单、筛选 |
| 模态 | `--app-overlay-shadow` | Dialog |
| 品牌徽章 | `--brand-glow*` | 仅徽章 |

Organize / Operate 默认停在 hairline + 字阶；Consume 对焦点媒体使用 hover/焦点抬升阶。

## Z-index

仅使用下列 token（`layout.css`）：

```
--z-content → --z-sticky → --z-header → --z-sidebar
→ --z-dropdown → --z-popover → --z-sheet → --z-dialog
→ --z-toast → --z-player-overlay
```

业务代码使用 `z-content` / `z-dialog` 等 utility 或 `var(--z-*)`。

## 验收

- [ ] 壳层分区未使用第二套 card 浮岛底
- [ ] 阴影仅来自上表 token
- [ ] 无业务魔法 z-index 数字
