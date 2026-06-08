---
title: Frontend 类型侵蚀 + 废弃重复组件
status: fixed
fixed_by: |
  src/types/api.ts — 统一 ApiResult<T>
  src/composables/rssTypes.ts — 改为 re-export
  src/types/videoPlayback.ts — 改为 re-export
  src/composables/{useSites,useLatestVideos,usePlaylist,useUserSettings,useUser,useSystemConfig,useVideoHistory}.ts — 移除局部定义
  src/composables/useGlobalVideoPlayer{.js→.ts} — .js 转 .ts
  src/components/playlist/PlaylistPanel.vue — 删除（无引用死代码）
  src/components/feed/ContinueWatching.vue — console.error → Logger
  src/{layouts/AppLayout,AuthLayout}.vue — 移除 window as any
  src/components/shell/DesktopTitleBar.vue — 移除 window as any + 修复类型
  src/composables/useRssReader.ts — 移除 window as any
  src/composables/{useRssFeeds,useRssAccounts,useRssEntries}.ts — 统一 error.message 访问
  src/composables/useVideoHistory.ts — 统一 error.message 访问
  src/views/{RssSources,SyncCenter}.vue — 统一 error.status 访问
  src/components/{PageHeader,SubscriptionSkeleton,AppToolbarFrame,AppEmptyState,AppPageShell,LoadingIndicator,AddChannelDialog,ImportSubscriptionDialog,ChannelHeader,ContextMenu,MobileNav,AppSegmentedControl,VirtualList,GlobalSearchBar,Switch,TaskDialog,SiteConfigEditorDialog}.vue — defineProps({}) → defineProps<{...}>()
  src/views/RssSources.vue — ApiResult import 路径更新
severity: high
category: code-smell
location: squirrel-frontend/src/
---

## 问题描述

### 类型侵蚀
- **112 处 `any` 类型**（73 在 .vue + 39 在 .ts）
- **51 处 `as any` 强制转换**（DashPlugin.ts 独占 16 处）
- **`ApiResult<T>` 定义了 7 次**，各文件 error 类型不一致（`any | null` / `unknown | null` / `any`）
- **12 个组件用 `defineProps({})` Options API 旧写法**，应改为 `defineProps<{...}>()`
- **`useGlobalVideoPlayer.js`** 是全项目唯一的 `.js` 文件，应改为 `.ts`

### 废弃/重复组件
- **Music.vue (1016行)  vs  MusicNew.vue (809行)** — 两套组件并存，不确定哪套是 canonical
- **GlobalMusicPlayerBar.vue (1224行)  vs  GlobalMusicPlayerBarNew.vue (551行)**
- **MusicSearchView.vue (452行)  vs  MusicSearchViewNew.vue (631行)**
- **两个 PlaylistPanel.vue** — `components/playlist/` (690行) 和 `components/video-player/` (174行)

### 其他
- `.custom-scrollbar` CSS 在 10+ 个文件中重复定义
- `console.error` 替代 Logger（ContinueWatching.vue:132）
- `window as any` 访问 desktopApp（3 处）

## 影响

- any 类型使 IDE 失去自动补全，运行时错误无法在编译期发现
- 废弃组件浪费维护精力，修复 bug 后可能只改了其中一个版本
- 重复 CSS 增加包体积

## 建议方向

1. 确定 Music vs MusicNew 哪套是 canonical，删除另一套
2. 定义共享 `ApiResult<T>` 在 `src/types/api.ts`
3. 12 个组件迁移到 `defineProps<{...}>()`
4. useGlobalVideoPlayer.js → .ts
5. 自定义滚动条 CSS 提取到 Tailwind 配置或共享 CSS 模块
