# UI 体系收口计划（UI System Consolidation Plan）

> 状态：待执行　|　分支基线：`redesign/impeccable-layout-overhaul`　|　创建：2026-08-29
>
> 背景：renderer 已有 shadcn-vue + reka-ui 路线的 `shared/ui` 组件库和三层设计 token
> （语义色 / 间距·层级·动效 / app chrome）。本计划的目标不是重建体系，而是收口最后 20%
> 的漂移：文字 scale、组件覆盖缺口、Button 双轨 API、播放器子主题声明、成文约定与画廊。

## 现状盘点结论（2026-08-29 实测数据）

| # | 问题 | 影响面（实测） |
|---|------|----------------|
| 1 | 字号无 scale token，裸写 `font-size` | 414 处 / 100 个文件；`0.75rem`×127、`0.6875rem`×88、`0.8125rem`×61、`0.875rem`×47，且混用 `11–15px` |
| 2 | shared/ui 缺组件，feature 自制浮层/菜单 | 无 DropdownMenu、Tooltip、Tabs、Slider；feature 侧 4 处 `Teleport` + 7 处 `position:fixed` 自制浮层（MusicQueuePanel、MusicImmersivePlayer、RssImageLightbox、YouTubeOAuthPrompt、ServerStatusButton、ChapterOverlay 等） |
| 3 | Button 双轨 API | `severity=` 有 **228 处在用**；`link/text/outlined` 为 **0 处** → 应保留 severity 方向、删除无人用的三别名 |
| 4 | 播放器第二套 token 未声明 | `video-player/themes/` 4 个 css，`--sp-*` 181 处引用，桥接点 `hsl(var(--primary))` 分散 |
| 5 | 体系零文档、无画廊 | `app/dev/` 为空；adr 仅 3 篇 playback 相关 |

token 使用基线：`var(--…)` 共约 2950 处（--app-*×611、语义色 --muted/--foreground 等、--space-*×377、--sp-*×181），token 化程度高，无需返工。

---

## Phase 1 — 文字 Scale Token（收益最大，先行）

**目标**：消灭 414 处裸 `font-size`，建立唯一文字 scale。

1. 在 `shared/styles/layout.css` 定义 scale（沿用现有 `--app-text-*` 命名，扩全档位）：
   ```css
   --app-text-2xs: 0.625rem;   /* 10px，徽标极小字 */
   --app-text-xs: 0.6875rem;   /* 11px，badge/muted（复用现 --app-text-badge-size） */
   --app-text-sm: 0.75rem;     /* 12px，次要文字（复用 --app-text-secondary-size） */
   --app-text-md: 0.8125rem;   /* 13px */
   --app-text-base: 0.875rem;  /* 14px，正文（复用 --app-text-body-size） */
   --app-text-lg: 1rem;        /* 16px */
   --app-text-xl: 1.125rem;    /* 18px */
   --app-text-2xl: 1.25rem;
   ```
   旧三个变量改为别名指向新档位，保持兼容。
2. **codemod**（scripts/ 下一次性 Node 脚本）：按映射表替换裸值 → token。
   `0.625rem→2xs, 0.6875rem→xs, 0.75rem→sm, 0.8125rem→md, 0.875rem→base, 1rem→lg, 1.125rem→xl, 1.25rem→2xl`；
   `11px→var(--app-text-xs)`、`12px→sm`、`13px→md`、`14px→base`、`15px→lg`；
   非档位值（`0.9375rem`、`0.95rem`）就近归档。
3. **防回潮**：ESLint 自定义规则或 CI grep gate —— `src/features/**` 与 `src/app/**` 出现 `font-size:\s*[0-9]` 即失败（shared/ui 与 video-player themes 豁免）。

**验收**：全库（除豁免目录）`grep -rE "font-size:\s*[0-9]"` 为 0；typecheck + 渲染截图抽查 RSS/视频/音乐/设置四页无视觉回归。

## Phase 2 — 补齐 shared/ui 缺口 + 收编浮层

**目标**：feature 不再自制浮层/菜单，弹层一律走体系组件。

1. **新增组件**（全部按现有 shadcn-vue + reka-ui + `sq-*` 模式）：
   - `DropdownMenu`（reka-ui DropdownMenuRoot，收编 AppContextMenu 的定位逻辑 `useContextMenuPosition`/`usePointerOutside`）
   - `Tooltip`（reka-ui TooltipRoot）
   - `Tabs`（reka-ui TabsRoot；收编 AppSectionNav 的样式 token）
   - `IconButton`（独立组件或 Button 专属形态，统一现有手写 icon button 的 36×36/圆形/hover token）
   - `Skeleton`：将 `shared/components/AppSkeleton`、`AppSkeletonText`、`AppSpinner`、`AppBounceDots` 迁入 `shared/ui/`，旧路径 re-export 一个版本后删除
2. **收编自制浮层**（每处独立 PR，可逐个验视觉）：
   - `YouTubeOAuthPrompt`、`RssImageLightbox` → `shared/ui/dialog`
   - `MusicQueuePanel`、`MusicImmersivePlayer` 的 fixed 弹层 → Dialog/Popover
   - `ServerStatusButton` 菜单 → Popover/DropdownMenu
   - `GlobalVideoPlayerHost`、`ChapterOverlay`、ToastProvider、AppContextMenu、`VideoItem` 悬浮预览 **保留** Teleport —— 前者是全屏媒体宿主与 toast 基础设施，属合理的体系内实现；在文档中声明为白名单
3. **防回潮**：CI gate —— `src/features/**` 禁止新增 `Teleport` 与 `position:\s*fixed`（白名单文件列表固化在脚本里）。

**验收**：白名单外 grep 为 0；抽查各弹层层级符合 `--z-*` 表（dialog 1300 / toast 1400 / player-overlay 1500）。

## Phase 3 — Button API 收敛

**目标**：单一 variant API，删除死代码别名。

1. 方向以数据为准：**保留 `severity`**（228 处在用），**删除 `link/text/outlined`**（0 处）及 `resolvedVariant` 中对应桥接分支。
2. `severity` 与 `variant` 语义合并：将 severity 的合法档位并入 `ButtonVariant` 类型（`default | secondary | destructive | contrast | success | info | warn | help`），`severity` 变为 deprecated 别名，codemod `severity="x"` → `variant="x"`（228 处机械替换），然后删除 severity prop。
3. 验收：`grep -rn "severity=" src/` 为 0；`grep -rnE "(link|text|outlined)=" 指向 Button 的调用` 为 0；Button.vue 不再含 resolvedVariant 桥接 computed。

## Phase 4 — 播放器子主题显式化

**目标**：`--sp-*` 从"事实上存在"变为"被声明的子主题"。

1. `video-player/themes/variables.css` 头部加注释块，声明其为 player-scoped sub-theme、与主 token 的桥接契约。
2. 桥接点收敛：所有 `hsl(var(--primary))` 式主 token 引用集中到 variables.css 一处（其余 `--sp-*` 只引用 `--sp-theme-*` 间接层），子主题外不得直接读主语义色。
3. 豁免声明：video-player 目录在 Phase 1/2 的 CI gate 中作为"已声明的独立子主题"豁免，理由写入文档（媒体 chrome 需不透明、常驻黑色背景）。
4. 验收：variables.css 之外 `grep "hsl(var(--" video-player/` 为 0。

## Phase 5 — 约定成文 + 组件画廊

**目标**：让体系和规矩可被发现，防再度发散。

1. **ADR-0004 `ui-system-and-tokens.md`**：记录三层 token 架构、shared/ui vs shared/components 两层分工、`sq-*` 前缀规则、播放器子主题、弹层白名单、"禁止裸写字号/颜色/自制浮层"三条硬规矩。
2. **组件画廊路由**（`app/dev/`，仅 dev 构建注册）：展示全部 shared/ui 组件的各 variant/size/token 档位，作为视觉回归抽查基准页。
3. `renderer/README.md` 增补"如何新增 UI 组件 / 何时进 shared/ui vs feature"一节。

**验收**：ADR 合入；`npm run dev` 可访问画廊路由看到全部组件。

---

## 执行顺序与工作量估计

| Phase | 依赖 | 规模 | 备注 |
|-------|------|------|------|
| 1 文字 scale | 无 | ~1–2 天（codemod + 视觉抽查） | 先行，机械收益最大 |
| 2 组件补齐 | 无（可与 1 并行） | ~3–5 天（4 个新组件 + 收编浮层逐个 PR） | 新组件先行，收编浮层按文件逐个做 |
| 3 Button 收敛 | 无（可并行） | ~0.5 天（机械 codemod） | 228 处替换 + 类型收口 |
| 4 播放器子主题 | 无 | ~0.5 天 | 纯注释 + 桥接点搬迁 |
| 5 文档 + 画廊 | 依赖 1–4 定型 | ~1 天 | 最后写，避免返工 |

每个 Phase 独立成 commit/PR；每步验收跑 `npm run typecheck` + 目标页面截图对比（e2e-shots/ 流程）。
