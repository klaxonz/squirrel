# Standards

← [目录](./README.md)

本文是**必须执行的界面设计标准（S1–S4）**。  
实现、评审、改视觉只依据下列条款与验收清单。形容词（高级、干净）不能替代条款。

**产品是什么、主链怎么走、页面谁主谁次** → 仓库 [README](../../../README.md)。  
**设计标准**只回答：界面必须用什么规格来做。二者不混写。

冲突时：以本页 + foundations/patterns 的可执行条款为准；代码 token 与文档不一致时先对齐再合入。

---

## 产品上下文（非条款）

Squirrel（归仓）的产品定义见 README：自托管多站视频订阅中枢。  
设计系统在该产品上落地时，默认有三类界面工作（对应 S1 Surface），**不是**产品路径分级：

| 界面工作 | 用户在干什么 | Surface |
|----------|--------------|---------|
| 看 / 听 / 读 | 浏览封面与正文、播放 | **Consume** |
| 订 / 筛 / 标 / 整理 | 订阅、筛选、列表状态 | **Organize** |
| 修管道 / 改配置 | 站点、任务、日志、设置 | **Operate** |

页面清单与导航结构见 [Shell](./patterns/shell.md)。产品叙事变更改 README；界面规格变更改本页与 Pattern。

---

## S1 · Surface 规格

**标准：** 每个页面（或页面主区域）必须归属且仅使用下列三种 Surface 之一。全站共用同一套 token 与 `shared/ui` / layout Pattern。

| Surface | 何时用 | 控件高 | 主行动 | 选中 / 当前 | 层次手段 |
|---------|--------|--------|--------|-------------|----------|
| **Consume** | 以观看、收听、阅读为主 | chrome 轻；CTA 可用 Comfort 40px | 每页 1 个 primary（播放 / 主 CTA） | `--app-selection-*` | 同色温 scrim、封面对比、`shadow-card-hover` 抬升 |
| **Organize** | 以订阅、筛选、标记、整理列表为主 | 工具栏 / 筛选 **32px** Dense | 每页 1 个 primary | `--app-selection-*` | hairline 分区 |
| **Operate** | 以配置、任务、日志、站点运维为主 | 表单字段 **36px** Default | 按表单提交需要 | `--app-selection-*` | 语义色 + 字阶 |

**混合页：** 以主停留区域定 Surface；次区域用对应控件高（例：Consume 页内筛选条 = Organize 32px）。

**组件来源：** 按钮、筛选、空态、工具栏 class 必须来自 `shared/ui` 与已文档化 Pattern；新能力先扩展 shared，再被业务引用。

**验收**

- [ ] 页面可指出所属 Surface
- [ ] 控件高度、主行动数量、选中 token 与上表一致
- [ ] 无业务页私有第二套 Button / 筛选 / 空态组件
- [ ] Operate 的密度与语义色用法未铺满 Consume / Organize 整页

细则 → [Shell](./patterns/shell.md)

---

## S2 · 色意映射

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

## S3 · 状态完整性

**标准：** 每个异步或可失败区域必须具备加载、空、错误三种可感知状态；同步失败、鉴权失败、站点不可用必须展示原因与可执行下一步。

| 状态 | 必须具备 |
|------|----------|
| Loading | 区域级 Skeleton 或 Block loader（形状贴近终态） |
| Empty | 标题 + 原因 + 下一步动作 |
| Error | 具体原因 + 恢复动作（重试 / 登录 / 查看日志等） |
| 同步 / 运维结果 | success / warning / destructive + 文案 |

数据缺失时展示真实空/错状态，不使用占位假内容冒充已加载数据。

**验收**

- [ ] 主列表与主详情均有 loading / empty / error 路径
- [ ] 失败态提供可执行下一步（重试或明确去向）
- [ ] 空态与错误文案符合 [Content](./content.md)

细则 → [States](./patterns/states.md)

---

## S4 · 视觉系统一致性

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

1. 新 UI / 改视觉：先定 **S1 Surface**，再落 token 与 Pattern。  
2. 评审：用各节 **验收** 清单勾选；未勾选项必须改到符合再合入。  
3. 扩展系统：按 [Governance](./governance.md) 更新 token/组件/文档同一变更集。  
4. 产品定义变更：改 README，不把产品路径表写进本标准。
