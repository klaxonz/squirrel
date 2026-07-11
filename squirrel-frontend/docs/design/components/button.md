# Button

← [Components](./README.md)

**代码：** `src/shared/ui/button`

## 是什么

触发行动的控件。

## 何时用 / 不用

| 用 | 不用 |
|----|------|
| 明确动作（保存、添加、删除） | 纯导航（用链接 / 侧栏） |
| 一页一个 `default` 主行动 | 一排多个 primary |

## 变体

| Variant | 场景 |
|---------|------|
| `default` | 主行动（primary） |
| `outline` / `secondary` | 次行动 |
| `ghost` | 工具栏弱操作 |
| `destructive` | 不可逆 |
| `link` | 行内文字链 |

## 规格

- 圆角：`--radius-md`
- Default 高 36px；工具栏常用 `size="sm"`（32px）
- 焦点：`ring-2` + `--ring`，不能只改颜色

## 相关

- 密度：[Spacing](../foundations/spacing.md)
- 主行动色：[Color](../foundations/color.md)
