# Standards（强制规格）

← [目录](./README.md)

本页是**必须执行的界面规格**。合入前用验收清单勾选。  
设计原则（两难取舍）→ [principles.md](./principles.md)  
产品定义 → [README](../../../README.md)

冲突时：以本页 + foundations/patterns 与代码 token 为准；文档与代码不一致时先对齐再合入。

---

## Spec 1 · Surface

**标准：** 每个页面（或页面主区域）必须归属且仅使用一种 [Surface](./patterns/surface.md)：`Consume` | `Organize` | `Operate`。  
全站共用同一套 token 与 `shared/ui` / layout Pattern。

Surface 定义密度、主行动数量、选中态与层次手段。完整表与页面落地表见 Pattern，不在此重复产品路径。

**验收**

- [ ] 页面可指出所属 Surface
- [ ] 控件高度、主行动、选中 token 符合该 Surface
- [ ] 无业务页私有第二套 Button / 筛选 / 空态
- [ ] Operate 规格未铺满 Consume / Organize 整页
- [ ] 含媒体呈现的 Consume 面（及 Organize 内视频卡）通过 [Media craft](./patterns/media-craft.md) 相关验收

→ [Surface](./patterns/surface.md) · [Media craft](./patterns/media-craft.md) · [Shell](./patterns/shell.md)

---

## Spec 2 · 色意映射

**标准：** 每一种界面意图只映射到下表中的一类 **system token**。业务样式只使用语义 token（`hsl(var(--…))` 或已定义的完整值 token）。色相轴：H28 暖中性。

| 意图 | 必须使用的 token |
|------|------------------|
| 画布 / 正文 | `--background` / `--foreground` |
| 主行动、焦点环、播放强调、品牌徽章 | `--primary` / `--ring` / 品牌梯度 token |
| 导航当前、列表选中、筛选开启、chip active | `--app-selection-*` |
| 健康 / 在线 / 成功 | `--success` + 文案或图标 |
| 警告 / 降级 | `--warning` + 文案或图标 |
| 危险 / 删除 | `--destructive` |
| Consume 舞台与封面 scrim | `hsl(var(--background) / α)` 或 `hsl(var(--overlay) / α)` |
| 结构线 | `--border` / `--app-hairline` |

**主行动数量：** 同一视图内 primary 实心主按钮至多 1 个。

**验收**

- [ ] 选中 / 当前态仅使用 `--app-selection-*`
- [ ] 健康态仅使用 success + 文案
- [ ] scrim 可追溯到 background 或 overlay
- [ ] 业务无裸 hex / 随意 hsl（集中定义的品牌梯度除外）

→ [Color](./foundations/color.md) · [Token 分层](./foundations/README.md#token-分层)

---

## Spec 3 · 状态完整性

**标准：** 每个异步或可失败区域必须具备加载、空、错误三种可感知状态；同步失败、鉴权失败、站点不可用必须展示原因与可执行下一步。

| 状态 | 必须具备 |
|------|----------|
| Loading | 区域级 Skeleton 或 Block loader（形状贴近终态） |
| Empty | 标题 + 原因 + 下一步动作 |
| Error | 具体原因 + 恢复动作 |
| 同步 / 运维结果 | success / warning / destructive + 文案 |

禁止用占位假内容冒充已加载数据。

**验收**

- [ ] 主列表与主详情均有 loading / empty / error
- [ ] 失败态有可执行下一步
- [ ] 文案符合 [Content](./content.md)

→ [States](./patterns/states.md)

---

## Spec 4 · 视觉系统一致性

**标准：** 下列项全站统一；缺任一条款视为不符合规格。

| 项 | 必须 |
|----|------|
| 字体 | `--font-sans` 明确 UI 家族；`--font-display` 与 body 在字重或 tracking 上可区分；优先自托管 |
| 字阶 | `--app-h*` / Hero；同一工具栏 ≤ 两档字号 |
| 圆角 | sm 4 / md 6 / lg 8 / xl 10（媒体卡 xl） |
| 媒体网格 | `.app-video-grid*` + `--app-grid-min`；同类卡封面比例一致 |
| 焦点 | 可交互元素 `:focus-visible` + `--ring` |
| 色温 | 全站 H28；Dark/Light 只调明度与饱和 |
| 阴影与 z | layout 中的 shadow / `--z-*` |
| 动效 | `--duration-*` / `--ease-*`；尊重 `prefers-reduced-motion` |

**验收**

- [ ] display 与 sans 在计算样式上可区分
- [ ] 新媒体卡 round / gap 与 token 一致
- [ ] 无业务魔法 z-index、无随机圆角阶

→ [Typography](./foundations/typography.md) · [Spacing](./foundations/spacing.md) · [Elevation](./foundations/elevation.md) · [Motion](./foundations/motion.md)

---

## 使用方式

1. 先用 [Principles](./principles.md) 判断方向。  
2. 定 **Spec 1 Surface**，再落 token 与 Pattern。  
3. 合入前勾选本页相关验收项。  
4. 扩展系统按 [Governance](./governance.md)。
