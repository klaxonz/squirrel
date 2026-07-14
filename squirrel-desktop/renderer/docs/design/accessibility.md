# Accessibility

← [目录](./README.md)

## 要求

- 目标 **WCAG 2.1 AA** 对比度
- 自定义控件必须有可见 `:focus-visible`
- 状态不只靠颜色（辅以文字、图标、角标）
- 图标按钮：`aria-label` / `title`
- 筛选激活：`aria-label="筛选，已启用 N 项"`
- 尊重 `prefers-reduced-motion`（见 [Motion](./foundations/motion.md)）

## 焦点

- 使用 `--ring`，与 primary 色相一致
- 不要只靠颜色变化表示焦点
- 模态打开时焦点陷阱；关闭后焦点回到触发器

## 相关

- [Color · ring](./foundations/color.md)
- [Filter Popover · a11y 标签](./patterns/filter-popover.md)
