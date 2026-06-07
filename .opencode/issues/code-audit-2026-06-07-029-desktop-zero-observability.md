---
title: Desktop 零可观测性 — 所有错误被 bare catch {} 吞没
status: open
severity: high
category: error-handling
location: squirrel-desktop/src/（全量）
---

## 问题描述

Electron 桌面端整个 `src/` 目录完全没有结构化日志。所有 `try/catch` 均使用裸 `catch {}`（不带日志），分布在 15+ 文件中：

- **youtubei_core.mjs**: 10 处 (30, 60, 82, 135, 168, 564, 644, 763, 788, 796)
- **cookie-header.mjs**: 7 处全部 `catch {}` (17, 31, 45, 65, 81, 97, 142)
- **ipc-handlers.mjs**: 5 处 (30, 35, 45, 300, 309)
- **site-login.mjs**: 7 处 (114, 157, 200, 247, 332, 414, 457)
- **youtube/index.mjs**: 2 处 (50, 158)
- **youporn/index.mjs**: 2 处 (68, 96)
- **pornhub/index.mjs**: 1 处 (72)
- **file-cache.mjs**: 2 处 (31, 43)，`catch (err)` 但不日志
- **search/providers/shared.mjs**: 1 处 (51)
- **window-state.mjs**: 1 处 (44)
- **window.mjs**: 1 处 (23)
- **bilibili/index.mjs, request-runtime.mjs**: 多处无日志 catch

没有任何文件使用 `console.error`、`console.warn` 或任何日志框架。

## 影响

- 生产环境中所有播放失败、登录错误、缓存失效均不可见
- 开发调试只能靠断点或猜测，无法排查线上问题
- 用户反馈的 bug 完全无法追踪根因

## 建议方向

1. 在 Electron 主进程引入结构化日志（如 `electron-log` 或自建 logger）
2. 所有 `catch {}` 至少改为 `catch (err) { logger.error('...', err) }`
3. 关键路径（播放解析、登录、网络请求）使用区分级别的日志
