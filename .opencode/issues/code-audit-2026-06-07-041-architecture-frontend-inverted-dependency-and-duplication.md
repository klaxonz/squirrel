---
title: 架构 — Frontend axios→composables 反向依赖 + 3处 remote-channel 重复
status: fixed
fixed_by: utils/axios.ts:3, composables/useRemoteChannel.ts:50, composables/useDesktopBridge.ts:14
severity: medium
category: architecture
location: squirrel-frontend/src/（跨文件）
---

## 问题描述

### 1. axios 基础设施层依赖 Vue composables（反向依赖）

`utils/axios.ts` 从 `composables/useServerConfig` 导入 `getServerUrl`。HTTP 客户端基础设施依赖于 Vue 响应式 composables，方向倒置。如果 composable 或 store 在初始化时使用 axios，则可能导致循环调用。

### 2. Remote-channel 获取逻辑重复 3 次

`fetchRemoteChannel()` 几乎相同的模式出现在：
- `LatestVideos.vue:454-518`（分页、去重、竞态处理）
- `Subscribed.vue:~618-660`（同上）
- `RemoteChannelDetail.vue:248-280`（同上）

每处重复分页、`window.desktopApp.getRemoteChannel()` 调用、request token 模式、超时处理。应提取为共享 composable。

### 3. `window.desktopApp` 分散在 13 个文件 27 处引用

没有中心化的 `useDesktopBridge` 抽象，导致：
- 分散的 `window.desktopApp?.isDesktop === true` 守卫
- 运行时类型错误无保护
- Electron 桥接与渲染逻辑耦合

### 4. Views 过于庞大（超出已有 issue 范围—不同角度）

| 视图 | 行数 | 混合职责 |
|---|---|---|
| Music.vue | 905 | 路由 15+ 分支 + 组件切换 + 状态管理 |
| Subscribed.vue | ~800 | 列表 + 搜索 + 过滤 + 订阅管理 |
| VideoPlay.vue | 717 | 播放 + 订阅 + 互动 + 元数据 + 推荐 |

这些视图混合了编排、UI 状态、业务逻辑和模板，按单一职责原则应拆分。

## 影响

- `axios.ts` 的 composable 依赖使在非 Vue 上下文（如测试）中 import axios 时可能出错
- Remote-channel 重复导致修复 bug 需修改 3 处，容易遗漏
- desktop bridge 无类型安全，错误静默失败
- 大视图难以测试和维护

## 建议方向

1. `axios.ts` 改为从常量/配置对象获取 serverUrl，而非从 composable
2. 提取 `useRemoteChannel` composable 封装分页 + 去重 + 超时逻辑
3. 创建 `useDesktopBridge` 类型安全抽象，集中所有 `window.desktopApp` 访问
4. 大视图按功能拆分为子视图，主视图仅做路由编排
