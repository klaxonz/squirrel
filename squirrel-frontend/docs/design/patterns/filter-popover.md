# Filter Popover

← [Patterns](./README.md)

**代码：** `AppFilterPanel` 等 · `shared/components/layout`  
**Surface：** Organize（Dense 32px）；可嵌在 Consume 页工具栏  
**规格：** [Spec 1](../standards.md#spec-1--surface) · [Spec 2](../standards.md#spec-2--色意映射)

## 适用

≥2 个筛选维度，或维度随上下文显隐（来源 / 时间 / 时长 / 类型 / 分级 / 特别关注）。

## 筛选与排序

| 能力 | 标准 UI |
|------|---------|
| 筛选（缩小集合） | 本 Popover |
| 排序（只改顺序） | 工具栏独立 `Select` |

## 行为规格

| 项 | 标准 |
|----|------|
| 选择完成位置 | 同一 Popover 内完成 |
| 短列表 | ≤6 项用 Chip 轨 |
| 站点等长列表 | OptionList 磁贴 |
| 生效 | 即时生效 |
| 重置 | 有条件时显示「重置」 |
| 触发器开启态 | `--app-selection-*` / `.is-active` + 中性计数 |
| 控件高 | Dense 32px |

## 结构

实现与字段布局以 `AppFilterPanel` 及现有 feed 工具栏为准；新筛选项扩展 shared Pattern，不新增业务私有面板。

## 验收

- [ ] 筛选仅通过 `AppFilterPanel`（或文档化等价）
- [ ] 排序在工具栏独立 Select
- [ ] 开启态为 selection token
- [ ] 控件高 32px
