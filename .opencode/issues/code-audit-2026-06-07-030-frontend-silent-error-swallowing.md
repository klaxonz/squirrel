---
title: Frontend 普遍静默吞异常 — 30+ catch {} 不处理不日志
status: fixed
fixed_by: 跨 22 文件 ~50 处 catch 块添加 Logger 日志
severity: high
category: error-handling
location: squirrel-frontend/src/（跨多文件）
---

## 问题描述

前端大量 `catch {}` / `catch (_) {}` / `catch (e) {}`（空 body）模式，异常被静默吞噬：

**核心播放器：**
- `core/error-recovery.ts`: 84, 99, 268 — 恢复流程错误被吞
- `core/createPlayerEngine.ts`: 171, 178, 276, 693, 763, 921, 936 — 引擎初始化/释放失败
- `core/PlayerAdapter.ts`: 174, 184, 196, 206, 239 — 适配器方法失败
- `plugins/dash/DashPlugin.ts`: 12 处 — Dash 插件错误
- `plugins/hls/HlsPlugin.ts`: 5 处 — HLS 插件错误
- `runtime/usePlayer.ts`: 153, 161 — 播放器状态读取失败

**Composables / 视图层：**
- `usePlaybackReporting.ts:77` — 播放报告发送失败静默
- `useGlobalSearch.ts:59` — 搜索导航失败
- `useGlobalVideoPlayer.ts:47,57,66` — 播放器操作失败
- `useRssAccounts.ts:51` — URL 解析失败
- `useRssFeeds.ts:258` — 订阅抓取失败
- `useRssEntries.ts:313` — 条目获取失败
- `useVideoDetail.ts:68,108` — 视频详情获取失败
- `useServerConfig.ts:25,49,110,171,187` — 配置读写失败
- `usePlaylist.ts:244` — 播放列表操作失败
- `useNavigationHistory.ts:60,78` — 导航失败
- 视图层 `VideoPlay.vue:413,524,652`、`Profile.vue:230`、`ServerConfig.vue:200,219`、`Settings.vue:450,469` 等

**覆盖范围：** 约 50+ 处静默 catch，跨越 25+ 文件。

## 影响

- 用户操作无声失败（"点了没反应"类问题无法排查）
- 播放报告丢失 → 历史记录不准
- 配置保存失败用户不知情
- 没有错误上报机制

## 建议方向

1. 在 `utils/logger.ts` 已有 Logger，让所有 catch 块写入日志
2. 对用户可见的操作（保存、登录）添加 toast/通知反馈
3. 对播放器内部错误，利用已存在的 error-recovery 机制上报
4. 引入 `monitorError` 统一函数，catch 块中至少调用一次
