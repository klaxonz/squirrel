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
- 已选筛选 Chip：`app-toolbar-chip--active`（中性选中）
- hover 可提示移除（destructive 倾向）

## Card · 媒体卡

- 表面 `radius-lg`；媒体卡 `radius-xl`
- 不嵌套卡片套卡片（除非内层是重复列表项）

## 相关

- [States pattern](../patterns/states.md)
- [Color](../foundations/color.md)
