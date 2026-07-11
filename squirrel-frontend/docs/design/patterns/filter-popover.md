# Filter Popover

← [Patterns](./README.md)

**核心 Pattern。** 代码：`AppFilterPanel` 等 · `shared/components/layout`

## 何时用

≥2 个筛选维度，或维度会随上下文显隐（来源 / 时间 / 时长 / 类型 / 分级 / 特别关注）。

## 排序 vs 筛选

| | 筛选 | 排序 |
|--|------|------|
| 作用 | 缩小集合 | 只改顺序 |
| UI | 本 Popover | 工具栏独立 Select |

## Do / Don’t

| Do | Don’t |
|----|--------|
| 同一 Popover 内完成选择 | 再叠一层 Select 下拉 |
| ≤6 项用 Chip 轨；站点用 OptionList 磁贴 | 长列表 + 散落 pill 伪表单 |
| 即时生效；有条件才显示「重置」 | 额外「应用」按钮 |
| 触发器中性选中 | primary 洗底 / 琥珀角标 |
| 排序独立工具栏 Select | 排序塞进筛选面板 |

## 结构

```
PopoverContent ~17.25rem · p-0 · shadow-popover
└── AppFilterPanel
    ├── header：筛选 + 计数 + 重置
    └── body
        ├── 来源 → AppFilterOptionList（3 列磁贴 + check）
        ├── 范围 → row：标签左 + AppFilterChips 右
        ├── 类型 / 分级 → row chips
        └── 特别关注 → 底部分隔 + Switch
```

## 实现锚点

| 部件 | 实现 |
|------|------|
| 壳 | `AppFilterPanel` |
| 分区 | `AppFilterSection`（`layout="row"`） |
| Chip | `AppFilterChips` |
| 站点 | `AppFilterOptionList` + `SiteIcon` |
| 开关 | `.app-filter-toggle` |
| 触发 | `.app-filter-toolbar-button` |

## 视觉

- 触发器激活：中性 ink（见 [Color](../foundations/color.md)）
- 站点选中：抬起表面 + 中性描边 + 勾，不用 primary 整行洗色
- 条件轨：左短标签、右 segmented
- 图标：`/api/sites/{slug}/icon` + `resolveServerAssetUrl`；失败用品牌 monogram

## 回显

- 内容区 `ActiveFilters` Chip 可移除单项
- 面板「重置」清全部
- 触发器 `aria-label="筛选，已启用 N 项"`

## 相关

- [Toolbar classes](../components/toolbar.md)
- [Forms · Dense Select](../components/forms.md)
