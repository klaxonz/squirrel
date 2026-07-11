# Navigation controls

← [Components](./README.md)

## 组件选型

| 组件 | 场景 | 代码 |
|------|------|------|
| `Tabs*` | 页面级分段 | `shared/ui/tabs` |
| `AppSegmentedControl` | 紧凑轨 | `shared/components/layout` |
| `AppSectionNav` | 页内文字 Tab（全部 / 未读…） | `shared/components/layout` |
| `Sidebar` + `SidebarMenuItem` | 主侧栏导航 | `shared/components/layout` |

## 主侧栏结构

```
aside.sidebar-rail
├── top-nav     首页（固定）
├── nav         分组（媒体 / 资料库 / 管理）
│   └── group   文字 section label + 菜单项
└── footer      设置
```

| 规则 | 说明 |
|------|------|
| 宽 | `--sidebar-expanded-width`（15rem），不随页改 |
| 底 | `--sidebar` 轻抬升；右边界 `var(--app-hairline)` |
| 项高 | `--sidebar-item-height`（36px Default） |
| 分组标题 | 仅文字、Micro 级；无分组图标 |
| 项缩进 | 分组标题提供层次；菜单项不再二次 indent |
| 分组语义 | 媒体 = 主路径 + 附属；资料库 = 辅路径；管理 = 支撑路径（S1） |
| 侧栏内容 | 导航项与必要入口；站点健康 / 任务细节在支撑页呈现 |

## 选中 / 悬停

| 状态 | 规格 |
|------|------|
| 默认 | `muted-foreground` 字 + 透明底 |
| Hover | `foreground / 0.055` 底 + `selection-fg` |
| Active（当前） | `var(--app-selection-bg)` + `var(--app-selection-fg)` + 字重 600 |
| Active hover | `var(--app-selection-bg-hover)` |
| Focus | inset ring（`--ring`） |
| 图标 | `currentColor`，随文字变 |

实现：`SidebarMenuItem.vue`（主栏）、`MusicNavItem.vue`（音乐次栏同语言）。

## 其它导航控件

| 组件 | 激活态 |
|------|--------|
| `Tabs*` / `AppSegmentedControl` / `AppSectionNav` | 前景字重 / 中性抬起，不用 primary 洗底 |

禁止每页自绘第三套 Tab 样式。

## 相关

- [Color · 选中](../foundations/color.md)
- [Shell pattern](../patterns/shell.md)
