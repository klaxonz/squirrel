# Spacing · Radius · Density

← [Foundations](./README.md)

**代码：** `src/shared/styles/layout.css`

## Spacing

`--space-0` … `--space-9`。  
页面槽：`--app-page-gutter*`；内容底距：`--app-content-padding-bottom`。

| 场景 | 值 |
|------|-----|
| 控件内 gap | 8px（`--space-2`） |
| 表单纵向 | 12–16px |
| 筛选 Popover 字段 | **12px** |
| 区块间距 | 24–32px |
| 媒体网格 | `--app-video-grid-gap*` |

## Radius

| Token | 值 | 用途 |
|-------|-----|------|
| `sm` | 4px | 内 item、小芯片 |
| `md` | 6px | 按钮、输入、工具栏控件 |
| `lg` | 8px | Popover、Dialog |
| `xl` | 10px | 媒体卡 |

## Density（控件高）

| 名 | 高 | 场景 |
|----|-----|------|
| Dense | 32px | 工具栏、筛选浮层、分段控件 |
| Default | 36px | 设置表单、对话框、侧栏项 |
| Comfort | 40px | 少用：强调 CTA |

**禁止：** Task 型 Popover 内用 Default 36px 堆出「表单草稿」感。
