---
title: 架构 — Desktop IPC 单体 321 行处理 5 个领域 + main.mjs 耦合 YouTube
status: fixed
fixed_by: src/ipc-handlers.mjs:1, src/main.mjs:2, src/playback/providers/javdb/index.mjs:145, src/playback/file-cache.mjs → src/shared/file-cache.mjs
severity: medium
category: architecture
location: squirrel-desktop/src/（跨文件）
---

## 问题描述

### 1. ipc-handlers.mjs — 单体处理程序

`ipc-handlers.mjs`（321 行）在单个 `installDesktopBridgeHandlers()` 函数中包含所有 ~20 个 IPC 通道，覆盖 5 个不同领域：
- YouTube/Bilibili 播放解析
- 网站登录
- 搜索
- 窗口管理
- 服务器配置

对比：后端将路由分布在 19 个文件（每个领域一个）。桌面端将所有 IPC 路由合并到一个文件中，与后端架构模式不一致。

### 2. main.mjs 直接导入特定提供商

`main.mjs:2` 直接 `import { prewarmYouTubePlayback } from './playback/providers/youtube/index.mjs'`。

应用入口点与 YouTube 提供商紧耦合。添加/删除提供商需修改 main.mjs。预热应由管理器协调，由各提供商注册。

### 3. 提供商结构不一致

| 提供商 | 结构 |
|---|---|
| youtube/ | index.mjs + youtubei_core.mjs（分离运行时） |
| bilibili/ | index.mjs + request-runtime.mjs（分离运行时） |
| javdb/ | index.mjs 单体 |
| pornhub/ | index.mjs 单体 |
| youporn/ | index.mjs 单体 |

javdb 导出 `__testing` 私有函数，youtube 混合 OAuth + 预热 + 播放解析。

### 4. file-cache.mjs 位置不当

`playback/file-cache.mjs` 被所有提供商使用，但放在 `playback/` 下而非 `shared/` 下。缓存是通用基础设施。

## 影响

- IPC 处理程序随通道增加难以维护
- 添加提供商需改 2-3 个不同文件，且无统一注册机制
- main.mjs 耦合特定提供商使预热逻辑不可扩展
- 提供商接口不统一，增加新提供商的认知负荷

## 建议方向

1. 将 ipc-handlers.mjs 按领域拆分为多个处理程序文件（如 `ipc-playback.mjs`、`ipc-search.mjs`），类似后端的 routes 拆分
2. 引入 `ProviderRegistry` 协调预热和生命周期，main.mjs 不直接引用具体提供商
3. 统一提供商接口（最少每个应实现 `resolvePlayback`），分离 OAuth 和播放职责
4. 将 `file-cache.mjs` 移至 `shared/` 目录
