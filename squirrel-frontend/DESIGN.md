---
name: Squirrel Frontend
description: Desktop-first media subscription and playback control surface
source_of_truth:
  tokens: src/shared/styles/layout.css
  themes: src/shared/styles/themes/dark.css
  primitives: src/shared/ui/**
  layout_primitives: src/shared/components/layout/**
---

# Squirrel 前端设计规格

本文档是**可执行规格**，不是愿景散文。  
冲突时以代码中的 CSS 变量与共享组件为准，并回写本文档；禁止在业务页发明第二套视觉语言。

| 权威来源 | 路径 |
|---------|------|
| 布局 / 密度 / z-index / motion / 共享 class | `src/shared/styles/layout.css` |
| 明暗色板 | `src/shared/styles/themes/dark.css`（含 `.light`） |
| 基础组件 | `src/shared/ui/**` |
| 布局与模式组件 | `src/shared/components/layout/**` |

---

## 1. 产品界面定位

**一句话：** 桌面端私人媒体运营台——浏览与播放以媒体为主，订阅/筛选/任务/诊断以可扫描、可操作为主。

**不是：** 流媒体营销页、SaaS 仪表盘模板、移动优先信息流。

**品牌气质：** 安静、电影感、能干。Chrome 收敛，状态清楚，动效短。

### 1.1 三类界面（Surface）

所有页面先归类，再选密度与强调色。同一路由内可混合（例如视频墙是 Media，顶栏筛选是 Task）。

| Surface | 典型页面 | 目标 | 默认密度 | Accent 用量 |
|---------|----------|------|----------|-------------|
| **Media** | 视频墙、频道详情、播放器、音乐封面墙 | 缩略图与标题主导 | 内容疏、chrome 轻 | 仅播放/选中/焦点 |
| **Task** | 订阅、筛选、历史、播放列表、RSS 列表 | 扫描、筛选、批处理 | 工具栏 32px、字段紧凑 | 选中/已筛选/主操作 |
| **System** | 设置、站点 runtime、定时任务、日志 | 诊断与配置 | 表单 36px、表格可读 | 语义色优先于 brand |

**决策：**

1. 先定 Surface，再选组件与间距。  
2. Media 区域禁止堆高对比表单控件抢缩略图。  
3. Task 浮层（筛选 Popover）用 **dense control（32px）**，不用默认表单 36px。  
4. System 状态用 `success` / `warning` / `destructive` / `info`，**不要用 primary 表示“健康/在线”**。

---

## 2. 颜色语义

色相轴统一为 **H28 暖琥珀**。Dark / Light 只调明度与饱和度，不换色温。  
值定义在 `themes/dark.css`；业务代码只消费语义 token，不写裸 HSL（品牌徽章渐变等已集中定义的除外）。

### 2.1 角色表

| Token | 职责 | 允许 | 禁止 |
|-------|------|------|------|
| `--background` / `--foreground` | 壳层画布与主文字 | 页面底、正文 | 用 background 当卡片抬升凑层次 |
| `--sidebar` | 主导航轻微抬升 | 仅主侧栏 | workbench 次栏再铺一层 card |
| `--card` | 内容块、输入底、列表项表面 | 媒体卡、设置分组、表内表面 | 给 shell 分区“刷存在感” |
| `--popover` | 浮层表面 | 菜单、筛选面板、下拉 | 与 page 同色无阴影导致“贴死” |
| `--muted` / `--muted-foreground` | 弱表面与次要信息 | 标签、占位、未激活图标 | 主文案长期用 muted-foreground |
| `--border` / `--app-hairline` | 结构线 | 分区、输入描边 | 深色下用高对比硬框描整个 shell |
| `--primary` | **交互强调 + 品牌** | 主按钮、选中、已筛选、焦点环、播放强调 | 成功/失败/告警；大面积装饰底 |
| `--ring` | 键盘焦点 | focus-visible | 当装饰描边滥用 |
| `--destructive` | 破坏性 | 删除、不可恢复错误 | 普通警告 |
| `--success` | 健康/成功 | 连接正常、任务成功 | 品牌装饰 |
| `--warning` | 需注意 | 降级、重试、部分失败 | 与 primary 混用表“选中” |
| `--info` | 中性信息 | 提示性状态 | 替代 primary 选中 |

### 2.2 Primary（琥珀）硬规则

```
primary 仅用于：
  - 主行动（Primary Button）
  - 明确的选中 / 已启用筛选 / 当前导航强调
  - focus ring（与 --ring 一致）
  - 播放相关高亮、品牌徽章

primary 不得用于：
  - “服务正常 / 同步成功”等运维语义（改 success）
  - 大面积背景洗色
  - 每个图标默认色
```

**已筛选 / 工具栏激活：** `border primary/0.22` + `bg primary/0.08` + 计数角标 `primary` 字色。  
**未激活 chrome：** `muted-foreground`，不要为了“好看”提对比。

### 2.3 Light 模式补充

- 浮层（popover/dropdown）依赖 **边框 + `--app-floating-shadow`**，不能只靠与页面同色的白底。  
- Light 下 hairline 本身更明显，少叠加重阴影；Dark 下阴影可略强以分层。  
- Primary 在 Light 为 `28 88% 50%`，字色用 `--primary-foreground`（白），保证按钮对比。

---

## 3. 字体

**UI 字体：** Inter + 系统 fallback（`--font-sans` / 产品界面统一）。  
**等宽：** JetBrains Mono（日志、ID、计数、`--app-mono` / `.app-mono`）。

**层级只用字号 / 字重 / 对比，不引入第二套展示字体。**

| 级别 | Token / 规格 | 用途 |
|------|----------------|------|
| Hero | `--app-hero-size` 1.75rem / 650 | 极少：登录或空状态主标题 |
| H1 | `--app-h1-*` 1.6875rem / 600 | 页面主标题 |
| H2 | `--app-h2-*` 1.25rem / 600 | 区块、设置分组 |
| H3 | `--app-h3-*` 1.0625rem / 600 | 卡片标题、模块名 |
| H4 | `--app-h4-*` 0.875rem / 600 | 紧凑模块标题 |
| Body | 0.875rem / 400–500 | 正文、列表行、说明 |
| Label | 0.75–0.8125rem / 600 | Tab、侧栏、按钮、字段标签 |
| Micro | 0.625–0.6875rem / 500–600 | 时长角标、筛选计数、次要元数据 |

**规则：**

- 产品 UI 使用固定 rem，不做流体大标题。  
- 同一工具栏内字号不超过两档（通常 12px 控件 + 11px 元数据）。  
- 筛选字段标签：`0.6875rem / 600`；面板标题：`0.8125rem / 650`。

---

## 4. 间距、圆角、控件高度

### 4.1 Spacing

使用 `--space-0` … `--space-9`（见 `layout.css`）。  
页面槽：`--app-page-gutter*`；内容底距：`--app-content-padding-bottom`。

| 场景 | 建议 |
|------|------|
| 控件内 gap | `--space-2`（8px） |
| 表单字段纵向 | `--space-3`–`--space-4`；**筛选 Popover 内字段 gap = 12px（0.75rem）** |
| 区块之间 | `--space-5`–`--space-6` |
| 媒体网格 | `--app-video-grid-gap*` |

### 4.2 Radius

| Token | 值 | 用途 |
|-------|-----|------|
| `--radius-sm` | 4px | 控件内 item、小芯片 |
| `--radius-md` / `--radius` | 6px | 按钮、输入、Select、Toolbar 控件 |
| `--radius-lg` | 8px | 面板、Popover、Dialog 外壳 |
| `--radius-xl` / `--app-card-radius` | 10px | 媒体卡片 |

### 4.3 控件高度（Density）

| 名称 | 高度 | 使用场景 |
|------|------|----------|
| **Dense** | 32px（`h-8`） | 工具栏、筛选 Popover 内 Select、分段控件、图标按钮 sm |
| **Default** | 36px（`h-9`） | 设置表单、对话框主字段、侧栏项（`--sidebar-item-height`） |
| **Comfort** | 40px（`h-10`） | 少用：强调主 CTA、空状态按钮 |

**禁止：** Task 型 Popover 内继续用 Default 36px 堆出“表单草稿”感。

---

## 5. 层级与阴影

### 5.1 壳层：单画布

- Title bar、主工作区、页头、工具栏：落在 `--background`（或透明叠在其上）。  
- 主侧栏：可用 `--sidebar` 轻抬升；**次栏（订阅列表、RSS 列表、设置 nav）透明 + 竖向 hairline**。  
- **禁止** 侧栏与工作区做成两块带 gap/圆角/投影的浮岛。  
- Shell 分区只用 `--app-hairline` / border，不用 `--card` 刷分区。

### 5.2 阴影词汇

| Token | 用途 |
|-------|------|
| `--app-surface-shadow` | 轻表面（表格壳等），非 shell |
| `--app-panel-shadow` | 中等面板 |
| `--app-floating-shadow`（Tailwind `shadow-popover`） | 菜单、筛选 Popover、下拉 |
| `--app-overlay-shadow` | Dialog / 重浮层 |
| `--brand-glow` / `--brand-glow-sm` | **仅品牌徽章** |

**规则：** 静止内容尽量靠色阶 + hairline；阴影只解释 **叠层、hover 抬起、品牌**。

### 5.3 Z-index

严格使用：`--z-content` → `--z-sticky` → `--z-header` → `--z-sidebar` → `--z-dropdown` → `--z-popover` → `--z-sheet` → `--z-dialog` → `--z-toast` → `--z-player-overlay`。  
禁止业务魔法数。

---

## 6. 动效

| Token | 值 | 用途 |
|-------|-----|------|
| `--duration-fast` | 120ms | hover、focus、Tab、开关 |
| `--duration-base` | 180ms | 面板显隐、页内过渡 |
| `--duration-slow` | 240ms | 大表面 |
| `--ease-default` / `--ease-out` | 见 layout.css | 标准 / 进入 |

- 尊重 `prefers-reduced-motion`。  
- 按压：`scale(0.985)`；禁用：`opacity: 0.4`（与 `--app-field-disabled-opacity` 一致）。

---

## 7. 组件规格

优先复用 `src/shared/ui` 与 `layout` 组件，**先找再造**。

### 7.1 Button

| Variant | 何时用 |
|---------|--------|
| `default`（primary） | 页内唯一主行动：保存、添加、确认 |
| `outline` / `secondary` | 次行动 |
| `ghost` | 工具栏、次要、图标+文字弱操作 |
| `destructive` | 删除等不可逆 |
| `link` | 行内文字链 |

- 形状：`--radius-md`；Default 高 36px；工具栏常用 `size="sm"`（32px）。  
- 焦点：`ring-2` + `--ring`；不要只改颜色无 ring。

### 7.2 Input / Select / Textarea

- 共享字段表面：`--app-field-bg`、`--app-field-border` 等。  
- Default 高 36px；**Toolbar / Filter 内 Select 用 Dense 32px + `text-xs`**。  
- Focus：border → ring，保留 ring，不用纯 glow 替代。

### 7.3 开关 Switch

- 用于二元且立即生效的偏好（如「仅特别关注」）。  
- 与说明文案组成 **toggle 行**（见 Pattern：Filter Popover），不要裸开关落在字段堆底部。

### 7.4 Tabs / Segmented

- 只用 `Tabs*` 或 `AppSegmentedControl`。  
- 紧凑轨 + 激活表面；禁止每页自绘第三种 Tab。

### 7.5 Badge / Chip

- 小圆角、1px 边、12px 字、低透明底。  
- 状态：文案 + 色，不只靠色。  
- 可移除筛选 Chip：outline + hover 可走向 destructive 提示。

### 7.6 Card / 媒体卡

- 应用表面 `--radius-lg`；媒体卡 `--radius-xl`。  
- 不嵌套“卡片套卡片”，除非内层是重复列表项。

### 7.7 Skeleton / Spinner / Toast / Empty

- Skeleton：仅 `AppSkeleton` + `--app-skeleton-*`。  
- Spinner：`--app-spinner-size-*`。  
- Toast：全局底右，`--z-toast`，语义分 success/error/info。  
- Empty：`AppEmptyState`；说明真实原因与下一步，禁止假数据遮丑。

### 7.8 Dialog / Popover / Menu

| 容器 | 用途 |
|------|------|
| Menu / Dropdown | 动作列表、排序短选项 |
| Popover | 筛选、状态摘要、轻量多字段 |
| Dialog | 确认、长表单、导入流程 |
| Sheet | 少用；需要时走 `--z-sheet` |

优先 **inline / Popover**，再 Modal。  
浮层 class：圆角 lg、border、`bg-popover`、`shadow-popover`。

---

## 8. 壳层与导航

### 8.1 桌面壳

固定结构：**Title bar → 主侧栏 → 顶栏（标题/搜索/用户）→ 滚动根 → 持久播放相关表面**。

- 前进/后退：应用级历史，不暴露浏览器历史心智。  
- 搜索：全局在顶栏（含 `Cmd/Ctrl+K`），不在侧栏重复一套。  
- 侧栏宽：`--sidebar-expanded-width`（15rem），**不随页面改几何**。  
- 折叠：工作区遮盖侧栏；被遮盖内容 `inert` 且移出 a11y 树。

### 8.2 Workbench

订阅 / 播放列表 / RSS / 设置等：**左列表 + 右内容**，中间一条竖线，次栏不铺 card 底。

### 8.3 页头与工具栏

- 页头：扁、底 hairline、不重复侧栏面包屑。  
- 工具栏控件：统一 `app-toolbar-control` / `app-toolbar-select-trigger` / `app-toolbar-icon-button`。  
- 组间可用 1px 竖线分隔（高约 16px）。

---

## 9. 交互模式（Patterns）

模式比单组件更重要。新功能先对模式，再填字段。

### 9.1 Toolbar Filter Popover（筛选）

**何时用：** 2 个以上筛选维度，或维度会按上下文显隐（来源 / 时间 / 时长 / 类型 / 分级 / 特别关注）。

**交互原则（重要）：**

- 筛选在 **同一 Popover 内完成选择**，**禁止** 再叠一层 Select 下拉（嵌套浮层难看、难扫、易被遮挡）。
- 少选项（≤6）用 **Chip 单选行**；带图标的长列表（站点）用 **面板内 OptionList**。
- 筛选即时生效，无「应用」按钮；条件数 > 0 显示「重置」。

**结构（必须）：**

```
PopoverContent（约 17.25rem，p-0，shadow-popover，overflow hidden）
└── AppFilterPanel
    ├── header：eyebrow「筛选」+ 计数 + 重置
    └── body
        ├── 来源 → AppFilterOptionList（3 列图标磁贴 + 短标签 + 角标 check）
        ├── 范围 → 时间 / 时长 两行（layout=row，标签左 + chip 轨右）
        ├── 类型 / 分级 → 次级 row chip
        └── 特别关注 → 底部分隔 + Switch
```

**实现锚点：**

| 部件 | 组件 / class |
|------|----------------|
| 壳 | `AppFilterPanel` |
| 分区 | `AppFilterSection`（`layout="row"` 用于条件轨） |
| Chip | `AppFilterChips` |
| 站点 | `AppFilterOptionList` 磁贴网格 + `SiteIcon` |
| 开关 | `.app-filter-toggle` |
| 触发器 | `.app-filter-toolbar-button` |

**视觉：**

- 站点选中：**白底抬起 + 中性描边 + 角标勾**，禁止 primary 整行洗色。  
- 条件轨：左短标签、右 segmented，避免三块同构「大段表单」。  
- 图标：`/api/sites/{slug}/icon` + `resolveServerAssetUrl`；失败用品牌 monogram。

**不要：**

- Popover 内堆 `Select` / `SelectTrigger` 做筛选维度  
- 长列表 + 散落 pill 的伪表单堆砌  
- 与排序、视图切换混在一个 Popover  
- 用无效 prop 导致站点图标全部 fallback

**有已选条件时：** 内容区可用 `ActiveFilters` Chip 回显；Chip 移除单项，面板「重置」清全部。

### 9.2 排序 vs 筛选

- **筛选：** 缩小集合（来源、时间、时长…）→ Filter Popover。  
- **排序：** 不缩小集合 → 工具栏独立 Select，不要塞进筛选面板。

### 9.3 媒体网格

- `.app-video-grid` / `--feed` / `--compact`；用 `--app-grid-min` 调密度。  
- 不要每页手写 `grid-cols-1 sm:… 3xl:…` 长链。

### 9.4 空态 / 错态 / 加载

| 状态 | 要求 |
|------|------|
| Loading | 区域级 Skeleton 或 Block loader，避免整页无意义闪白 |
| Empty | 标题 + 原因 + 可行动作（清空筛选 / 去添加） |
| Error | 具体错误与重试；禁止“出了点问题”掩盖 runtime/auth |

### 9.5 运维状态

连接、同步、任务结果：`success` / `warning` / `destructive` + 文案（及可选图标）。  
**在线/健康 ≠ primary。**

---

## 10. 无障碍

- 目标 **WCAG 2.1 AA** 对比度。  
- 自定义控件必须有可见 `:focus-visible`。  
- 状态不只靠颜色（辅以文字、图标、角标）。  
- 图标按钮要有 `aria-label` / `title`。  
- 筛选触发器在激活时应反映数量（如 `aria-label="筛选，已启用 N 项"`）。

---

## 11. 决策树（速查）

```
新 UI 需求
  ├─ 改壳层结构？ → 否：保持单画布；是：先改 layout 规范再改页面
  ├─ 需要强调色？
  │    ├─ 主行动 / 选中 / 已筛选 / 焦点 → primary
  │    ├─ 成功 / 健康 → success
  │    ├─ 警告 → warning
  │    └─ 危险 → destructive
  ├─ 多条件筛选？ → Pattern 9.1 AppFilterPanel，禁止页内私有 panel 样式
  ├─ 仅排序？ → 工具栏 Select，不进筛选
  ├─ 控件高度？
  │    ├─ 工具栏 / 筛选浮层 → 32px
  │    └─ 设置表单 / 对话框 → 36px
  ├─ 已有 Button/Input/Select/Tabs/AppSkeleton/AppEmptyState/AppFilterPanel？
  │    └─ 有则复用，禁止平行组件
  └─ 现有页面很丑？
       └─ 按本规格重做该 Surface/Pattern，不复制错误当规范
```

---

## 12. 明确禁止

1. 移动优先断点堆叠（除非需求显式要求移动端）。  
2. 侧栏 + 工作区双浮岛（padding + gap + 双圆角阴影）。  
3. workbench 次栏 `--card` 刷底。  
4. 装饰性大渐变字、无意义 glass、斜线纹理、仪表盘假指标。  
5. 色条侧边告警卡（用全边框 + 图标 + 文案）。  
6. 未激活 UI 高饱和、高对比。  
7. 用 primary 表示“正常/已连接”。  
8. 业务页私有筛选面板样式（必须 `AppFilterPanel` + `app-filter-*`）。  
9. 新 z-index / 新 spacing 刻度不进 `layout.css`。  
10. 用假 UI 掩盖缺数据、runtime 失败、鉴权失败。

---

## 13. 与 PRODUCT 的关系

- `PRODUCT.md`：用户、目的、品牌个性、产品原则。  
- `DESIGN.md`（本文）：**如何画、如何选组件、如何用 token**。  

产品原则冲突时：以可操作性与 token 一致性为准，并同时更新两份文档中的对应句，避免“气质形容词”直接驱动实现。

---

## 14. 修订规则

1. **Token 变更：** 先改 `layout.css` / `themes/dark.css`，再改本文对应表。  
2. **新模式：** 先在 `shared/components` 落地，再写入第 9 节。  
3. **禁止** 只改文案口号不改可执行条款。  
4. 本文中文为主；代码标识符保持与仓库一致的英文 class / token 名。
