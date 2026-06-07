---
title: 'Frontend: 超级组件 — VideoPlayer.vue (3418行) 和 RssSources.vue (2962行)'
status: open
severity: high
category: code-smell
location: squirrel-frontend/src/components/video-player/VideoPlayer.vue, src/views/RssSources.vue
---

## 问题描述

### VideoPlayer.vue (3418 行)
单一 SFC 包含：template (~660行) + 业务逻辑 (~2300行) + CSS (~450行)。处理：播放控制、画质选择、字幕管理、章节导航、睡眠定时器、AB 循环、剪辑标记、播放列表、UpNext、键盘快捷键、全屏、HUD、触控手势等。`core/createPlayerEngine.ts` 另有 1187 行。

### RssSources.vue (2962 行)
处理：账户管理、feed 列表、条目浏览、筛选、阅读器、右键菜单、灯箱、移动端 sheet、字体设置、同步进度轮询等。直接 import 30+ API 函数，所有状态以 `ref()` 分散管理，无 composable 或 store 抽象。

## 影响

- 几乎不可能维护、review、测试
- 任何修改都可能影响不相关的功能
- 新开发者的学习曲线极高
- RssSources.vue 完全不可测

## 建议方向

1. VideoPlayer.vue → 抽取 composable：`usePlaybackControls`、`useSubtitleSettings`、`useChapterNavigation`、`useSleepTimer`、`useClipMarkers`
2. VideoPlayer.vue → 分离每个 overlay 为独立组件（UpNextOverlay、ChapterOverlay 等）
3. `createPlayerEngine.ts` → 拆为 `engine-factory.ts`、`quality-controller.ts`、`stats-tracker.ts`、`error-recovery.ts`、`subtitle-controller.ts`
4. RssSources.vue → 抽取 composable：`useRssAccounts`、`useRssFeeds`、`useRssEntries`、`useRssReader`
5. 考虑建立 Pinia store 管理 RSS 共享状态
