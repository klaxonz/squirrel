---
title: 'Frontend: 类型安全侵蚀与分层违规'
status: fixed
fixed_by: |
  - src/views/Settings.vue:140,142,172,213
  - src/stores/user.ts:6,13,36,48,60
  - src/components/music/GlobalMusicPlayerBar.vue:339
  - src/components/video-player/VideoPlayer.vue:614,767,837,843,846,852-855,1112,1115,1146,1546
severity: high
category: architecture
location: squirrel-frontend/src/ (全局)
---

## 问题描述

### 类型安全 (132+ `any` 出现)
- DashPlugin.ts: 20+ `as any` 强制转换
- VideoPlayer.vue: 15+ `any` 使用
- Settings.vue: `(userSettings as any)[item.key]` 绕过类型检查
- Store: `login: async (data: any)` 等

### 分层违规
1. **musicPlayer store** 直接 import API 函数并在 store action 中调用 HTTP
2. **GlobalMusicPlayerBar.vue** 直接 import `getMusicSongComments`、`getMusicCommentCounts` 等
3. **多个 View 绕过 Store**：Subscribed.vue、VideoPlay.vue、LatestVideos.vue、ChannelHeader.vue 等直接调用 API，造成状态分散

## 影响

- `any` 使 TypeScript 的类型检查失效，运行时错误无法在编译期捕获
- 状态分散导致难以调试、数据不一致、缓存混乱
- 无单一可信源（Single Source of Truth）

## 建议方向

1. 定义明确 API 响应接口，替换 `any`
2. 创建领域 Pinia store（如 `useSubscriptionStore`、`useVideoFeedStore`）封装 API 调用
3. store 仅管理状态，将 HTTP 调用委托给 composable 或 service 层
4. 为 DashPlugin 添加正确的 Shaka/Dash.js 类型包装
