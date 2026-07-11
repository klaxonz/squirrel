# Shell · Workbench · Toolbar

← [Patterns](./README.md)

**条款：** [S1](../principles.md#s1--产品身份) · [S2](../principles.md#s2--surface-规格)

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
| 侧栏分组 | 媒体（主/附属）· 资料库（辅）· 管理（支撑）；见 [Navigation](../components/navigation.md) |
| 侧栏菜单 | 文字分组 + `--app-selection-*` 当前态 |
| 折叠 | 被遮内容 `inert`，移出 a11y 树 |
| 壳角色 | 安静导航与搜索；主链内容在滚动区 |

## S1 路径 ↔ 页面

| S1 路径 | 页面 | 默认 S2 Surface |
|---------|------|-----------------|
| 主 | 订阅、首页、视频库、播放 | 订阅 → Organize；首页/库/播放 → Consume |
| 辅 | 筛选条、历史、播放列表 | Organize |
| 支撑 | 站点、定时、日志、设置 | Operate |
| 附属 | RSS、音乐 | Consume（控件与 token 同系统） |

## Surface 规格（必须选用）

| Surface | 适用 | 控件高 | 主行动 | 选中 | 层次 |
|---------|------|--------|--------|------|------|
| **Consume** | 首页、视频墙、播放器；音乐、RSS 阅读 | chrome 轻；主 CTA 可用 40px | 每页 1× primary | `--app-selection-*` | 同色温 scrim、封面对比、卡抬升 |
| **Organize** | 订阅工作台、筛选、列表批处理、历史、播放列表 | **32px** Dense | 每页 1× primary | `--app-selection-*` | hairline 分区 |
| **Operate** | 站点、定时任务、日志、设置 | **36px** Default 字段 | 按提交需要 | `--app-selection-*` | 语义色 + 字阶 |

### 如何选定

| 主停留行为 | Surface |
|------------|---------|
| 看 / 听 / 读已入库或附属内容 | Consume |
| 订、筛、标、整理列表 | Organize |
| 站点会话、任务、日志、配置 | Operate |

混合页：主区域定 Surface；次区域用其自身规格（Consume 页内筛选 = Organize 32px）。

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
| 主路径 wayfinding | 区域标题或 rail header（如 `FeedRailHeader`） |
| 控件 class | [toolbar classes](../components/toolbar.md) |
| 组间分割 | 1px 竖线，高约 16px |
| 筛选开启 | `.is-active` + 中性计数（selection token） |

## 验收

- [ ] 壳结构与上表一致（侧栏宽、搜索位置、折叠 inert）
- [ ] 页面已标明 S1 路径 + S2 Surface，并遵守对应行规格
- [ ] 工具栏 / 筛选仅使用文档化 class 与 shared 组件
