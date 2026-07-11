# 意图 → 标准实现

← [目录](./README.md)

查表即标准。左列是界面意图，右列是**必须使用**的实现。  
产品主链与部署见 [README](../../../README.md)，不在本表。

| 意图 | 标准实现 | 条款 |
|------|----------|------|
| 定页面规格 | 声明 Surface：Consume / Organize / Operate | [S1](./principles.md#s1--surface-规格) · [Shell](./patterns/shell.md) |
| 查某路由用哪套 Surface | [Shell · 页面 → Surface](./patterns/shell.md#当前应用页面--surface) | Pattern |
| 订阅工作台 | Organize · Dense 32px | S1 |
| 首页 / 视频库 / 播放 | Consume | S1 |
| 站点 / 定时 / 日志 / 设置 | Operate · 36px 字段 | S1 |
| 页内主行动 | `Button` `variant="default"`（primary），每视图 1 个 | S2 |
| 工具栏次要操作 | `Button` `ghost` 或 `outline` | S1 Organize |
| 导航当前 / 列表选中 / 筛选开启 | `--app-selection-*` 或 `.is-active` | S2 · [Color](./foundations/color.md) |
| Consume 舞台 / 封面遮罩 | `hsl(var(--background) / α)` 或 `hsl(var(--overlay) / α)` | S2 · Color |
| Consume 卡焦点抬升 | `shadow-card-hover` + transform | S1 · [Elevation](./foundations/elevation.md) |
| 健康 / 在线 / 成功 | `--success` + 文案 | S2 |
| 警告 / 降级 | `--warning` + 文案 | S2 |
| 删除 / 不可恢复 | `destructive` 或 `--destructive` | S2 |
| 多条件筛选 | `AppFilterPanel` · Dense 32px | S1 · [Filter](./patterns/filter-popover.md) |
| 仅排序 | 工具栏 `Select` | Filter Pattern |
| 媒体墙 | `.app-video-grid*` | S4 · [Media grid](./patterns/media-grid.md) |
| 视频卡次要操作 | flag + meta ghost + 右键菜单 | [Media card actions](./patterns/media-card-actions.md) |
| 空列表 | `AppEmptyState`：标题 + 原因 + 下一步 | S3 · [States](./patterns/states.md) |
| 区域加载 | `AppSkeleton` / `AppBlockLoader` | S3 |
| 同步/站点失败 | 原因 + 可执行下一步 | S3 |
| 新 token | 写入 foundations 后再引用 | S4 · [Governance](./governance.md) |

完整条款与验收：[Standards](./principles.md)
