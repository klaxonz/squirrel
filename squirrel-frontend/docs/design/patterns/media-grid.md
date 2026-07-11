# Media grid

← [Patterns](./README.md)

**代码：** `layout.css` → `.app-video-grid`  
**S1 路径：** 主 / 辅（库与订阅流）  
**Surface：** Consume 墙；Organize 页内网格仍复用本 token  
**条款：** [S5](../principles.md#s5--视觉系统一致性)

## 标准用法

```html
<div class="app-video-grid"><!-- cards --></div>
<div class="app-video-grid app-video-grid--feed">…</div>
<div class="app-video-grid app-video-grid--compact">…</div>
```

| 变体 | 规格 |
|------|------|
| 默认 | 均匀 gap（本地 feed / VideoList） |
| `--feed` | 更松行列 gap（远程 / 频道） |
| `--compact` | 更小 `--app-grid-min` |

密度：覆盖 `--app-grid-min`（默认约 280px）。

## 验收

- [ ] 媒体墙使用 `.app-video-grid*`
- [ ] 密度通过 `--app-grid-min` 调整
- [ ] 同类卡封面比例一致
