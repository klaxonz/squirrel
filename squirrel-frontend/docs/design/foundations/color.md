# Color

← [Foundations](./README.md)

**代码：** `src/shared/styles/themes/dark.css` · 选中 token 在 `layout.css`

## 规则

- **色相：** H28 暖琥珀。Dark / Light 只调明度与饱和，不换色温。
- **写法：** token 存 HSL 通道（如 `28 90% 58%`），使用 `hsl(var(--primary))` 或 `hsl(var(--primary) / α)`。
- **禁止：** 业务代码写裸 hex / 裸 hsl（徽章渐变等已集中定义的除外）。

## 角色

| 意图 | Token | 用在 |
|------|-------|------|
| 画布 / 正文 | `--background` / `--foreground` | 页底、主文案 |
| 抬升表面 | `--card` / `--popover` | 内容块、浮层 |
| 弱化 | `--muted` / `--muted-foreground` | 占位、未激活、次要信息 |
| 结构线 | `--border` / `--app-hairline` | 分区、描边 |
| **主行动 / 品牌** | `--primary` | 主按钮、焦点环、播放、徽章 |
| **中性选中** | `--app-selection-*` | 筛选开启、chip active、列表选中、对齐侧栏 |
| 焦点环 | `--ring` | `:focus-visible` |
| 危险 | `--destructive` | 删除、不可恢复错误 |
| 成功 | `--success` | 连接正常、任务成功 |
| 警告 | `--warning` | 降级、重试、部分失败 |
| 信息 | `--info` | 中性提示 |

## 三套强调（不要混）

```
品牌 / 主行动     →  primary
选中 / 开启 / 当前 →  --app-selection-*   （中性 ink）
运维语义          →  success | warning | destructive | info
```

## Primary：允许 / 禁止

| ✓ 允许 | ✗ 禁止 |
|--------|--------|
| Primary Button | 选中、已筛选、导航当前、列表选中 |
| Focus ring | 筛选计数角标 |
| 播放高亮 | 「服务正常 / 已连接」 |
| 品牌徽章（字标、logo） | 大面积洗底、图标默认色 |
| | light 下 primary 低 α 洗出脏桃色 |

## 中性选中 token

定义在 `layout.css`（**完整色值**，非 HSL 通道三元组）：

| Token | 值 |
|-------|-----|
| `--app-selection-bg` | `hsl(var(--foreground) / 0.08)` |
| `--app-selection-bg-hover` | `hsl(var(--foreground) / 0.1)` |
| `--app-selection-border` | `hsl(var(--border) / 0.9)` |
| `--app-selection-border-hover` | `hsl(var(--border))` |
| `--app-selection-fg` | `hsl(var(--foreground))` |
| `--app-selection-count-bg` | `hsl(var(--foreground) / 0.12)` |
| `--app-selection-count-fg` | `hsl(var(--foreground))` |

用法：`background: var(--app-selection-bg)`（不要再包 `hsl()`）。  
与侧栏 `.sidebar-item.is-active` 同语言。

## Do / Don’t

| Do | Don’t |
|----|--------|
| 筛选按钮激活：中性底 + 前景字 + 中性角标 | 琥珀底 / 琥珀字 / 实心 primary 角标 |
| 主按钮一页一个 | 工具栏每个控件都 primary |
| 在线状态用 success +「已连接」 | 用 primary 点表示健康 |
| 浮层：border + `shadow-popover` | light 下纯白无边无影「贴死」页面 |

## Light 补充

- 浮层依赖 **边框 + `--app-floating-shadow`**。
- Light 下 hairline 更明显，少叠加重阴影。
- Light primary：`28 88% 50%`，字色 `--primary-foreground`（白）。
