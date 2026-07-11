# Governance

← [目录](./README.md)

规定**如何扩展与合入**设计系统。条款本身在 [Standards](./principles.md)（S1–S5）。  
产品身份与仓库 [README](../../../README.md) 一致。

## 源优先级

1. 代码中的 token 与共享组件（`layout.css` / `themes/dark.css` / `shared/**`）  
2. 本目录文档（与代码必须同变更集对齐）  
3. 业务页样式：仅页面结构与一次性布局；视觉值必须引用 token

## 合入前必做

1. 标明 **S1 路径等级**（主 / 辅 / 支撑 / 附属）与 **S2 Surface**  
2. 对照 [Standards 验收清单](./principles.md) 勾选相关项  
3. 意图用色符合 [Color 意图表](./foundations/color.md)  
4. 组件来自 `shared/ui` 或已文档化 Pattern；若新增：先入 shared，再写文档，再被业务引用  
5. 新增 spacing / z-index / 色 / 动效：先写入 foundations 文件，业务只引用 token

## 扩展流程

```
需求 → 定 S1 路径 + S2 Surface
     → 已有 Pattern / 组件？
         是 → 组合使用
         否 → 在 shared 实现 + 更新对应 docs/design 页 + token（若需要）
     → 验收清单勾选
     → 合入
```

## 变更集规则

| 规则 | 说明 |
|------|------|
| 文档与代码同步 | token / 组件 / Pattern 变更与 `docs/design/**` 同一变更集 |
| 先标准后业务 | 改视觉优先改 foundations 或 shared，再扫业务引用 |
| 可验收 | 每个 UI 变更能指出满足的 S1–S5 条款 |
| 形容词无效 | 「更高级 / 更干净」须改写为具体 token、Surface 或 Pattern 变更 |
| 身份一致 | UI 叙事与 README「多站订阅中枢 / 归仓」一致 |

## 不合规即阻断

下列情况视为**未达标准**，应改到符合 S1–S5 再合入：

| 现象 | 违反 |
|------|------|
| 主路径第一焦点不是入库内容 / 订阅对象 / 播放主体 | S1 |
| 订阅 → 库 → 播放链路在 IA 上断裂 | S1 |
| Operate 规格铺满主路径整页 | S1 · S2 |
| 页面无 Surface 或混用未说明 | S2 |
| 业务私有第二套按钮 / 筛选 / 空态 | S2 |
| 选中态使用 primary 洗底或琥珀角标 | S3 |
| 健康态使用 primary | S3 |
| scrim 使用无法追溯的裸色 | S3 |
| 单视图多个实心 primary 主按钮 | S3 |
| 缺 loading / empty / error，或假数据充数 | S4 |
| 同步/站点失败无可操作下一步 | S4 |
| display 与 sans 不可区分；随机圆角 / 魔法 z-index | S5 |

## 修订 Standards 本身

若条款无法落地或与产品目标冲突：

1. 先改 `principles.md` 与相关 foundation/pattern 页  
2. 与 README 产品叙述对齐（若身份变更）  
3. 再改 token / shared  
4. 最后扫业务  

只改口号、不改验收条款与代码，视为未完成修订。
