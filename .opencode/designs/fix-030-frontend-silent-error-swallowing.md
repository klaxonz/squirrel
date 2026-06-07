# Fix 030 — Frontend Silent Error Swallowing

## 根因

前端 25+ 文件中约 50+ 处 `catch {}` / `catch (_) {}` / `catch (e) {}`（空 body），异常被静默吞噬，无日志、无用户反馈。

## 修复思路

1. 创建 `src/utils/monitorError.ts` — 统一日志辅助函数，写入 `Logger.warn/error` + 可选的 context 标识
2. 逐步修复所有裸 catch 块：`catch (err) { logger.warn('[context]', err) }` 或 `monitorError('context', err)`
3. 对已有 toast/用户反馈的 catch 块，额外增加日志输出（不破坏现有用户体验）
4. 对播放器核心的 catch，通过 `playerLogger` 记录

## 涉及文件

- 新建: `src/utils/monitorError.ts`
- 播放器核心: `error-recovery.ts`, `createPlayerEngine.ts`
- 插件: `DashPlugin.ts`, `HlsPlugin.ts`, `ShakaDashPlugin.ts`
- Composables: `usePlaybackReporting`, `useGlobalSearch`, `useGlobalVideoPlayer`, `useVideoDetail`, `useServerConfig`, `usePlaylist`, `useNavigationHistory`, `useRssAccounts`, `useRssFeeds`, `useRssEntries`
- 视图: `VideoPlay.vue`, `Profile.vue`, `ServerConfig.vue`, `Settings.vue`

## 潜在风险

- 最小改动：只修改 catch 块内部，不改变控制流
- 向后兼容：所有 `catch` 仍执行原逻辑（返回默认值、显示 toast 等）
- 不影响现有测试：只加日志语句，不影响返回值或状态
