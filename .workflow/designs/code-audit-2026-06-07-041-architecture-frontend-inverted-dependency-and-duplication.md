# 修复方案：axios 反向依赖 + Remote-channel 重复

## Problem 1: axios.ts 反向依赖

**根因：** `utils/axios.ts` 从 `composables/useServerConfig` 导入 `getServerUrl`，导致 HTTP 基础设施层依赖于 Vue composable（反向依赖）。

**修复：** 提取纯函数模块 `utils/serverConfig.ts`，只做 localStorage 读写 + 内存缓存，不依赖 Vue 响应式。`axios.ts` 和 `useServerConfig.ts` 都改为依赖此模块。

**涉及文件：**
- `utils/serverConfig.ts`（新建）
- `utils/axios.ts`（改 import）
- `composables/useServerConfig.ts`（改 `getServerUrl` 实现，复用 `serverConfig` 的缓存）

**风险：** 低 — 提取的函数与原逻辑一致。

## Problem 2: Remote-channel 获取逻辑 3 处重复

**根因：** `LatestVideos.vue`、`Subscribed.vue`、`RemoteChannelDetail.vue` 各自独立实现 `fetchRemoteChannel()`，均含 request token 竞态处理、`Promise.race` 超时、分页、去重。

**修复：** 提取 `composables/useRemoteChannel.ts` 封装核心分页状态机。LatestVideos 和 Subscribed 改为使用此 composable；RemoteChannelDetail 行为略有不同（route 驱动 profile），但核心 fetch 逻辑共享。

**涉及文件：**
- `composables/useRemoteChannel.ts`（新建）
- `views/LatestVideos.vue`（替换 `fetchRemoteChannel`）
- `views/Subscribed.vue`（同上）
- `views/RemoteChannelDetail.vue`（可选，短期可保持独立）

**风险：** 中 — 需保证模板绑定兼容新 composable 的返回值。

## Problem 3: `window.desktopApp` 分散访问

**根因：** 27 处直接访问 `window.desktopApp` 散布在 13 个文件中，无中心化类型安全抽象。

**修复：** 创建 `composables/useDesktopBridge.ts` 提供类型安全的 `useDesktopBridge()` 封装。先建立抽象层，逐步迁移高价值文件（`useServerConfig.ts`、`useVideoDetail.ts`、`SiteRuntimeManager.vue`）。

**涉及文件：**
- `composables/useDesktopBridge.ts`（新建）
- 首批迁移：`useServerConfig.ts`、`useVideoDetail.ts`
- 其余文件逐步跟进

**风险：** 中 — 新增抽象不会破坏现有代码，迁移时需注意 `isDesktop` 守卫逻辑不变。

## Problem 4: Views 过于庞大

**状态：** 延后处理。issue 原文已注明「超出已有 issue 范围」，需另开专属 issue 拆分大视图。

## 总风险
- 最小改动，向后兼容
- 不改 `site_runtimes/`、不改凭据、不涉及桌面播放兜底
- 不改未涉及子项目的代码
