# Media card actions

← [Patterns](./README.md)

视频卡上的次要操作（已读 / 稍后看 / 喜欢）。

## 问题

不要在缩略图上放 **三个等权圆形按钮**。  
那会：

- 抢媒体（违反「媒体优先」）
- 把状态工具栏做成播放器 chrome
- 用 primary / 高对比填充表达「开着」，与选中规范冲突

## 形态

| 层 | 做什么 | 不做什么 |
|----|--------|----------|
| **缩略图** | 封面、时长、进度；有状态时左上角 **静默 flag 条**（只读、可扫） | 操作工具栏、等权 FAB |
| **元信息区** | 右对齐 **ghost 图标切换**（hover / focus-within 显；已开保持显） | 实心圆、品牌色洗底 |
| **右键菜单** | 完整操作（已读/未读、稍后看、喜欢、复制链接） | 只放一半动作 |

```
┌─────────────────────────┐
│  [✓ 🔖 ♥]   flags only  │  ← 仅已开启状态，非按钮栏
│                         │
│              12:34      │
└─────────────────────────┘
Title
avatar  channel · site     [✓][🔖][♥]  ← meta quick toggles
        8小时前
```

## 交互

1. **主行动**：点击卡片 → 打开/播放（不变）。
2. **快捷切换**：元信息区 ghost 图标；`click.stop`，不触发开卡。
3. **完整菜单**：右键 → `ContextMenu`（含稍后看）。
4. **扫描**：已开状态在缩略图 flag + meta `is-on` 同时可辨。

## 视觉 token

| 状态 | 规格 |
|------|------|
| 默认 quick | `muted-foreground` 低透明，无底 |
| Hover quick | `foreground/0.06` 底 + `selection-fg` |
| On | `--app-selection-bg` + `--app-selection-fg` |
| Flag 条 | 黑半透明胶囊 + 白图标，**pointer-events: none** |
| 标题 hover | `foreground`（**不用 primary**） |

## 实现

- `features/video/components/feed/VideoItem.vue`
- `features/video/components/feed/ContextMenu.vue`

## 相关

- [Principles · 媒体优先](../principles.md)
- [Color · 选中](../foundations/color.md)
- [Media grid](./media-grid.md)
