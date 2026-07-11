# Toolbar classes

← [Components](./README.md)

**代码：** `src/shared/styles/layout.css`

工具栏 / 筛选触发器共用 class，禁止业务页另起一套。

| Class | 用途 |
|-------|------|
| `.app-filter-toolbar-button` | 筛选触发器（`.is-active` = 中性选中） |
| `.app-filter-toolbar-button__count` | 计数角标（中性，非 primary） |
| `.app-toolbar-chip` / `--active` | 条件 Chip |
| `.app-toolbar-select-trigger` | 工具栏 Select |
| `.app-toolbar-icon-button` | 工具栏图标按钮 |
| `.app-filter-select` | 筛选内 Dense Select |
| `.app-filter-button` / `.app-filter-toggle` | 筛选面板内控件 |

激活态全部走 `--app-selection-*`。见 [Color](../foundations/color.md)。

## 相关

- [Shell · 工具栏](../patterns/shell.md)
- [Filter Popover](../patterns/filter-popover.md)
