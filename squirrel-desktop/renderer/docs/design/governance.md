# Governance

← [目录](./README.md)

规定**如何扩展与合入**设计系统。

| 文档 | 管什么 |
|------|--------|
| [UI Clone Anchors](./ui-clone-anchors.md) | 页面级视觉宿主与冻结规则（**好看 = 像锚点**） |
| [Principles](./principles.md) | 决策取舍 |
| [Standards](./standards.md) | 强制规格与验收 |
| [README](../../../README.md) | 产品定义 |

## 源优先级

1. [UI Clone Anchors](./ui-clone-anchors.md) 的 PrimeVue Aura 全局视觉宿主与冻结尺寸
2. 代码中的 token 与共享组件（`layout.css` / `themes/dark.css` / `shared/**`）
3. 本目录其余文档（与代码必须同变更集对齐）
4. 业务页样式：仅页面结构与一次性布局；视觉值必须引用 token

## 合入前必做

1. 不违反 [UI Clone Anchors](./ui-clone-anchors.md)（无锚点依据的「更好看」变更直接阻断）
2. 不违反 [Principles](./principles.md)
3. 标明 **Surface**（Consume / Organize / Operate）
4. 勾选 [Standards](./standards.md) 相关验收项
5. 意图用色符合 [Color](./foundations/color.md)
6. 组件来自 PrimeVue-backed `shared/ui` 或已文档化 Pattern
7. 新 spacing / z-index / 色 / 动效：先写入 foundations
8. 若改路由归属：同步 [Surface 落地表](./patterns/surface.md)

## 新增组件 / Pattern（三步）

```
1. 提案
   - 说明意图、为何现有组件不够
   - 指定 Surface、相关原则（P1–P5）
   - 是否进入 shared（默认：是，若全站复用）

2. 实现
   - 代码放入 shared/ui（PrimeVue 产品适配层）或 shared/components/layout
   - 使用 system token；需要新值则先加 foundations
   - 补 a11y：焦点、键盘、必要 aria
   - 更新 docs/design 对应页（组件或 Pattern）

3. 合入
   - 勾选 Standards 验收
   - 同一变更集：代码 + 文档（+ token 若有）
   - 业务页只引用，不复制
```

**Snowflake（单页特例）：** 仅当无法合理进 shared 时允许业务本地结构样式；视觉值仍须引用 token。在 PR 中注明原因与后续是否回收进系统。

## 扩展流程（简图）

```
需求 → 对原则 → 定 Surface
     → 已有组件/Pattern？ 是 → 组合使用
                          否 → 走「新增三步」
     → 验收 → 合入
```

## 变更集规则

| 规则 | 说明 |
|------|------|
| 文档与代码同步 | token / 组件 / Pattern 与 `docs/design/**` 同变更集 |
| 先系统后业务 | 先 foundations / shared，再业务引用 |
| 可验收 | 能指出满足的 Spec 1–4 |
| 形容词无效 | 「更高级」须落成 token / Surface / Pattern |
| 产品 vs 设计 | 产品改 README；规格改 Standards；原则改 Principles |

## 不合规即阻断

| 现象 | 违反 |
|------|------|
| 页面无 Surface 或混用未说明 | Spec 1 |
| Operate 规格铺满 Consume / Organize 整页 | Spec 1 · P1 |
| 媒体卡/墙/首页 feed 未达 Media craft 配方 | Spec 1 · [Media craft](./patterns/media-craft.md) |
| 业务私有第二套按钮 / 筛选 / 空态 | Spec 1 · P3 |
| 选中态使用 primary 洗底或琥珀角标 | Spec 2 · P2 |
| 健康态使用 primary | Spec 2 |
| scrim 无法追溯 token | Spec 2 |
| 单视图多个实心 primary 主按钮 | Spec 2 |
| 缺 loading / empty / error，或假数据充数 | Spec 3 · P4 |
| 失败态无可执行下一步 | Spec 3 |
| display 与 sans 不可区分；随机圆角 / 魔法 z-index | Spec 4 · P5 |
| 无 Aura 宿主依据的视觉微调 / 按 Surface 混搭外部产品皮肤 | [UI Clone Anchors](./ui-clone-anchors.md) |

## 修订本系统

1. 视觉宿主 / 冻结尺寸变更 → `ui-clone-anchors.md`
2. 原则变更 → `principles.md`
3. 强制规格变更 → `standards.md` + 相关 foundation/pattern
4. 产品身份变更 → README（不在设计标准里复制主链表）
5. 再改 token / shared / 业务

只改口号、不改验收与代码，视为未完成。
