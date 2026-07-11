# 30 秒决策

← [目录](./README.md)

| 我要… | 用… | 不要… |
|-------|-----|--------|
| 页内唯一主行动 | `Button` `default`（primary） | 一页多个 primary |
| 工具栏弱操作 | `Button` `ghost` / `outline` | 全刷成 primary |
| 当前导航 / 列表选中 / 筛选已开 | 中性 `--app-selection-*` | primary 底 / 字 / 角标 |
| 成功 / 在线 / 健康 | `success` + 文案 | primary |
| 警告 / 降级 | `warning` + 文案 | 与选中混用 |
| 删除 / 不可恢复 | `destructive` | 普通取消按钮 |
| 多条件筛选 | [Filter Popover](./patterns/filter-popover.md) | 页内私有面板、嵌套 Select |
| 仅排序 | 工具栏 `Select` | 塞进筛选 Popover |
| 工具栏 / 筛选浮层控件高 | **32px** Dense | 36px 表单高 |
| 设置 / 对话框字段高 | **36px** Default | — |
| 媒体墙布局 | `.app-video-grid` | 手写 `grid-cols-*` 长链 |
| 空列表 | `AppEmptyState` + 原因 + 下一步 | 假数据 / 含糊「暂无」 |

更深规则：[Color](./foundations/color.md) · [Components](./components/README.md) · [Patterns](./patterns/README.md)
