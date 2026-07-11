# States

← [Patterns](./README.md)

**规格：** [Spec 3](../standards.md#spec-3--状态完整性) · **原则：** [P4](../principles.md#p4--状态闭环)

## 加载 · 空 · 错

| 状态 | 标准 | 组件 |
|------|------|------|
| Loading | 区域级 Skeleton / Block loader，形状贴近终态 | `AppSkeleton` / `AppBlockLoader` |
| Empty | 标题 + 原因 + 可行动作 | `AppEmptyState` |
| Error | 具体原因 + 恢复动作 | 文案 + 按钮 |

## 运维与结果态

| 意图 | Token + 表达 |
|------|----------------|
| 健康 / 在线 / 成功 | `--success` + 文案（可加图标） |
| 警告 / 降级 | `--warning` + 文案 |
| 失败 / 危险 | `--destructive` + 文案 |
| 列表选中 / 筛选触发器开 | `--app-selection-*` |
| 筛选面板内当前项 | `--app-filter-raised-*` |

## 验收

- [ ] 主列表与主详情具备 loading / empty / error
- [ ] 空态与错误符合 [Content](../content.md)
- [ ] 运维结果使用语义色 + 文案

## 相关

- [Standards · Spec 3](../standards.md#spec-3--状态完整性)
- [Content](../content.md)
- [Feedback components](../components/feedback.md)
- [Color](../foundations/color.md)
