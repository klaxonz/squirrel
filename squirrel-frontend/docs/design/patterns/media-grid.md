# Media grid

← [Patterns](./README.md)

**代码：** `layout.css` → `.app-video-grid`

## 用法

```html
<div class="app-video-grid"><!-- cards --></div>
<div class="app-video-grid app-video-grid--feed">…</div>
<div class="app-video-grid app-video-grid--compact">…</div>
```

| 变体 | 说明 |
|------|------|
| 默认 | 均匀 gap（本地 feed / VideoList） |
| `--feed` | 更松的行列 gap（远程 / 频道） |
| `--compact` | 更小 `--app-grid-min` |

密度：覆盖 `--app-grid-min`（默认约 280px）。

## Don’t

- 每页手写 `grid-cols-1 sm:… 3xl:…` 长链
- 用卡片嵌套卡片撑布局
