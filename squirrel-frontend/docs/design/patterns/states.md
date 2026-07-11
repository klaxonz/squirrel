# States

← [Patterns](./README.md)

## 加载 · 空 · 错

| 状态 | 要求 | 组件 |
|------|------|------|
| Loading | 区域级 Skeleton / Block loader，避免整页闪白 | `AppSkeleton` / `AppBlockLoader` |
| Empty | 标题 + **原因** + **可行动作**（清空筛选 / 去添加） | `AppEmptyState` |
| Error | 具体错误 + 重试；禁止含糊「出了点问题」 | 文案 + 按钮 |

## 运维状态

连接、同步、任务结果：

```
success | warning | destructive  +  文案（可加图标）
```

| 意图 | 用 | 不用 |
|------|-----|------|
| 健康 / 在线 | `success` | `primary` |
| 选中 / 已筛选 | `--app-selection-*` | `primary` |

## 相关

- [Content](../content.md)
- [Feedback components](../components/feedback.md)
- [Color](../foundations/color.md)
