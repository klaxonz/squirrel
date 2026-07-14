# Media craft（Consume 品质配方）

← [Patterns](./README.md)

**Surface：** [Consume](./surface.md)  
**原则：** [P1 内容优先](../principles.md#p1--内容与真实状态优先) · [P5 可预期](../principles.md#p5--一致即可预期)  
**规格：** [Spec 1](../standards.md#spec-1--surface) · [Spec 2](../standards.md#spec-2--色意映射) · [Spec 4](../standards.md#spec-4--视觉系统一致性)

本页是 **Consume 场景的品质下限**：按 Standards 做「对」之外，媒体呈现必须达到下列配方，评审可逐项勾选。  
操作形态见 [Media card actions](./media-card-actions.md)；网格见 [Media grid](./media-grid.md)。

**源码参照（完成态以代码为准，冲突时改代码或回写本页）：**

| 区域 | 代码 |
|------|------|
| 视频卡 | `features/video/components/feed/VideoItem.vue` |
| 缩略图 | `features/video/components/feed/VideoThumbnail.vue` |
| 网格 | `layout.css` → `.app-video-grid*` |
| 首页舞台 | `features/video/views/HomeView.vue`（`.home-stage*`） |
| Rail 标题 | `features/video/components/feed/FeedRailHeader.vue` |

---

## 1. 目标

| 目标 | 含义 |
|------|------|
| 想点 | 封面与标题第一眼可读、可辨 |
| 可扫 | 来源、时间、时长、进度不抢戏但找得到 |
| 有层 | 封面 → 标题 → meta → 次要操作，层级稳定 |
| 同温 | 遮罩与画布同色温（Spec 2 scrim） |
| 不抢 | 次要操作与 chrome 不压过媒体（P1） |

---

## 2. 视频卡（网格）

### 2.1 结构（固定顺序）

```
┌─────────────────────────────┐
│  flags（仅已开）             │
│                             │
│                    duration │
│  ▓▓▓ progress               │
└─────────────────────────────┘
Title                        ← 主文案
[avatar] source · site   [⚡] ← meta + quick
         date
```

| 层 | 必须 | 禁止 |
|----|------|------|
| 缩略图 | 真实封面（或统一占位）、固定比例、圆角 `xl` 卡 / 缩略图与 token 一致 | 拉伸变形、白边毛边、缩略图上等权操作栏 |
| 标题 | 网格 **最多 2 行**；字重 ≥ 600；`foreground`；`line-height` 紧凑 | 标题用 primary；3 行以上默认露出 |
| Meta | 来源名可读；次行日期 / 站点用 muted，对比仍可扫 | meta 与标题同色同重导致糊成一块 |
| Quick | 见 media-card-actions：默认弱、hover/focus-within 显、on = selection | 实心 primary 圆钮工具栏 |
| 时长 | 压在封面上，tabular；底 `--app-media-badge-bg`，字 `--app-media-on-image` | 裸白字无底、对比不足 |
| 进度 | 底边细条（约 2–3px）；填充可用 primary 或高对比浅条 | 粗进度条抢封面 |

### 2.2 比例与间距

| 项 | 配方 |
|----|------|
| 封面比例 | 网格默认 **16:9**（与 `VideoThumbnail` 一致）；同类墙内比例统一 |
| 卡圆角 | 容器 / 封面使用 `--radius-xl` 或文档化等价（Spec 4） |
| 封面→标题 | **0.5–0.75rem**（现参照约 `0.625rem`） |
| 网格 gap | 仅 `.app-video-grid*` + `--app-video-grid-gap*`；不手写长 breakpoint 链 |
| 最小列宽 | `--app-grid-min` 默认约 280px；紧凑变体单独覆盖 |

### 2.3 交互

| 状态 | 配方 |
|------|------|
| Hover 卡 | 允许 `shadow-card-hover` + 轻微 `transform`（仅 transform/opacity）；标题保持 foreground |
| Focus-visible | 卡或主控：环用 `--ring`，与全局 focus 一致 |
| 主点击 | 整卡（或明确主热区）→ 打开/播放 |
| Quick | `click.stop`；不触发展开卡 |

### 2.4 列表变体

| 项 | 配方 |
|----|------|
| 布局 | 左固定比封面，右标题 + meta；垂直对齐标题顶或光学中线 |
| 标题 | 可 1–2 行；描述若有，muted、最多 2 行 |
| 密度 | 行高舒适可点；不要 Operate 表单那套 36px 字段感 |

### 验收 · 视频卡

- [ ] 16:9（或墙内统一比）、无毛边白边  
- [ ] 标题 ≤ 2 行、字重清晰、非 primary  
- [ ] 时长/进度可读且不抢封面  
- [ ] 无缩略图等权操作栏；quick 符合 media-card-actions  
- [ ] hover/focus 有层、无布局抖动（不用改 width/height 做动画）  
- [ ] scrim/时长底可追溯 background 或 overlay token  

---

## 3. 媒体墙 / Rail

| 项 | 配方 |
|----|------|
| 布局 | 只用 `.app-video-grid` / `--feed` / `--compact` |
| 分区标题 | H2 级 rail header；与卡片墙 **左缘对齐** |
| 标题→墙 | 区块间距 24–32px 量级；rail 之间可略松（28–40px） |
| 横向 rail | 卡片高度一致；滚动不裁切 focus 环 |
| 空墙 | Spec 3：原因 + 下一步（去订阅 / 清空筛选） |
| 加载 | Skeleton **形状贴近终态**（封面块 + 两行字），禁止整页单圆圈 |

### 验收 · 墙

- [ ] 无手写 `grid-cols-1 sm:…3xl` 长链  
- [ ] rail 标题与内容对齐、间距稳定  
- [ ] skeleton 像卡不是通用 spinner  

---

## 4. 焦点舞台（首页 Hero / 继续看主视觉）

Consume 焦点区允许更强层次，但必须 **同色温、可扫、可点**。

| 项 | 配方 |
|----|------|
| 媒体 | 大图或主推封面；加载时占位尺寸稳定（防 CLS） |
| Scrim | 仅 `hsl(var(--background) / α)` 或 `hsl(var(--overlay) / α)` 多层；**禁止**与画布脱节的纯黑/纯白孤岛 |
| 标题 | Hero 或 H1 + display；最多 **2 行**；对比足够 |
| 副文 | meta ≤ 约 1–2 行；muted 或半透明 foreground，仍可读 |
| 主 CTA | 每视图 1 个 primary（播放 / 继续）；次操作 ghost |
| 进度 | 若有：文案 + 细条，primary 填充可接受 |
| 与下方墙 | 舞台底与第一 rail 间距明确；不黏成一片 |

### 验收 · 舞台

- [ ] scrim 可指出 token 来源  
- [ ] 标题/CTA 无需滚动即可理解主行动（桌面主栏宽度下）  
- [ ] 仅一个实心 primary  
- [ ] 与下方内容同色温连续  

---

## 5. 播放页（内容优先摘要）

| 项 | 配方 |
|----|------|
| 播放器 | 主列焦点；控件不长期遮挡画面中心内容 |
| 标题区 | 标题 > 频道/源 > 次要动作；次要用 ghost |
| 关联/列表 | 侧列或下方用卡配方；密度可 Organize 工具条但不改卡的 Consume 层级 |
| 错误 | 播失败：原因 + 重试 / 检查站点登录（Spec 3） |

完整播放器 chrome 细节可另开 Pattern；本页保证 **信息层级与状态** 不低于此。

---

## 6. 文字与对比（Consume 下限）

| 元素 | 配方 |
|------|------|
| 卡标题 | ≥ 0.875rem，字重 ≥ 600，`foreground` |
| 来源名 | 可点击时 hover 提高对比；默认不低于明显 muted |
| 次要 meta | micro / 2xs–xs；`muted-foreground` |
| 封面上的字 | 必须有底或 scrim；不靠「深色封面碰运气」 |
| 数字时长 | `app-mono` 或 tabular；右下或规范位置统一 |

---

## 7. 色与深度（Consume）

| 项 | 配方 |
|----|------|
| 画布 | `--background` 暖中性 |
| 抬升 | 卡 hover 用 elevation token，不描 primary 大环当「选中」 |
| 选中/已开 | 仅 `--app-selection-*`（列表选中、quick on） |
| 播放强调 | primary 仅 CTA、细进度、焦点环 |
| 禁止 | 大面积 primary 洗卡；Operate 语义色当装饰条 |

---

## 8. 与 Standards 的关系

| 层级 | 管什么 |
|------|--------|
| Principles / Spec 1–4 | 对、稳、一致、可验收底线 |
| **本页 Media craft** | Consume **好看与可扫的下限配方** |
| 单组件实现 | 以源码参照为准；改视觉先改 shared/模式再扫业务 |

合入 **首页、视频库、订阅流内卡片、播放相关 Consume 面** 时：Standards 验收 + 本页相关验收 **都要勾**。  
Organize 页内的视频卡仍按本页卡配方（媒体不降级）；工具栏仍用 Organize 32px。

---

## 9. 总验收（Media craft）

- [ ] 卡：结构、比例、标题行数、操作分离达标  
- [ ] 墙：grid token、rail 节奏、skeleton 成形  
- [ ] 舞台（若有）：同色温 scrim、单 primary、标题可读  
- [ ] 对比与封面上文字达标  
- [ ] 无纯黑/纯白色温断裂、无缩略图工具栏回潮  

未勾选项视为 **Consume 品质未达标**（即使 Spec 勾选通过）。
