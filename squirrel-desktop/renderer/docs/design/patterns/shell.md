# Shell · Workbench · Toolbar

← [Patterns](./README.md)

**规格：** [Spec 1 Surface](../standards.md#spec-1--surface)  
**明细：** [Surface](./surface.md)
**视觉宿主：** [UI Clone Anchors](../ui-clone-anchors.md)（壳 → FreeTube）
**布局验证：** [Visual verification](../visual-verification.md)

## 桌面壳（标准结构）

```
Title bar
├── 主侧栏（导航，宽 15rem）
└── 主列
    ├── 顶栏（全局搜索 Cmd+K / 用户）
    ├── 滚动内容
    └── 持久播放表面
```

| 项 | 标准值 / 行为 |
|----|----------------|
| 桌面标题栏 | `--app-titlebar-height` = `2rem`；仅承载窗口、侧栏、前进后退控制 |
| 全局顶栏 | `--app-header-height` = `3.25rem`；搜索居中，账户入口靠右 |
| 历史 | 应用级前进后退 |
| 搜索 | 仅顶栏全局搜索 |
| 侧栏宽 | `--sidebar-expanded-width` = `15rem` |
| 侧栏分组 | 与 `sidebar.ts` 一致：媒体 · 资料库 · 管理；见 [Navigation](../components/navigation.md) |
| 侧栏菜单 | 文字分组 + `--app-selection-*` 当前态 |
| 折叠 | 被遮内容 `inert`，移出 a11y 树 |
| 壳角色 | 安静导航与搜索；内容在滚动区 |

## Workbench

| 项 | 标准 |
|----|------|
| 结构 | 左列表 + 右内容 + 中间竖线 |
| 次栏底 | 透明，与画布同层 |
| 分区 | `--app-hairline` + 字阶 |

## 页头与工具栏

| 项 | 标准 |
|----|------|
| 页头 | 扁、底 hairline |
| 区域 wayfinding | rail header 等已有 Pattern（如 `FeedRailHeader`） |
| 控件 class | [toolbar classes](../components/toolbar.md) |
| 组间分割 | 1px 竖线，高约 16px |
| 筛选开启 | `.is-active` + selection 计数 token |

## 验收

- [ ] 壳结构与上表一致
- [ ] 页面 Surface 见 [Surface](./surface.md)
- [ ] 工具栏 / 筛选仅使用文档化 class 与 shared 组件
