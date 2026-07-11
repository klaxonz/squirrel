# Governance

← [目录](./README.md)

## 源与优先级

1. 代码 token / 共享组件  
2. 本设计文档（`docs/design/**` + 入口 `DESIGN.md`）  
3. 业务页本地样式（应趋近于零）

改视觉：先改 `layout.css` / `themes/dark.css` 或共享组件 → 再回写对应文档页。

## 扩展清单

新增 UI 前自问：

1. 属于哪个 Surface？（Media / Task / System）→ [Shell](./patterns/shell.md)  
2. 已有 Pattern 能覆盖吗？→ [Patterns](./patterns/README.md)  
3. 已有组件能组合吗？→ [Components](./components/README.md)  
4. 若必须新建：放进 `shared/`，并更新对应文档页

## 明确禁止

1. 移动优先断点堆叠（除非需求明确要求移动端）  
2. 侧栏 + 工作区双浮岛  
3. Workbench 次栏 card 刷底  
4. 装饰大渐变字、无意义 glass、斜线纹理、假指标  
5. 色条侧边告警（用全边框 + 图标 + 文案）  
6. 未激活 UI 高饱和、高对比  
7. primary 表示健康 / 已连接  
8. primary 表示选中 / 已筛选 / 导航当前（含 alpha 洗底与琥珀角标）  
9. 业务页私有筛选面板（必须 `AppFilterPanel`）  
10. 新 z-index / spacing 不进 `layout.css`  
11. 假 UI 掩盖缺数据、runtime / 鉴权失败  
12. light 下高饱和暖色低 α 脏桃色表面  

## 修订

- Token / 组件 / Pattern 变更与文档同一变更集提交  
- 禁止只改口号不改可执行条款  
- 发现「规范导致脏 UI」：先改规范与共享 token，再扫业务，不单页打补丁  
- 气质形容词不能直接驱动实现，必须落到 Surface、token 与 Pattern  
