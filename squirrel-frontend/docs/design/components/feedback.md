# Feedback

← [Components](./README.md)

| 能力 | 规格 | 代码 |
|------|------|------|
| Skeleton | 仅 `AppSkeleton` + `--app-skeleton-*` | `shared/components` |
| Spinner | `--app-spinner-size-*`（过程反馈可用 primary 色） | `AppSpinner` |
| Toast | 底右、`--z-toast`；success / error / info | `shared/components/toast` |
| Empty | `AppEmptyState`：原因 + 下一步 | layout 组件 |
| 列表选中 | `AppListOption` / `AppSelectableListItem` → `--app-selection-*` | layout |

## Badge · Chip

- 状态 = 文案 + 色，不只靠色
- 筛选开启计数：工具栏 `.app-filter-toolbar-button__count`（selection count）
- 面板内互斥当前：raised segment（`--app-filter-raised-*`），见 [Filter Popover](../patterns/filter-popover.md)

## Card · 媒体卡

- 表面 `radius-lg`；媒体卡 `radius-xl`
- 不嵌套卡片套卡片（除非内层是重复列表项）

## 相关

- [States pattern](../patterns/states.md)
- [Color](../foundations/color.md)
