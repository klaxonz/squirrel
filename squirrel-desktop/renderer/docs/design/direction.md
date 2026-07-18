# Design direction

← [DESIGN.md](../../DESIGN.md)

本页是 **唯一维护的设计文档**。实现以代码为准。

---

## 产品

自托管多站视频订阅中枢：订阅 → 同步入库 → 浏览整理 → 播放；附带 RSS、音乐与运维。  
能力清单见仓库根 [README](../../../../README.md)。

---

## 立场

1. **允许 redesign** 布局、密度、控件气质；现有 UI 是实现现状，不是终点。
2. **真源在代码**：`shared/styles/**`、`shared/ui/**`、壳与页面组件。
3. **外部产品只借结构/工作流**，不要混多套皮肤。
4. **不要**用已删除的长篇 design system / 旧审计报告挡合理改动。

---

## 底线（产品，不是视觉教条）

| | |
|--|--|
| 内容与真实状态优先 | 空/错要诚实，装饰不抢内容 |
| 状态闭环 | loading / empty / error + 可执行下一步 |
| 意图可预期 | 主行动、危险、选中全站同一套表达（token 可改） |
| 系统先于特例 | 扩展 `shared/ui`，业务页不私建第二套控件 |

---

## 工程

| 层 | 位置 |
|----|------|
| Token / 主题 | `src/shared/styles/` |
| 控件 | `src/shared/ui/` |
| 壳 | `src/app/layouts/` · `src/app/shell/` |
| 业务 | `src/features/` |

### 测试

- **要**：调用真实函数 / composable / store / API client，断言行为。
- **不要**：`readFile` + 正则扫 Vue/CSS 冒充单测。
- 视觉：Electron/截图或手工，别用假单元测试锁美学。

### 写文档

方向性决策 **只在本页** 补短句。不要重建锚点表、冻结尺寸手册、Pattern 百科。
