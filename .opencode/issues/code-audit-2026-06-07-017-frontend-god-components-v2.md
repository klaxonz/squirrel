---
title: Frontend 上帝组件第二轮 — VideoPlayer(2673行) / RssSources(1941行) / Music(1016行)
status: fixed
severity: high
category: architecture
location: squirrel-frontend/src/components/video-player/VideoPlayer.vue, src/views/RssSources.vue, src/views/Music.vue
---

## 问题描述

前次审查已标记的上帝组件问题未彻底解决：

- **VideoPlayer.vue** (2673 行) — 超大规模播放器组件，整合了 Dash/HLS/Subtitles 等插件，模板数千行
- **RssSources.vue** (1941 行) — 内联 200 行上下文菜单 + 100 行阅读器面板，模板 950 行
- **Music.vue** (1016 行) — 管理 14 种视图模式、58 个函数、40+ 个响应式状态

此外还有 **31 个源文件超过 400 行**（vs 先前审计报告的 2-3 个），表明上帝组件问题在扩大而非收敛。

## 影响

- 难以测试和维护
- 多人协作时合并冲突频繁
- 单个组件修改可能影响不相关的功能
- 编译/热更新性能降低

## 建议方向

1. VideoPlayer.vue: 将 overlay 系统、控制栏、进度条等拆为独立子组件
2. RssSources.vue: 提取 ContextMenu、ReaderPanel、AccountDropdown 为独立组件
3. Music.vue: 每个视图模式独立路由，Music.vue 仅做 layout shell
4. 建立组件大小红线（建议 <400 行），CI 检查
