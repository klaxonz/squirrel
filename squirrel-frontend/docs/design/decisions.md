# 意图 → 标准实现

← [目录](./README.md)

查表即标准。左列是意图，右列是**必须使用**的实现。

| 意图 | 标准实现 | 条款 |
|------|----------|------|
| 定产品路径 | 主 / 辅 / 支撑 / 附属（归仓主链） | [S1](./principles.md#s1--产品身份) |
| 定页面规格 | 声明 Surface：Consume / Organize / Operate | [S2](./principles.md#s2--surface-规格) · [Shell](./patterns/shell.md) |
| 订阅工作台 | Organize · Dense 32px · 添加/导入为主行动之一 | S1 主路径 · S2 |
| 首页 / 视频库 / 播放 | Consume · 内容与播放优先 | S1 主路径 · S2 |
| 站点 / 定时 / 日志 / 设置 | Operate · 36px 字段 · 语义色状态 | S1 支撑 · S2 |
| 页内主行动 | `Button` `variant="default"`（primary），每视图 1 个 | S3 |
| 工具栏次要操作 | `Button` `ghost` 或 `outline` | S2 Organize |
| 导航当前 / 列表选中 / 筛选开启 | `--app-selection-*` 或 `.is-active` 工具栏 class | S3 · [Color](./foundations/color.md) |
| Consume 舞台 / 封面遮罩 | `hsl(var(--background) / α)` 或 `hsl(var(--overlay) / α)` | S3 · Color |
| Consume 卡焦点抬升 | `shadow-card-hover` + transform | S2 · [Elevation](./foundations/elevation.md) |
| 健康 / 在线 / 成功 | `--success` + 文案（可加图标） | S3 |
| 警告 / 降级 / 同步部分失败 | `--warning` + 文案 | S3 |
| 删除 / 不可恢复 | `destructive` 变体或 `--destructive` | S3 |
| 多条件筛选 | `AppFilterPanel` Pattern · Dense 32px | S2 · [Filter](./patterns/filter-popover.md) |
| 仅排序 | 工具栏 `Select`（独立于筛选面板） | Filter Pattern |
| Organize 工具栏控件高 | **32px** Dense | S2 |
| Operate 表单字段高 | **36px** Default | S2 |
| 媒体墙 | `.app-video-grid` / `--feed` / `--compact` | S5 · [Media grid](./patterns/media-grid.md) |
| 视频卡次要操作 | 缩略图 flag + meta ghost 切换 + 右键菜单 | [Media card actions](./patterns/media-card-actions.md) |
| 空列表 | `AppEmptyState`：标题 + 原因 + 下一步 | S4 · [States](./patterns/states.md) |
| 区域加载 | `AppSkeleton` / `AppBlockLoader` | S4 |
| 同步/站点失败 | 原因 + 重试或导向站点/日志 | S4 |
| 新颜色 / 新间距 / 新 z | 写入 `layout.css` 或 `themes/dark.css` 后使用 | S5 · [Governance](./governance.md) |

完整条款与验收：[Standards](./principles.md)
