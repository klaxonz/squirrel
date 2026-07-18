# Button

← [Components](./README.md)

**代码：** `src/shared/ui/button`

## 适配边界

`Button` 是 PrimeVue Button 的薄语义适配：只映射本产品文档中的
`default` / `secondary` / `outline` / `ghost` / `destructive` / `link` 意图，和
`default` / `sm` / `lg` 三档密度。`icon-only` 使用 PrimeVue 的原生图标按钮
样式。

禁止把播放器、媒体卡、标题栏等业务场景继续塞进 Button 的 `variant` 或 `size`。
媒体卡、列表行、时间轴标记等自定义交互应使用语义化原生 `button`，由对应 pattern
持有布局和行为；不得以 `unstyled` 绕开 Aura。

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
