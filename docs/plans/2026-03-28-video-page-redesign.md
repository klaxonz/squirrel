# 2026-03-28 视频播放页重构设计 (Immersive Cockpit Design)

## 1. 概述 (Overview)
重构 `squirrel-frontend` 的视频播放页 (`VideoPlay.vue`)，使其在视觉风格上与重构后的视频列表页 (`VideoItem.vue`) 保持高度一致。采用 **“沉浸式监控舱 (Immersive Cockpit)”** 设计风格，将观影体验转化为一种“技术终端操作”感。

## 2. 核心设计语言 (Visual Language)
- **配色**：
  - 底色：`#050505` (深邃黑)。
  - 点缀色：`#ff4d00` (Terminal Orange)。
  - 辅助色：`rgba(255, 255, 255, 0.05)` (技术分割线)。
- **字体**：
  - 标题：Sans-serif, 600 weight.
  - 元数据：等宽字体 (`Courier New` / `JetBrains Mono`)，字号 `0.65rem` - `0.72rem`，全大写。
- **质感**：
  - 背景扫描线 (Scanlines)：2% 透明度的水平条纹。
  - 取景框 (Viewfinder)：15px L型橙色线框。
  - 呼吸感发光 (Backlight Glow)：橙色元素在激活或悬停时带有扩散发光阴影。

## 3. 详细设计 (Detailed Design)

### 3.1 视频播放器外框 (The Monitor)
- **容器**：视频播放器嵌套在一个带有 12px 内边距的容器中，内边距显示背景的扫描线。
- **取景标记**：容器四个角使用 `1px solid #ff4d00` 的 L 型边框。
- **装饰**：播放器顶部正中显示 `[SYSTEM_MONITOR_01]` 标签（等宽字体）。

### 3.2 视频信息面板 (The Console)
- **标题**：位于 `[ENTRY_DATA]` 标签右侧，底部增加 1px 的橙色细线。
- **频道信息**：设计成“身份 ID 卡”模式。
  - 头像带有一个圆形的扫描进度圈。
  - 订阅/取消订阅按钮改为极简线框风格。
- **交互按钮**：
  - 按钮样式：`1px solid rgba(255, 255, 255, 0.1)`，悬停变橙色并产生发光。
  - 激活状态：橙色背景 + 橙色边框 + 橙色发光。

### 3.3 侧边栏列表 (Related Streams)
- **卡片布局**：横向紧凑布局，缩略图比例 16:9，2px 微圆角。
- **编号底纹**：每个卡片背景带有一个大号、低透明度 (5%) 的数字编号 (01, 02...)。
- **悬停特效**：卡片在悬停时略微上移，并显示 `[DATA_READING...]` 提示。

## 4. 技术实现 (Implementation Details)
- **CSS**：大量使用 CSS 变量控制发光效果和配色。
- **动画**：使用 Vue 3 的 `<transition>` 配合 `transform` 和 `opacity` 实现扫描进入感。
- **响应式**：保持现有的 Widescreen 模式逻辑，但在宽屏下增强左右面板的分割感。

## 5. 验收标准 (Success Criteria)
- 视频播放页的整体感官与列表页 (`VideoItem.vue`) 完美融合。
- UI 交互不仅满足功能，还要提供强烈的情绪价值（技术感、高级感）。
- 保持高性能，不引入过多的重绘或计算开销。
