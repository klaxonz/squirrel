# Elevation · Z-index

← [Foundations](./README.md)

**代码：** `src/shared/styles/layout.css`

## 壳层 = 单画布

- 顶栏 / 工作区 / 工具栏落在 `--background`（或透明叠其上）。
- 主侧栏可轻抬 `--sidebar`。
- Workbench **次栏透明 + 竖线**，不刷 card、不做双浮岛。
- Shell 分区用 `--app-hairline` / border，不用 `--card` 刷分区。

## 阴影

| Token | 用途 |
|-------|------|
| `--app-surface-shadow` | 轻表面 |
| `--app-panel-shadow` | 中等面板 |
| `--app-floating-shadow` / `shadow-popover` | 菜单、筛选 |
| `--app-overlay-shadow` | Dialog |
| `--brand-glow*` | **仅**品牌徽章 |

静止内容优先 hairline + 色阶；阴影解释叠层与抬起。

## Z-index

禁止业务魔法数，严格使用：

```
content → sticky → header → sidebar
→ dropdown → popover → sheet → dialog → toast → player-overlay
```

对应 token：`--z-content` … `--z-player-overlay`。
