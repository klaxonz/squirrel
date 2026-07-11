# Media card actions

← [Patterns](./README.md)

**Surface：** Consume（卡）；嵌在 Organize 页时仍用本形态  
**规格：** [Spec 1](../standards.md#spec-1--surface) · [Spec 2](../standards.md#spec-2--色意映射) · **原则：** [P1](../principles.md#p1--内容与真实状态优先)

视频卡次要操作（已读 / 稍后看 / 喜欢）的标准形态。

## 结构

| 层 | 标准内容 |
|----|----------|
| 缩略图 | 封面、时长、进度；已开启状态时左上角只读 flag 条 |
| 元信息区 | 右对齐 ghost 图标切换（hover / focus-within 显示；已开保持显示） |
| 右键菜单 | 完整操作集（已读/未读、稍后看、喜欢、复制链接） |

```
┌─────────────────────────┐
│  [✓ 🔖 ♥]   flags only  │
│                         │
│              12:34      │
└─────────────────────────┘
Title
avatar  channel · site     [✓][🔖][♥]
        8小时前
```

## 交互

| 步骤 | 标准行为 |
|------|----------|
| 主行动 | 点击卡片 → 打开 / 播放 |
| 快捷切换 | 元信息区 ghost；`click.stop` |
| 完整菜单 | 右键 → ContextMenu |
| 可扫状态 | flag + meta `is-on` 同时表达已开 |

## 视觉

| 状态 | Token / 规格 |
|------|----------------|
| 默认 quick | `muted-foreground`，无底 |
| Hover quick | `foreground/0.06` 底 + selection fg |
| On | `--app-selection-bg` + `--app-selection-fg` |
| Flag 条 | overlay/background alpha 胶囊 + 浅色图标；`pointer-events: none` |
| 标题 hover | `--foreground` |
| 卡 hover | `shadow-card-hover` + transform（可选） |

## 实现

- `features/video/components/feed/VideoItem.vue`
- `features/video/components/feed/ContextMenu.vue`

## 验收

- [ ] 缩略图上无等权操作工具栏
- [ ] 已开态使用 selection token
- [ ] 主点击仍为打开 / 播放
