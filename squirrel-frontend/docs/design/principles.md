# Standards

← [目录](./README.md)

本文是**必须执行的标准（S1–S5）**。  
实现、评审、改视觉只依据下列条款与验收清单。形容词（高级、干净）不能替代条款。

产品叙事与仓库根目录 [README](../../../README.md) 一致。冲突时：以本页 + foundations/patterns 的可执行条款为准；代码 token 与文档不一致时先对齐再合入。

---

## S1 · 产品身份

**标准：** Squirrel（归仓）是**自托管的多站视频订阅中枢**。  
界面必须服务这条主链：

```
多站订阅 / 导入 → 同步入库 → 浏览 · 未读 · 稍后看 → 播放
```

站点会话、定时任务、日志保证管道可用，是**支撑路径**，不定义整站气质。  
RSS、音乐是**同壳附属**，不参与定义主身份。

| 路径等级 | 页面范围 | 设计目标（必须达到） |
|----------|----------|----------------------|
| **主路径** | 订阅、首页、视频库、播放 | 内容进得来、扫得清、状态可处理（未读/稍后等）、点得开播 |
| **辅路径** | 筛选工具、历史、播放列表 | 可扫、可筛、可整理；工具栏 Dense 规格 |
| **支撑路径** | 站点、定时任务、日志、设置 | 管道可修；状态真实；错误可恢复 |
| **附属** | RSS、音乐 | 遵守同一 token / 组件；不改变主路径规格 |

**验收**

- [ ] 主路径页面的第一视觉焦点是入库内容、订阅对象或播放主体（不是运维指标墙）
- [ ] 订阅 → 库 → 播放链路在信息架构上连续（侧栏与页内入口可完成，不依赖隐藏运维页）
- [ ] 支撑路径可独立完成排障（登录/任务/日志），且不把 Operate 规格铺到主路径整页
- [ ] 附属页不引入第二套视觉系统

---

## S2 · Surface 规格

**标准：** 每个页面（或页面主区域）必须归属且仅使用下列三种 Surface 之一的规格。全站共用同一套 token 与 `shared/ui` / layout Pattern。

Surface 描述**界面规格**，与 S1 路径等级配合使用（例：主路径里的视频库 = Consume；主路径里的订阅工作台 = Organize）。

| Surface | 适用 | 控件高 | 主行动 | 选中 / 当前 | 层次手段 |
|---------|------|--------|--------|-------------|----------|
| **Consume** | 首页、视频墙、播放器；附属：音乐、RSS 阅读 | chrome 轻；CTA 可用 Comfort 40px | 每页 1 个 primary（播放 / 主 CTA） | `--app-selection-*` | 同色温 scrim、封面对比、`shadow-card-hover` 抬升 |
| **Organize** | 订阅工作台、筛选、列表批处理、历史、播放列表 | 工具栏 / 筛选 **32px** Dense | 每页 1 个 primary | `--app-selection-*` | hairline 分区 |
| **Operate** | 站点、定时任务、日志、设置 | 表单字段 **36px** Default | 按表单提交需要 | `--app-selection-*` | 语义色 + 字阶 |

**混合页：** 以用户主停留区域定 Surface；次区域采用对应 Surface 的控件高（例：Consume 页内筛选条 = Organize 32px）。

**组件来源：** 按钮、筛选、空态、工具栏 class 必须来自 `shared/ui` 与已文档化 Pattern；新能力先扩展 shared，再被业务引用。

**验收**

- [ ] 页面可指出所属 S1 路径等级与 S2 Surface
- [ ] 控件高度、主行动数量、选中 token 与上表一致
- [ ] 无业务页私有第二套 Button / 筛选 / 空态组件

细则 → [Shell](./patterns/shell.md)

---

## S3 · 色意映射

**标准：** 每一种界面意图只映射到下表中的一类 token。业务样式只使用语义 token（`hsl(var(--…))` 或已定义的完整值 token），色相轴为 H28 暖中性。

| 意图 | 必须使用的 token |
|------|------------------|
| 画布 / 正文 | `--background` / `--foreground` |
| 主行动、焦点环、播放强调、品牌徽章 | `--primary` / `--ring` / 品牌梯度 token |
| 导航当前、列表选中、筛选开启、chip active | `--app-selection-*`（完整值，见 Color） |
| 健康 / 在线 / 成功 | `--success` + 文案或图标 |
| 警告 / 降级 | `--warning` + 文案或图标 |
| 危险 / 删除 | `--destructive` |
| Consume 舞台与封面 scrim | `hsl(var(--background) / α)` 或 `hsl(var(--overlay) / α)` |
| 结构线 | `--border` / `--app-hairline` |

**主行动数量：** 同一视图内 primary 实心主按钮至多 1 个。

**验收**

- [ ] 选中 / 当前态仅出现 `--app-selection-*` 视觉
- [ ] 健康态仅出现 success（或等价语义）+ 文案
- [ ] scrim / 遮罩可追溯到 background 或 overlay token
- [ ] 业务文件无裸 hex / 无 HSL 通道外的随意色（集中定义的品牌梯度除外）

细则 → [Color](./foundations/color.md)

---

## S4 · 状态完整性

**标准：** 每个异步或可失败区域必须具备加载、空、错误三种可感知状态；同步失败、鉴权失败、站点不可用必须展示原因与可执行下一步。

| 状态 | 必须具备 |
|------|----------|
| Loading | 区域级 Skeleton 或 Block loader（形状贴近终态） |
| Empty | 标题 + 原因 + 下一步动作（例：去添加订阅、清空筛选） |
| Error | 具体原因 + 恢复动作（重试 / 登录站点 / 查看日志等） |
| 同步 / 运维结果 | success / warning / destructive + 文案 |

数据缺失时展示真实空/错状态，不使用占位假内容冒充已加载数据。

**验收**

- [ ] 主列表与主详情均有 loading / empty / error 路径
- [ ] 订阅同步与站点相关失败可导向支撑路径中的可操作修复
- [ ] 空态与错误文案符合 [Content](./content.md)

细则 → [States](./patterns/states.md)

---

## S5 · 视觉系统一致性

**标准：** 下列项全站统一；缺任一条款视为不符合标准。

| 项 | 必须 |
|----|------|
| 字体 | `--font-sans` 为明确 UI 家族；`--font-display` 在字重或 tracking 上与 body 可区分；优先自托管 |
| 字阶 | 使用 `--app-h*` / Hero 规格；同一工具栏 ≤ 两档字号 |
| 圆角 | sm 4 / md 6 / lg 8 / xl 10（媒体卡 xl） |
| 媒体网格 | `.app-video-grid*` + `--app-grid-min`；封面比例在同类卡内一致 |
| 焦点 | 可交互元素具备 `:focus-visible` 环（`--ring`） |
| 色温 | 全站 H28 轴；Dark/Light 只调明度与饱和 |
| 阴影与 z | 使用 layout 中的 shadow / `--z-*` 阶 |
| 动效 | `--duration-*` / `--ease-*`；尊重 `prefers-reduced-motion` |

**验收**

- [ ] display 与 sans 在计算样式上可区分
- [ ] 新媒体卡 round / gap 与 token 一致
- [ ] 无业务魔法 z-index、无随机圆角阶

细则 → [Typography](./foundations/typography.md) · [Spacing](./foundations/spacing.md) · [Elevation](./foundations/elevation.md) · [Motion](./foundations/motion.md)

---

## 使用方式

1. 新 UI / 改视觉：先定 **S1 路径等级 + S2 Surface**，再落 token 与 Pattern。  
2. 评审：用各节 **验收** 清单勾选；未勾选项必须改到符合再合入。  
3. 扩展系统：按 [Governance](./governance.md) 更新 token/组件/文档同一变更集。
