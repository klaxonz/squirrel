# Toolbar classes

← [Components](./README.md)

**代码：** `src/shared/styles/layout.css`

**Surface：** Organize（Dense 32px）；嵌在 Consume 页时控件高仍为 32px。  
**规格：** [Spec 1](../standards.md#spec-1--surface) · [Spec 2](../standards.md#spec-2--色意映射)

| Class | 用途 | 开启 / 当前 |
|-------|------|-------------|
| `.app-filter-toolbar-button` | 筛选触发器 | `.is-active` → `--app-selection-*` |
| `.app-filter-toolbar-button__count` | 计数角标 | selection count token |
| `.app-toolbar-select-trigger` | 工具栏 Select | `.is-active` → selection |
| `.app-toolbar-icon-button` | 工具栏图标按钮 | `.is-active` → selection |
| `.app-filter-toggle` | 筛选面板内 Switch 行 | 开关本体 + 标题字重；无行 wash |

面板内互斥分段轨 / 站点磁贴当前项用 **raised**（`--app-filter-raised-*`），不是 selection 墨水洗。见 [Color](../foundations/color.md) · [Filter Popover](../patterns/filter-popover.md)。

## 相关

- [Shell · 工具栏](../patterns/shell.md)
- [Filter Popover](../patterns/filter-popover.md)
