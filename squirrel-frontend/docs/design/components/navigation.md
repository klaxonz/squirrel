# Navigation controls

← [Components](./README.md)

## 组件选型

| 组件 | 场景 | 代码 |
|------|------|------|
| `Tabs*` | 页面级分段 | `shared/ui/tabs` |
| `AppSegmentedControl` | 紧凑轨 | `shared/components/layout` |
| `AppSectionNav` | 页内文字 Tab（全部 / 未读…） | `shared/components/layout` |
| `SidebarMenuItem` | 主侧栏导航 | `shared/components/layout` |

## 规则

- 激活态：前景字重 / 中性抬起（`--app-selection-*` 或侧栏 ink），**不用 primary 洗底**
- 禁止每页自绘第三套 Tab 样式
- 侧栏 active：`foreground / 0.08` 底 + `foreground` 字

## 相关

- [Color · 选中](../foundations/color.md)
- [Shell pattern](../patterns/shell.md)
