# Shell · Workbench · Toolbar

← [Patterns](./README.md)

**条款：** [S1 Surface](../principles.md#s1--surface-规格)

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
| 历史 | 应用级前进后退 |
| 搜索 | 仅顶栏全局搜索 |
| 侧栏宽 | `--sidebar-expanded-width` = `15rem` |
| 侧栏分组 | 与 `sidebar.ts` 一致：媒体 · 资料库 · 管理；见 [Navigation](../components/navigation.md) |
| 侧栏菜单 | 文字分组 + `--app-selection-*` 当前态 |
| 折叠 | 被遮内容 `inert`，移出 a11y 树 |
| 壳角色 | 安静导航与搜索；内容在滚动区 |

## 当前应用：页面 → Surface

下列对照是**现有路由的落地表**（Pattern 应用说明），不是产品路径分级。改路由时同步改本表。

| 页面 / 区域 | Surface |
|-------------|---------|
| 首页、视频库墙、播放器 | Consume |
| 音乐、RSS 阅读 | Consume |
| 订阅工作台、筛选条、历史、播放列表 | Organize |
| 站点、定时任务、日志、设置 | Operate |

混合：Consume 页内的筛选条仍用 Organize 控件高（32px）。

## Surface 规格（与 S1 一致）

| Surface | 控件高 | 主行动 | 选中 | 层次 |
|---------|--------|--------|------|------|
| **Consume** | chrome 轻；主 CTA 可用 40px | 每页 1× primary | `--app-selection-*` | 同色温 scrim、封面对比、卡抬升 |
| **Organize** | **32px** Dense | 每页 1× primary | `--app-selection-*` | hairline 分区 |
| **Operate** | **36px** Default 字段 | 按提交需要 | `--app-selection-*` | 语义色 + 字阶 |

### 如何选定（不依赖产品路径表）

| 主停留行为 | Surface |
|------------|---------|
| 看 / 听 / 读 | Consume |
| 订 / 筛 / 标 / 整理列表 | Organize |
| 改配置 / 修站点与任务 / 看日志 | Operate |

### 组件

| 需求 | 标准来源 |
|------|----------|
| 按钮 / 输入 / 对话框 | `shared/ui/**` |
| 工具栏 / 筛选 / 空态 / 页壳 | `shared/components/layout/**` + `layout.css` class |
| 新媒体网格 | `.app-video-grid*` |

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
- [ ] 页面可指出 Surface 并遵守对应行
- [ ] 工具栏 / 筛选仅使用文档化 class 与 shared 组件
