# Media grid

← [Patterns](./README.md)

**代码：** `layout.css` → `.app-video-grid`  
**Surface：** Consume 墙；Organize 页内网格仍复用本 token  
**规格：** [Spec 4](../standards.md#spec-4--视觉系统一致性)  
**品质：** [Media craft · 墙](./media-craft.md#3-媒体墙--rail)

## 标准用法

```html
<div class="app-video-grid"><!-- cards --></div>
<div class="app-video-grid app-video-grid--feed">…</div>
<div class="app-video-grid app-video-grid--compact">…</div>
<div class="app-video-rail"><article class="app-video-rail-card">…</article></div>
<div class="app-music-grid">…</div>
```

| 变体 | 规格 |
|------|------|
| 默认 | 均匀 gap（本地 feed / VideoList） |
| `--feed` | 更松行列 gap（远程 / 频道） |
| `--compact` | 更小 `--app-grid-min` |
| `.app-video-rail` | 横向滚动轨道；gap、snap、overflow 由共享 class 管理 |
| `.app-video-rail-card` | 固定 rail 卡宽；卡与 skeleton 共用 |
| `.app-music-grid` | 音乐专辑 / 歌单 / 榜单 artwork 墙；使用冻结的 `--app-music-grid-min` |

密度：覆盖 `--app-grid-min`（默认约 320px）。
横向 rail：`--app-video-rail-card-width` = `19rem`，`--app-video-rail-gap` = `1.25rem`。
音乐 artwork 墙：`--app-music-grid-min` = `180px`，不在业务页私设更密的最小列宽。

## 验收

- [ ] 媒体墙使用 `.app-video-grid*`
- [ ] 密度通过 `--app-grid-min` 调整
- [ ] 同类卡封面比例一致
- [ ] 横向 rail 不在业务组件重复声明卡宽、gap 或分页距离
- [ ] 音乐 artwork 墙使用 `.app-music-grid`，不手写 `120–160px` 私有网格
