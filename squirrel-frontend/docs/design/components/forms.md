# Forms

← [Components](./README.md)

**代码：** `src/shared/ui`（Input / Select / Textarea / Switch）· 字段表面 token 在 `layout.css`

## Input · Select · Textarea

| 用 | 不用 |
|----|------|
| 收集用户输入 | 筛选维度里叠 Select（见 [Filter Popover](../patterns/filter-popover.md)） |

### 规格

- 共享表面：`--app-field-bg`、`--app-field-border` 等
- 设置 / 对话框：**36px** Default
- **工具栏 Select：32px + `text-xs`**
  - class：`app-toolbar-select-trigger`
  - 多维筛选优先 [Filter Popover](../patterns/filter-popover.md) chip / 磁贴，不在面板内叠 Dense Select
- Focus：边框切入 ring，不用纯 glow 替代

## Switch

| 用 | 不用 |
|----|------|
| 二元、即时生效的偏好 | 需要确认才提交的设置（用 Checkbox + 保存） |

- 与说明文案组成 **toggle 行**（见 Filter Pattern）
- 不要裸开关堆在面板底部

## 相关

- [Spacing · Density](../foundations/spacing.md)
- [Filter Popover](../patterns/filter-popover.md)
