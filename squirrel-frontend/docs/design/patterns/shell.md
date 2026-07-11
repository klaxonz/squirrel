# Shell · Workbench · Toolbar

← [Patterns](./README.md)

## 桌面壳

```
Title bar
├── 主侧栏（导航，宽 15rem）
└── 主列
    ├── 顶栏（标题 / 全局搜索 Cmd+K / 用户）
    ├── 滚动内容
    └── 持久播放表面
```

| 规则 | 说明 |
|------|------|
| 历史 | 应用级前进后退，不暴露浏览器历史心智 |
| 搜索 | 全局在顶栏，不在侧栏重复 |
| 侧栏宽 | `--sidebar-expanded-width`（15rem），不随页面改几何 |
| 折叠 | 被遮内容 `inert` 且移出 a11y 树 |

## Workbench

左列表 + 右内容 + 中间竖线。  
次栏**不铺 card 底**。

## 页头与工具栏

- 页头扁、底 hairline、不重复侧栏面包屑
- 控件统一 [toolbar classes](../components/toolbar.md)
- 组间可用 1px 竖分割（高约 16px）
- 已启用筛选：中性 `.is-active` + 中性计数

## Surface 提示

| Surface | 典型 | 密度 | 强调 |
|---------|------|------|------|
| Media | 视频墙、播放器 | chrome 轻 | 仅播放 / 焦点 |
| Task | 订阅、筛选 | 工具栏 32px | 主操作 primary；选中中性 |
| System | 设置、日志 | 表单 36px | 语义色优先 |

## 相关

- [Elevation · 单画布](../foundations/elevation.md)
- [Filter Popover](./filter-popover.md)
