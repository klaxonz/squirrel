# Color

← [Foundations](./README.md)

**代码：** `src/shared/styles/themes/dark.css` · 选中 token 在 `layout.css`  
**规格：** [Spec 2 色意映射](../standards.md#spec-2--色意映射) · **原则：** [P2](../principles.md#p2--同一意图同一视觉语言)

## 色轴

| 项 | 标准 |
|----|------|
| 色相 | H28 暖琥珀 / 暖中性 |
| Dark / Light | 只调明度与饱和，色相不变 |
| Token 存储 | HSL 通道三元组（如 `28 90% 58%`），使用时 `hsl(var(--name))` 或 `hsl(var(--name) / α)` |
| 业务用色 | 仅语义 token；品牌梯度等例外必须集中定义在 foundations |

## 意图 → Token（完整表）

| 意图 | Token | 用法 |
|------|-------|------|
| 画布 | `--background` | 页底 |
| 正文 | `--foreground` | 主文案 |
| 抬升表面 | `--card` / `--popover` | 内容块、浮层 |
| 弱化 | `--muted` / `--muted-foreground` | 占位、次要信息 |
| 结构线 | `--border` / `--app-hairline` | 分区、描边 |
| 主行动 / 品牌 / 播放强调 | `--primary` / `--primary-foreground` | 实心主按钮、播放高亮、徽章 |
| 焦点环 | `--ring` | `:focus-visible` |
| 选中 / 当前 / 筛选开启 | `--app-selection-*` | 见下表 |
| 成功 | `--success` | 连接正常、任务成功 |
| 警告 | `--warning` | 降级、部分失败 |
| 危险 | `--destructive` | 删除、不可恢复错误 |
| 信息 | `--info` | 中性提示 |
| 遮罩 / scrim | `--overlay` 或 `--background` 的 alpha | Consume 舞台、封面压字 |
| 模态遮罩 | `--overlay` + `bg-overlay` 工具类 | Dialog / Sheet |

## 选中 token（完整色值）

定义在 `layout.css`（Dark 默认）；Light 在 `themes/dark.css` 的 `.light` 覆盖 alpha。  
使用时直接 `var(--app-selection-bg)`，不再包 `hsl()`。  
边框用 **foreground alpha**（不用 `--border`），避免 Light 纸面 / popover 上选中边溶解成 hairline。

| Token | Dark 默认 | Light 覆盖 |
|-------|-----------|------------|
| `--app-selection-bg` | `hsl(var(--foreground) / 0.1)` | `/ 0.06` |
| `--app-selection-bg-hover` | `/ 0.14` | `/ 0.09` |
| `--app-selection-border` | `/ 0.18` | `/ 0.16` |
| `--app-selection-border-hover` | `/ 0.26` | `/ 0.24` |
| `--app-selection-fg` | `hsl(var(--foreground))` | 同 |
| `--app-selection-count-bg` | `/ 0.16` | `/ 0.1` |
| `--app-selection-count-fg` | `hsl(var(--foreground))` | 同 |

侧栏当前项、筛选触发器 `.is-active`、列表选中行共用此组。

## 筛选浮层抬起面（双主题）

筛选 **分段轨 / 站点磁贴** 的「当前项」用抬起面，不用 selection 墨水洗（避免 Light 灰泥、Dark 糊成一片）。  
定义在 `layout.css`；Light 在 `themes/dark.css` `.light` 覆盖。

**Dark 规则：** raised 必须比 track **更亮**（`card` ~L9% 压在 `secondary` ~L13% 上会像凹坑，禁止）。

| Token | Dark 默认 | Light |
|-------|-----------|-------|
| `--app-filter-track-bg` | `hsl(var(--secondary))` | 同 |
| `--app-filter-raised-bg` | `hsl(28 8% 17%)`（亮于 track） | `hsl(var(--card))` |
| `--app-filter-raised-fg` | `hsl(var(--foreground))` | 同 |
| `--app-filter-raised-shadow` | `var(--shadow-xs)` | 同 |
| `--app-filter-tile-idle-bg` | `muted / 0.45` | `muted / 0.75` |
| `--app-filter-tile-idle-border` | `border / 0.7` | `border / 0.95` |
| `--app-filter-tile-hover-bg` | `muted / 0.65` | `muted` |
| `--app-filter-tile-raised-shadow` | 仅 elevation | 仅 elevation |

选中磁贴边框用 `--app-selection-border`（单通道；不要再在 shadow 里叠 1px 环）。

## Primary 使用范围

| 场景 | 规格 |
|------|------|
| 主按钮 | `Button` default，**每视图至多 1 个**实心 primary |
| 焦点环 | `--ring`（与 primary 同色相） |
| 播放 | 主 CTA、进度强调细条 |
| 品牌徽章 | `--brand-gradient` / `--brand-glow*`（仅徽章） |

## Consume 层次用色

| 场景 | 规格 |
|------|------|
| 舞台 / 封面 scrim | `hsl(var(--background) / α)` 或 `hsl(var(--overlay) / α)`，可多层叠加 |
| 封面上文案 | 对比度达到可读；压字层同样使用上列 token |
| 卡 hover 抬升 | elevation token + transform；颜色仍走 foreground / selection，不改写选中语义 |
| 进度 | primary 细条或等价 token |

## Light

| 项 | 标准 |
|----|------|
| Primary | `28 88% 50%`，字色 `--primary-foreground` |
| 浮层 | 边框 + `--app-floating-shadow` |
| Hairline | 相对 Dark 更清晰；少叠加重阴影 |

## 验收（Spec 2）

- [ ] Chrome「当前 / 列表选中 / 筛选触发器开」仅使用 `--app-selection-*`
- [ ] 筛选面板内 segment / tile 当前使用 `--app-filter-raised-*`（Dark 下 raised 亮于 track）
- [ ] 任意「健康 / 已连接」仅使用 success + 文案
- [ ] 任意 scrim 可指出 background 或 overlay 来源
- [ ] 业务样式无裸 hex / 随意 hsl（集中品牌梯度除外）
- [ ] 单视图 primary 实心主按钮 ≤ 1
