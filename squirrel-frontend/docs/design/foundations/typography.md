# Typography

← [Foundations](./README.md)

**代码：** `layout.css`（`--app-h1-*` 等）· 字体变量在 `index.css`  
**规格：** [Spec 4](../standards.md#spec-4--视觉系统一致性) · **原则：** [P5](../principles.md#p5--一致即可预期)

## 字体角色

| 角色 | Token | 标准 |
|------|-------|------|
| UI | `--font-sans` | 明确 UI 无衬线家族 + 中文系统 fallback；优先自托管 |
| Display | `--font-display` | 与 body 在字重或 tracking 上可区分（可同家族） |
| 等宽 | `--font-mono` | 日志、ID、计数（`.app-mono`） |

`--font-display` 必须解析为可区分的展示规格；与 sans 完全同值视为未达标。

## 字阶

| 级别 | 规格 | 场景 |
|------|------|------|
| Hero | 1.75rem / 650 | 登录、Consume 舞台 / 空态主标题 |
| H1 | 1.6875rem / 600 | 页 / 区域标题 |
| H2 | 1.25rem / 600 | 分组、rail header |
| H3 | 1.0625rem / 600 | 卡片 / 模块标题 |
| H4 | 0.875rem / 600 | 紧凑标题 |
| Body | 0.875rem / 400–500 | 正文、列表 |
| Label | 0.75–0.8125rem / 500–600 | 侧栏、按钮、Tab、字段标签 |
| Micro | 0.625–0.6875rem / 500–600 | 角标、次要元数据 |

## 使用规则

| 项 | 标准 |
|----|------|
| 单位 | 固定 rem |
| 工具栏 | 同一工具栏 ≤ 两档字号 |
| 筛选字段标签 | 0.6875rem / 600 |
| 筛选面板标题 | 0.8125rem / 650 |
| Consume 舞台标题 | Hero 或 H1 + display |
| Organize / Operate 标题 | H2–Body 为主 |

## 验收

- [ ] 计算样式下 display 与 sans 可区分
- [ ] 标题使用 `--app-h*` 或等价 class
- [ ] 工具栏字号档位数 ≤ 2
