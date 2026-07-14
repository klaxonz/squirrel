# Overlays

← [Components](./README.md)

**代码：** `shared/ui`（dropdown-menu / popover / dialog 等）

## 选型

| 容器 | 何时用 | 何时不用 |
|------|--------|----------|
| Menu / Dropdown | 动作列表、短排序 | 多字段表单 |
| Popover | 筛选、轻量多字段 | 长流程、强确认 |
| Dialog | 确认、导入、长表单 | 一个开关就能解决的事 |
| Sheet | 少用 | 默认优先 Popover |

## 视觉

- `bg-popover` + border + `shadow-popover` + `radius-lg`
- Light 下不能只靠白底无边无影

## 相关

- [Elevation](../foundations/elevation.md)
- [Filter Popover](../patterns/filter-popover.md)
