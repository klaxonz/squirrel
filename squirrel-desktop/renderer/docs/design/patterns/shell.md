# Shell · Workbench · Toolbar

← [Patterns](./README.md)

**规格：** [Spec 1 Surface](../standards.md#spec-1--surface)  
**明细：** [Surface](./surface.md)
**视觉宿主：** [UI Clone Anchors](../ui-clone-anchors.md)（壳 → FreeTube）

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
| 全局顶栏 | `--app-header-height` = `2.75rem`；搜索居中，账户入口靠右（中性头像，非 primary） |
| 沉浸路由 | 播放 / RSS / 音乐：`meta.sidebar.defaultOpen=false` 默认收起全局侧栏；播放页隐藏全局搜索顶栏 |
| 历史 | 应用级前进后退 |
| 搜索 | 仅顶栏全局搜索 |
| 侧栏宽 | `--sidebar-expanded-width` = `15rem` |
| 侧栏分组 | 与 `sidebar.ts` 一致：订阅与内容 · 资料库 · 工具；见 [Navigation](../components/navigation.md) |
| 侧栏菜单 | 文字分组 + `--app-selection-*` 当前态 |
| 折叠 | 被遮内容 `inert`，移出 a11y 树 |
| 音乐底栏 | Music 页按 YesPlayMusic 固定为 `--app-music-player-height` = `4rem`；跨全窗口、仅顶边 hairline、进度条贴顶，曲目信息 / 播放控制 / 音量队列三等分；离开 Music 后保留侧栏 mini/dock 行为 |
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
- [ ] Music 页活动播放器为 4rem 全宽底栏，内容区使用三等分且不遮住主内容
- [ ] 页面 Surface 见 [Surface](./surface.md)
- [ ] 工具栏 / 筛选仅使用文档化 class 与 shared 组件
