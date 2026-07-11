# Toolbar classes

← [Components](./README.md)

**代码：** `src/shared/styles/layout.css`

**Surface：** Organize（Dense 32px）；嵌在 Consume 页时控件高仍为 32px。  
**规格：** [Spec 1](../standards.md#spec-1--surface) · [Spec 2](../standards.md#spec-2--色意映射)

| Class | 用途 |
|-------|------|
| `.app-filter-toolbar-button` | 筛选触发器（`.is-active` = selection） |
| `.app-filter-toolbar-button__count` | 计数角标（selection count token） |
| `.app-toolbar-chip` / `--active` | 条件 Chip |
| `.app-toolbar-select-trigger` | 工具栏 Select |
| `.app-toolbar-icon-button` | 工具栏图标按钮 |
| `.app-filter-select` | 筛选内 Dense Select |
| `.app-filter-button` / `.app-filter-toggle` | 筛选面板内控件 |

开启 / 激活态：`--app-selection-*`。见 [Color](../foundations/color.md)。

## 相关

- [Shell · 工具栏](../patterns/shell.md)
- [Filter Popover](../patterns/filter-popover.md)
