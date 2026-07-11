# Design principles

← [目录](./README.md)

本页是**设计原则**：两难时选哪边。  
数量少、可记忆；不写 token 表、不写路由清单。

**强制规格**（Surface / 色 / 状态 / 视觉一致性）→ [standards.md](./standards.md)  
**产品是什么** → 仓库 [README](../../../README.md)

---

## P1 · 内容与真实状态优先

界面的第一职责是让用户看清内容、完成操作、知道系统真实情况。  
装饰、氛围、chrome 服务于内容与状态，不抢主焦点、不掩盖失败。

| 倾向 | 收起 |
|------|------|
| 封面、标题、进度、下一步 | 无信息的大装饰、假数据、空壳 cinematic |
| 真实空 / 错 / 同步失败 | 用漂亮占位假装已就绪 |

---

## P2 · 同一意图，同一视觉语言

同一种用户意图在全站只对应一套视觉表达。  
换页、换功能不换「选中长什么样」「成功长什么样」。

| 倾向 | 收起 |
|------|------|
| 选中 / 当前 / 筛选开 → 同一 selection 语言 | 有的页 primary 洗底、有的页灰底 |
| 主行动 → 同一 primary 用法 | 工具栏每个按钮都抢主色 |

细则 → [Standards · 色意](./standards.md#spec-2--色意映射) · [Color](./foundations/color.md)

---

## P3 · 系统先于特例

先复用 token、`shared/ui` 与已有 Pattern；新能力优先扩展系统，再被业务引用。  
业务页不为单页发明第二套按钮、筛选或空态。

| 倾向 | 收起 |
|------|------|
| 扩展 shared + 文档 | 业务 scoped 私有组件库 |
| 例外进入 foundations / Pattern |  silently 分叉 |

细则 → [Governance](./governance.md)

---

## P4 · 状态闭环

凡异步或可失败区域，必须让用户感知加载、空、错误，并在失败时给出可执行下一步。  
「说真话」是原则；具体形态见规格与 Pattern。

| 倾向 | 收起 |
|------|------|
| Skeleton / 原因 + 动作 | 空白闪烁、无动作「出错了」 |
| 同步失败可重试或导向修复 | 吞掉错误只 toast 一下 |

细则 → [Standards · 状态](./standards.md#spec-3--状态完整性) · [States](./patterns/states.md)

---

## P5 · 一致即可预期

字号、圆角、间距、色温、焦点、动效全站可预期。  
用户学一次交互语言，处处可用；例外必须有文档化理由。

| 倾向 | 收起 |
|------|------|
| 统一 token 与字阶 | 随机圆角、魔法 z-index、裸色 |
| 可见的键盘焦点 | 仅 hover 无 focus-visible |

细则 → [Standards · 视觉系统](./standards.md#spec-4--视觉系统一致性)

---

## 原则如何落到规格

| 原则 | 主要落点 |
|------|----------|
| P1 | Surface 密度、媒体 Pattern、空错态 |
| P2 | 色意映射、Button 主行动数量 |
| P3 | Governance、组件来源 |
| P4 | Spec 3、States Pattern、Content |
| P5 | Spec 4、Foundations |

做 UI / 评审时：先问是否违反原则，再用 [Standards](./standards.md) 验收清单逐项勾选。
