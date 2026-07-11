# Spacing · Radius · Density

← [Foundations](./README.md)

**代码：** `src/shared/styles/layout.css`  
**规格：** [Spec 1](../standards.md#spec-1--surface) · [Spec 4](../standards.md#spec-4--视觉系统一致性)

## Spacing

使用 `--space-0` … `--space-9`。页面槽：`--app-page-gutter*`；内容底距：`--app-content-padding-bottom`。

| 场景 | 标准值 |
|------|--------|
| 控件内 gap | 8px（`--space-2`） |
| 表单纵向 | 12–16px |
| 筛选 Popover 字段 | 12px |
| 区块间距 | 24–32px |
| Consume rail / 分区 | 28–40px |
| 媒体网格 | `--app-video-grid-gap*` |

## Radius

| Token | 值 | 用途 |
|-------|-----|------|
| `sm` | 4px | 内 item、小芯片 |
| `md` | 6px | 按钮、输入、工具栏控件 |
| `lg` | 8px | Popover、Dialog |
| `xl` | 10px | 媒体卡 |

全站仅此四阶。

## Density（控件高）

| 名 | 高 | Surface |
|----|-----|---------|
| Dense | 32px | Organize 工具栏、筛选浮层、分段控件 |
| Default | 36px | Operate 设置表单、对话框；侧栏项 |
| Comfort | 40px | Consume / 登录等强调 CTA |

## 验收

- [ ] 间距来自 `--space-*` 或文档化 app 槽 token
- [ ] 圆角仅 sm/md/lg/xl
- [ ] 控件高与页面 Surface 一致（Spec 1）
