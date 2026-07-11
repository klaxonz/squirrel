# Governance

← [目录](./README.md)

规定**如何扩展与合入**设计系统。条款在 [Standards](./principles.md)（S1–S4）。  
产品定义在仓库 [README](../../../README.md)，不在本文件维护路径表。

## 源优先级

1. 代码中的 token 与共享组件（`layout.css` / `themes/dark.css` / `shared/**`）  
2. 本目录文档（与代码必须同变更集对齐）  
3. 业务页样式：仅页面结构与一次性布局；视觉值必须引用 token

## 合入前必做

1. 标明 **S1 Surface**（Consume / Organize / Operate）  
2. 对照 [Standards 验收清单](./principles.md) 勾选相关项  
3. 意图用色符合 [Color 意图表](./foundations/color.md)  
4. 组件来自 `shared/ui` 或已文档化 Pattern；若新增：先入 shared，再写文档，再被业务引用  
5. 新增 spacing / z-index / 色 / 动效：先写入 foundations，业务只引用 token  
6. 若改了路由归属：同步 [Shell · 页面 → Surface](./patterns/shell.md)

## 扩展流程

```
需求 → 定 S1 Surface
     → 已有 Pattern / 组件？
         是 → 组合使用
         否 → 在 shared 实现 + 更新 docs/design + token（若需要）
     → 验收清单勾选
     → 合入
```

## 变更集规则

| 规则 | 说明 |
|------|------|
| 文档与代码同步 | token / 组件 / Pattern 变更与 `docs/design/**` 同一变更集 |
| 先标准后业务 | 改视觉优先改 foundations 或 shared，再扫业务 |
| 可验收 | 每个 UI 变更能指出满足的 S1–S4 条款 |
| 形容词无效 | 「更高级 / 更干净」须改写为 token、Surface 或 Pattern 变更 |
| 产品 vs 设计 | 产品叙事改 README；界面规格改 Standards / Pattern |

## 不合规即阻断

| 现象 | 违反 |
|------|------|
| 页面无 Surface 或混用未说明 | S1 |
| Operate 规格铺满 Consume / Organize 整页 | S1 |
| 业务私有第二套按钮 / 筛选 / 空态 | S1 |
| 选中态使用 primary 洗底或琥珀角标 | S2 |
| 健康态使用 primary | S2 |
| scrim 使用无法追溯的裸色 | S2 |
| 单视图多个实心 primary 主按钮 | S2 |
| 缺 loading / empty / error，或假数据充数 | S3 |
| 失败态无可执行下一步 | S3 |
| display 与 sans 不可区分；随机圆角 / 魔法 z-index | S4 |

## 修订 Standards 本身

1. 改 `principles.md` 与相关 foundation/pattern  
2. 产品身份变更时同步 README（不在 Standards 里复制路径表）  
3. 再改 token / shared  
4. 最后扫业务  

只改口号、不改验收条款与代码，视为未完成修订。
