# 意图 → 标准实现

← [目录](./README.md)

查表即规格。产品主链见 [README](../../../README.md)。原则见 [Principles](./principles.md)。

| 意图 | 标准实现 | 依据 |
|------|----------|------|
| 定页面密度 / 强调 | 声明 Surface：Consume / Organize / Operate | [Spec 1](./standards.md#spec-1--surface) · [Surface](./patterns/surface.md) |
| 查某路由 Surface | [Surface 落地表](./patterns/surface.md#当前应用页面--surface) | Pattern |
| 订阅工作台 | Organize · Dense 32px | Spec 1 |
| 首页 / 视频库 / 播放 | Consume | Spec 1 |
| 站点 / 定时 / 日志 / 设置 | Operate · 36px 字段 | Spec 1 |
| 页内主行动 | `Button` `default`，每视图 1 个 | Spec 2 · P2 |
| 工具栏次要操作 | `ghost` / `outline` | Spec 1 Organize |
| 导航当前 / 列表选中 / 筛选触发器开 | `--app-selection-*` / `.is-active` | Spec 2 · [Color](./foundations/color.md) |
| 筛选面板内 segment / tile 当前 | `--app-filter-raised-*`（tile 边 selection） | Spec 2 · [Filter](./patterns/filter-popover.md) |
| Consume scrim | `background` / `overlay` 的 alpha | Spec 2 |
| 卡焦点抬升 | `shadow-card-hover` + transform | Spec 1 · [Elevation](./foundations/elevation.md) |
| 健康 / 成功 | `--success` + 文案 | Spec 2 |
| 警告 | `--warning` + 文案 | Spec 2 |
| 删除 | `destructive` | Spec 2 |
| 多条件筛选 | `AppFilterPanel` · 32px | Spec 1 · [Filter](./patterns/filter-popover.md) |
| 仅排序 | 工具栏 `Select` | Filter |
| 媒体墙 | `.app-video-grid*` | Spec 4 · [Media grid](./patterns/media-grid.md) · [Media craft](./patterns/media-craft.md) |
| 视频卡品质 | 16:9、标题 2 行、层级、同色温 scrim | [Media craft](./patterns/media-craft.md) |
| 视频卡次要操作 | flag + meta ghost + 右键 | [Media card actions](./patterns/media-card-actions.md) |
| 首页 | FreeTube 堆叠 rail（无 hero 舞台 / 侧队列） | [Media craft · 首页 feed](./patterns/media-craft.md#4-首页-feedfreetube--无-hero-舞台) |
| 空 / 加载 / 错 | `AppEmptyState` / Skeleton / 原因+动作 | Spec 3 · [States](./patterns/states.md) |
| 新 token | 先 foundations，再引用 | Spec 4 · [Token 分层](./foundations/README.md#token-分层) · [Governance](./governance.md) |

验收清单：[Standards](./standards.md)
